from pathlib import Path
import os
import sqlite3

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

DB_PATH = Path(__file__).with_name("ecommerce.sqlite3")

def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    with conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (pedido_id, produto)
            )
            """
        )


def formatar_pedido(pedido_id: int) -> str:
    with conectar() as conn:
        linhas = conn.execute(
            """
            SELECT
                id,
                produto,
                quantidade,
                preco_unitario,
                quantidade * preco_unitario AS subtotal
            FROM pedido_produtos
            WHERE pedido_id = ?
            ORDER BY id
            """,
            (pedido_id,),
        ).fetchall()

    if not linhas:
        return f"Pedido {pedido_id} ainda nao possui produtos cadastrados."

    total = sum(linha["subtotal"] for linha in linhas)
    itens = [
        (
            f"- item_id={linha['id']} | {linha['produto']} | "
            f"qtd={linha['quantidade']} | "
            f"preco=R$ {linha['preco_unitario']:.2f} | "
            f"subtotal=R$ {linha['subtotal']:.2f}"
        )
        for linha in linhas
    ]

    return "\n".join([f"Pedido {pedido_id}:", *itens, f"Total: R$ {total:.2f}"])


@tool
def cadastrar_produto_pedido(
    pedido_id: int,
    produto: str,
    quantidade: int,
    preco_unitario: float,
) -> str:
    """Cadastra um produto em um pedido. Se ja existir, soma a quantidade."""
    produto = produto.strip()

    if not produto:
        return "O nome do produto nao pode ficar vazio."

    if quantidade <= 0:
        return "A quantidade precisa ser maior que zero."

    if preco_unitario < 0:
        return "O preco unitario nao pode ser negativo."

    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO pedido_produtos (
                pedido_id,
                produto,
                quantidade,
                preco_unitario
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pedido_id, produto) DO UPDATE SET
                quantidade = pedido_produtos.quantidade + excluded.quantidade,
                preco_unitario = excluded.preco_unitario,
                atualizado_em = CURRENT_TIMESTAMP
            """,
            (pedido_id, produto, quantidade, preco_unitario),
        )

    return f"Produto cadastrado/atualizado com sucesso.\n{formatar_pedido(pedido_id)}"


@tool
def atualizar_produto_pedido(
    pedido_id: int,
    produto: str,
    quantidade: int | None = None,
    preco_unitario: float | None = None,
) -> str:
    """Atualiza a quantidade e/ou o preco unitario de um produto do pedido."""
    produto = produto.strip()

    if not produto:
        return "O nome do produto nao pode ficar vazio."

    if quantidade is None and preco_unitario is None:
        return "Informe a nova quantidade, o novo preco unitario, ou ambos."

    if quantidade is not None and quantidade <= 0:
        return "A quantidade precisa ser maior que zero."

    if preco_unitario is not None and preco_unitario < 0:
        return "O preco unitario nao pode ser negativo."

    campos = []
    valores = []

    if quantidade is not None:
        campos.append("quantidade = ?")
        valores.append(quantidade)

    if preco_unitario is not None:
        campos.append("preco_unitario = ?")
        valores.append(preco_unitario)

    campos.append("atualizado_em = CURRENT_TIMESTAMP")
    valores.extend([pedido_id, produto])

    with conectar() as conn:
        cursor = conn.execute(
            f"""
            UPDATE pedido_produtos
            SET {", ".join(campos)}
            WHERE pedido_id = ? AND produto = ?
            """,
            valores,
        )

    if cursor.rowcount == 0:
        return f"Produto '{produto}' nao encontrado no pedido {pedido_id}."

    return f"Produto atualizado com sucesso.\n{formatar_pedido(pedido_id)}"


@tool
def listar_produtos_pedido(pedido_id: int) -> str:
    """Lista os produtos cadastrados em um pedido."""
    return formatar_pedido(pedido_id)


inicializar_banco()

tools = [
    cadastrar_produto_pedido,
    atualizar_produto_pedido,
    listar_produtos_pedido,
]

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY"),
)

llm_com_tools = llm.bind_tools(tools)


def assistente(state: MessagesState):
    """No principal: decide se conversa, pergunta dados faltantes ou chama tools."""
    system = SystemMessage(
        content=(
            "Voce e um atendente de ecommerce que gerencia produtos de pedidos. "
            "Use as tools para cadastrar, atualizar e listar produtos de um pedido. "
            "Nunca invente pedido_id, produto, quantidade ou preco. "
            "Se faltar algum dado obrigatorio, pergunte ao cliente antes de chamar "
            "a ferramenta. Depois que uma tool retornar, explique o resultado de "
            "forma curta e confirme o estado atual do pedido."
        )
    )

    resposta = llm_com_tools.invoke([system] + state["messages"])
    return {"messages": [resposta]}


grafo_builder = StateGraph(MessagesState)

grafo_builder.add_node("assistente", assistente)
grafo_builder.add_node("tools_sqlite", ToolNode(tools))

grafo_builder.add_edge(START, "assistente")
grafo_builder.add_conditional_edges(
    "assistente",
    tools_condition,
    {
        "tools": "tools_sqlite",
        "__end__": "__end__",
    },
)
grafo_builder.add_edge("tools_sqlite", "assistente")

grafo = grafo_builder.compile()


def mostrar_fluxo(evento):
    """Mostra o caminho percorrido no grafo a cada interacao."""
    ultima_mensagem = evento["messages"][-1]

    if ultima_mensagem.type == "human":
        return

    if getattr(ultima_mensagem, "tool_calls", None):
        for tool_call in ultima_mensagem.tool_calls:
            print(f"ORQUESTRACAO: assistente -> tools_sqlite | chamada: {tool_call}")
        return

    if ultima_mensagem.type == "tool":
        print(
            "ORQUESTRACAO: tools_sqlite -> assistente | "
            f"resultado:\n{ultima_mensagem.content}"
        )
        return

    print(f"IA: {ultima_mensagem.content}")


def main():
    print("Chat ecommerce iniciado. Digite 'sair' para encerrar.")
    print("Exemplo: cadastre 2 teclados de 150 reais no pedido 10")

    historico = []

    while True:
        pergunta = input("Voce: ")

        if pergunta.lower() == "sair":
            break

        historico.append(HumanMessage(content=pergunta))

        for evento in grafo.stream({"messages": historico}, stream_mode="values"):
            mostrar_fluxo(evento)

        historico = evento["messages"]


if __name__ == "__main__":
    main()
