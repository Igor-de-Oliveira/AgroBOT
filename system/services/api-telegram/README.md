# Telegram Bot — AgroBOT Chat Gateway

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.x-2CA5E0.svg)](https://docs.python-telegram-bot.org/)
[![FastAPI Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Serviço simples que conecta usuários do **Telegram** ao **AgroBOT**. 
> Recebe mensagens no Telegram e encaminha para a API de chat do AgroBOT, retornando a resposta ao usuário.

---

## Sumário
- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Pré-requisitos](#-pré-requisitos)
- [Configuração](#-configuração)
- [Execução](#-execução)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Fluxo de Mensagens](#-fluxo-de-mensagens)
- [Solução de Problemas](#-solução-de-problemas)
- [Licença](#-licença)

---

## 🔎 Visão Geral

Este serviço implementa um **bot do Telegram** usando a biblioteca **python-telegram-bot**, que:
1) Responde ao comando `/start` com uma mensagem de boas-vindas.
2) Encaminha qualquer texto do usuário para a API de chat do AgroBOT (`API_URL_CHAT`), via **HTTP GET** com o parâmetro `string`.
3) Devolve ao usuário a resposta produzida pelo backend.

---

---

## Pré-requisitos

- Um **bot** criado no Telegram (via **@BotFather**) para obter o **TELEGRAM_BOT_TOKEN**

---

## Configuração

1. Crie um arquivo `.env` na raiz do projeto (mesma pasta do `main.py`) com:
   ```bash
   TELEGRAM_BOT_TOKEN=SEU_TOKEN_AQUI
   API_URL_CHAT=http://localhost:8002/chat
   ```

## Execução

Rode o bot em **polling** (escuta ativa):
```bash
uv run python .\src\api-telegran\main.py
```

---

## Variáveis de Ambiente

| Variável            | Obrigatória | Padrão                       | Descrição                                                                 |
|---------------------|-------------|------------------------------|---------------------------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`| Sim         | —                            | Token do bot do Telegram fornecido pelo @BotFather.                       |
| `API_URL_CHAT`      | sim         | `http://localhost:8002/chat` | URL do endpoint de chat do AgroBOT. O código chama `GET ?string=<texto>`. |


---


## Fluxo de Mensagens

1. Usuário envia texto no Telegram.
2. O bot chama `GET {API_URL_CHAT}?string=<mensagem>`.
3. Se `status_code == 200`, retorna `response.json()['response']` (fallback: texto padrão).
4. Em caso de erro de rede/servidor, informa: **"Erro ao conectar com o chatbot."**

---
