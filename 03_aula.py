import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages


load_dotenv()


loader = PyPDFLoader("boletim_servico.pdf")
docs = loader.load()
print(f"Total de páginas extraídas: {len(docs)}")
print(f"Visualizando os primeiros 200 caracteres da Página 1:\n{docs[0].page_content[:200]}...\n")


splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50) #quebra do documento em pedaços menores
chunks = splitter.split_documents(docs)
print(f"Total de pedaços (chunks) gerados: {len(chunks)}")
print(f"Visualizando um chunk completo:\n{chunks[0].page_content}\n")


embedder = OpenAIEmbeddings(model="text-embedding-3-small") #gera embeddings matemáticos

# Demonstração didática rápida do embedding:
vetor_exemplo = embedder.embed_query("boletim de servico") #transforma o texto em um vetor de números
print(f"O texto 'boletim_servico' foi transformado em um vetor (matriz) de {len(vetor_exemplo)} dimensões!")
print(f"Início do vetor gerado: {vetor_exemplo[:10]}...\n")

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embedder,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 2})




class AgentState(TypedDict):                #definição do estado, ele precisa saber as mensagens e "quem" é o próximo a agir
    messages: Annotated[list, add_messages]
    next: str



llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY") # pyright: ignore[reportArgumentType]
) #definir os nós


web_search = DuckDuckGoSearchRun()



def agente_pesquisador(state: AgentState):
    """Agente especialista em buscar na internet."""
    ultima_mensagem = state["messages"][-1].content
    print(f"\n[Agente Pesquisador] Buscando na Web por: {ultima_mensagem}")
    
    resultado = web_search.invoke(ultima_mensagem)
    
    # o agente formata a resposta e devolve para o estado
    resposta_formatada = f"Resultados da Web: {resultado}"
    return {"messages": [AIMessage(content=resposta_formatada, name="Pesquisador")]}

def agente_rag(state: AgentState):
    """Agente especialista no documento PDF da empresa."""
    ultima_mensagem = state["messages"][-1].content
    print(f"\n[Agente RAG] Buscando no Banco Vetorial...")
    
    documentos = retriever.invoke(ultima_mensagem)
    contexto = "\n\n".join([doc.page_content for doc in documentos])
    

    # print(f"[RAG] Chunks recuperados:\n{contexto}")
    
    prompt = f"Use o contexto a seguir para responder à pergunta. Contexto: {contexto}\n\nPergunta: {ultima_mensagem}"
    resposta = llm.invoke([HumanMessage(content=prompt)])
    
    return {"messages": [AIMessage(content=resposta.content, name="Especialista_RAG")]}

def agente_supervisor(state: AgentState):
    """O decisor para onde rotear a requisição."""
    
    prompt_sistema = """Você é um supervisor de roteamento.
Sua equipe tem dois especialistas:
1. "Pesquisador": Para buscas na internet e atualidades.
2. "RAG": Para perguntas sobre o documento de boletim de serviço para os servidores da UFPI.

Leia a pergunta do usuário e responda APENAS com UMA das opções abaixo:
- Pesquisador
- RAG
- FINISH (se a pergunta já foi respondida satisfatoriamente)"""

    # 1. Veja se a pergunta do usuário está chegando aqui
    print(f"\n[DEBUG] Mensagens no estado: {state.get('messages')}")

    mensagens_para_llm = [SystemMessage(content=prompt_sistema)] + state["messages"]
    resposta = llm.invoke(mensagens_para_llm)

    # 2. Veja o que a LLM está respondendo de fato
    print(f"\n[DEBUG] Resposta crua da LLM: {resposta.content}")

    escolha = resposta.content.strip().upper()
    
    # Tratamento simples caso o LLM seja muito tagarela
    if "PESQUISADOR" in escolha:
        next_agent = "Pesquisador"
    elif "RAG" in escolha:
        next_agent = "RAG"
    else:
        next_agent = "FINISH"
        
    print(f"\n[Supervisor] Roteando para: {next_agent}")
    return {"next": next_agent}



workflow = StateGraph(AgentState) #começa a criação do grafo

workflow.add_node("Supervisor", agente_supervisor)
workflow.add_node("Pesquisador", agente_pesquisador)
workflow.add_node("RAG", agente_rag)

workflow.add_edge(START, "Supervisor")


workflow.add_conditional_edges(         # O Edge Condicional: O que o Supervisor decidir dita o próximo nó
    "Supervisor",
    lambda state: state["next"],
    {
        "Pesquisador": "Pesquisador",
        "RAG": "RAG",
        "FINISH": END
    }
)


workflow.add_edge("Pesquisador", "Supervisor")      # Depois que os agentes trabalham, eles sempre devolvem pro Supervisor avaliar
workflow.add_edge("RAG", "Supervisor")

graph = workflow.compile()


def main():
    print("Chat MultiAgentes iniciado. Digite 'sair' para encerrar.")
    print("Exemplo: Como está o campus novo da UFPI? ou: Qual é a notícia mais recente de IA?\n")
    
    historico = []
    
    while True:
        pergunta = input("Você: ")
        if pergunta.lower() == 'sair':
            break
            
        historico.append(HumanMessage(content=pergunta))
        
        # Stream_mode="updates" permite ver cada nó atualizando o estado ao vivo
        for evento in graph.stream({"messages": historico, "next": ""}, stream_mode="updates"):
            for node_name, state_update in evento.items():
                # Evita printar as decisões internas de roteamento do supervisor, 
                # foca só no que os agentes retornaram.
                if "messages" in state_update:
                    ultima_msg = state_update["messages"][-1]
                    if ultima_msg.name or node_name != "Supervisor":
                        print(f"\n{node_name}: {ultima_msg.content}")

if __name__ == "__main__":
    main()