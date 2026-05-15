from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from langchain.tools import tool
from dotenv import load_dotenv
import os

load_dotenv()

@tool
def somar(a: int, b: int) -> int:
    """Soma dois números inteiros"""
    return a + b

@tool
def multiplicar(a: int, b: int) -> int:
    """Multiplica dois números inteiros"""
    return a + b

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=os.getenv("OPENAI_API_KEY")
)

tools = [somar, multiplicar]

llm = llm.bind_tools(tools)

historico = []

while True:
    pergunta = input("Você: ")

    if pergunta == "sair":
        break

    historico.append(
        ("human", pergunta)
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Voce é um assistente de IA especializada em calculos. Use tools quando necessario"),
        *historico
    ])

    chain = prompt | llm

    resposta = chain.invoke({})

    if resposta.tool_calls:

        historico.append(resposta)

        for tool_call in resposta.tool_calls:

            print(f"CHAMDA DE TOOL: {tool_call}")

            nome_tool = tool_call["name"]
            argumentos = tool_call["args"]

            if nome_tool == "somar":
                resultado_tool = somar.invoke(argumentos)
            
            if nome_tool == "multiplicar":
                resultado_tool = multiplicar.invoke(argumentos)

            historico.append(
                ToolMessage(
                    content=resultado_tool,
                    tool_call_id=tool_call["id"]
                )
            )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente de IA especializado em cálculos. Use tools quando necessário."),
            *historico
        ])

        chain = prompt | llm

        resposta = chain.invoke({})

    historico.append(resposta)

    print(f"IA: {resposta.content}")