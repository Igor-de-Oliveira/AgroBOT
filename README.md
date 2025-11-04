# AgroBOT Project

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Repository](https://img.shields.io/badge/GitHub-Igor--de--Oliveira--%2F--AgroBOT-black?logo=github)](https://github.com/Igor-de-Oliveira/AgroBOT)


> Plataforma inteligente para comunicação e suporte em cultivo hidropônico, integrando processamento de dados, IA generativa e automação via Telegram.

---

## Sumário
- [Visão Geral](#-visão-geral)
- [Linguagens e Tecnologias](#-linguagens-e-tecnologias)
- [Descrição dos Arquivos](#-descrição-dos-arquivos)
- [Execução](#-execução)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Desenvolvimento Local](#-desenvolvimento-local)
- [Licença](#-licença)
- [Autor e Colaborações](#-autor-e-colaborações)

---

## Visão Geral

O **AgroBOT** é um sistema modular desenvolvido em **Python** que combina **inteligência artificial**, **automação** e **análise de dados agrícolas**.  
Ele permite a interação via **chat (FastAPI)** e **bot do Telegram** e utiliza **modelos de linguagem de grande escala (LLMs)** com **RAG** (Retrieval-Augmented Generation) para fornecer respostas contextualizadas.

---

## Linguagens e Tecnologias

### **Backend**
- **Python 3.12**
  - Framework: **FastAPI** criação de APIs REST.
  - Servidor: **Uvicorn** execução assíncrona de aplicações ASGI.

### **Bibliotecas Principais**
- **dotenv** gerenciamento de variáveis de ambiente.
- **pandas**, **numpy** processamento e análise de dados.
- **requests** integração HTTP entre serviços.
- **python-multipart** manipulação de arquivos.
- **python-telegram-bot** automação e comunicação com o Telegram.
- **langchain-core**, **langchain-openai**, **langchain-community** pipeline de IA e RAG.
- **fastapi**, **uvicorn** estrutura e execução das APIs.

### **Banco de Dados**
- **Qdrant** banco vetorial para armazenamento de embeddings e buscas semânticas.

### **Inteligência Artificial**
- **LLMs (Large Language Models)** geração de respostas baseadas em contexto.  
- **RAG (Retrieval-Augmented Generation)** busca vetorial combinada com LLMs.  
- **LangChain Framework** integração modular entre modelos, prompts e vetores.

### **Containerização e Orquestração**
- **Docker** empacotamento e isolamento dos serviços.  
- **Docker Compose** orquestração e rede interna entre os contêineres.

---

## Descrição dos Arquivos

| Caminho | Função |
|---|---|
| [`/system/services/api-extractor/src/api-extractor/main.py`](https://github.com/Igor-de-Oliveira/AgroBOT/blob/main/system/services/api-extractor/src/api-extractor/main.py) | Processa planilhas ODS e converte os dados em JSON segmentado por intervalos de tempo. |
| [`/system/services/api-telegram/src/api-telegram/main.py`](https://github.com/Igor-de-Oliveira/AgroBOT/blob/main/system/services/api-telegram/src/api-telegram/main.py) | Configura o bot do Telegram que interage com usuários e encaminha mensagens para a API de chat. |
| [`/system/services/api-llm/src/api-llm/main.py`](https://github.com/Igor-de-Oliveira/AgroBOT/blob/main/system/services/api-llm/src/api-llm/main.py) | Gera embeddings e integra com modelos (OpenAI) para consultas semânticas via RAG. |
| [`/system/services/api-llm/src/bd-vetorial/main.py`](https://github.com/Igor-de-Oliveira/AgroBOT/blob/main/system/services/api-llm/src/bd-vetorial/main.py) | Serviço de banco vetorial (Qdrant) para armazenar embeddings e suportar buscas do RAG. |
| [`/docker-compose.yaml`](https://github.com/Igor-de-Oliveira/AgroBOT/blob/main/docker-compose.yaml) | Define e conecta os serviços Docker para execução integrada. |


---

## Execução

Cada serviço utiliza **Uvicorn** como servidor ASGI para rodar as APIs FastAPI.

Para iniciar **todos os serviços juntos**:

```bash
docker-compose up --build    
```

Ou em modo “detached” (segundo plano):

```bash
docker-compose up -d     
```

Esse comando irá subir todos os serviços definidos no arquivo `docker-compose.yaml` e construir as imagens Docker se necessário.

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto, com as seguintes variaveis:

```bash
OPENAI_API_KEY= XXXXXX
TELEGRAM_BOT_TOKEN = XXXXXX
```

## Desenvolvimento Local

Você pode executar qualquer serviço manualmente para depuração:

```bash
cd .\system\services\api-llm\  
uv run python .\src\api-llm\main.py    
```

---

## Licença

Distribuído sob a licença **MIT**.

## Autor e Colaborações

<table align="center">
  <tr>
    <td align="center">
      <a href="https://github.com/Igor-de-Oliveira">
        <img src="https://avatars.githubusercontent.com/Igor-de-Oliveira" width="120px;" alt="Foto de Igor de Oliveira da Silva"/>
        <br />
        <sub><b>Igor de Oliveira da Silva</b></sub>
      </a>
      <br />
      <sub> Desenvolvedor & Pesquisador</sub>
    </td>
  </tr>
</table>

<p align="center">
   <b>UTFPR — Câmpus Santa Helena</b><br>
</p>

<p align="center">
  <a href="https://github.com/Igor-de-Oliveira/AgroBOT">
    <img src="https://img.shields.io/badge/📦%20Projeto-AgroBOT-blue?style=for-the-badge" alt="AgroBOT badge">
  </a>
  <a href="https://www.utfpr.edu.br/campus/santahelena">
    <img src="https://img.shields.io/badge/🎓%20UTFPR-Santa%20Helena-yellow?style=for-the-badge" alt="UTFPR badge">
  </a>
</p>

---