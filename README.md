# Aula LangChain + LangGraph

Projeto de exemplo para executar aplicações simples com LangChain, LangGraph,
OpenAI e variaveis de ambiente com `python-dotenv`.

## Requisitos

- Python 3.13 ou superior
- `uv`
- Uma chave da OpenAI configurada em um arquivo `.env`

## 1. Instalar o uv

### Linux/macOS

Com `wget`:

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

Ou com `curl`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Depois, feche e abra o terminal novamente ou recarregue o shell:

```bash
source ~/.bashrc
```

Se estiver usando `zsh` no macOS:

```bash
source ~/.zshrc
```

Verifique a instalacao:

```bash
uv --version
```

### Windows

No PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Feche e abra o PowerShell novamente. Depois verifique:

```powershell
uv --version
```

## 2. Configurar este projeto

Entre na pasta do projeto:

```bash
cd aula-langchain-langgraph
```

Crie o ambiente virtual e instale as dependencias do `pyproject.toml`:

```bash
uv sync
```

Ative o ambiente virtual.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
.venv\Scripts\activate.bat
```

## 3. Configurar a chave da OpenAI

Crie um arquivo chamado `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sua-chave-da-openai-aqui
```

Exemplo de criacao pelo terminal no Linux/macOS:

```bash
printf "OPENAI_API_KEY=sua-chave-da-openai-aqui\n" > .env
```

Exemplo no Windows PowerShell:

```powershell
"OPENAI_API_KEY=sua-chave-da-openai-aqui" | Out-File -Encoding utf8 .env
```

Importante: nao publique chaves reais no GitHub, README, slides ou grupos. Para
o minicurso, distribua a chave por um canal temporario e revogue a chave depois
da aula.

## 4. Executar os exemplos

Exemplo basico com LangChain e tools:

```bash
uv run python 01_aula.py
```

Exemplo com LangGraph, tools e SQLite:

```bash
uv run python 02_aula.py
```

Durante a execucao, digite uma mensagem no terminal. Para encerrar:

```text
sair
```

## Criando um projeto do zero

Esta e a sequencia usada para criar um novo projeto semelhante ao do minicurso.

### Linux/macOS

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
uv --version

mkdir aula-langchain-langgraph
cd aula-langchain-langgraph

uv init
uv venv
source .venv/bin/activate

uv add langchain langchain-openai langgraph python-dotenv
```

Crie o arquivo `.env`:

```bash
printf "OPENAI_API_KEY=sua-chave-da-openai-aqui\n" > .env
```

Execute o arquivo Python do exemplo:

```bash
uv run python 01_aula.py
```

### Windows PowerShell

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version

mkdir aula-langchain-langgraph
cd aula-langchain-langgraph

uv init
uv venv
.venv\Scripts\Activate.ps1

uv add langchain langchain-openai langgraph python-dotenv
```

Crie o arquivo `.env`:

```powershell
"OPENAI_API_KEY=sua-chave-da-openai-aqui" | Out-File -Encoding utf8 .env
```

Execute o arquivo Python do exemplo:

```powershell
uv run python 01_aula.py
```

## Solucao de problemas

### `uv` nao encontrado

Feche e abra o terminal novamente. Se continuar, confira se o diretorio de
instalacao do `uv` foi adicionado ao `PATH`.

### Erro de chave da OpenAI

Confira se o arquivo `.env` esta na raiz do projeto e se a variavel esta escrita
exatamente assim:

```env
OPENAI_API_KEY=sua-chave-da-openai-aqui
```

### Erro ao ativar ambiente no Windows

Se o PowerShell bloquear a ativacao do ambiente virtual, execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Depois tente novamente:

```powershell
.venv\Scripts\Activate.ps1
```
