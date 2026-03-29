# Especificacao de Objetivo Geral
## Projeto AgroBOT

---

## 1. Proposito do Documento

Este documento define o objetivo geral do projeto AgroBOT dentro de uma abordagem de Spec-Driven Development. Ele orienta decisoes de arquitetura, desenvolvimento, integracao e evolucao do sistema.

---

## 2. Visao Geral do Projeto

O AgroBOT e uma plataforma integrada para suporte ao cultivo hidroponico, usando inteligencia artificial, processamento de dados e interfaces conversacionais.

O sistema permite que produtores:

- Enviem dados operacionais (planilhas ODS, PDFs e outros formatos)
- Processem e estruturem essas informacoes automaticamente
- Consultem insights por chatbot
- Recebam suporte baseado em conhecimento tecnico e dados historicos

---

## 3. Objetivo Geral

Desenvolver uma plataforma escalavel, modular e orientada a dados para monitorar, analisar e recomendar acoes sobre cultivo hidroponico por meio de chatbot com LLM, usando dados estruturados e busca semantica.

---

## 4. Objetivos Especificos

### 4.1 Processamento de Dados
- Permitir upload de planilhas ODS
- Permitir upload de arquivos PDF
- Converter dados para estruturas normalizadas (DataFrame/JSON)
- Agrupar dados em intervalos temporais relevantes (12h)
- Garantir consistencia e padronizacao de datas e horarios

### 4.2 Armazenamento e Indexacao
- Armazenar binarios originais e JSONs processados em S3/MinIO como repositorio canonico
- Utilizar prefixos logicos `Arquivos/` (upload original) e `Json/` (artefatos processados)
- Indexar informacoes em banco vetorial para busca semantica
- Persistir metadados de upload em banco relacional
- Persistir links de storage (`link_arquivo_AWS` e `link_json_aws`) no PostgreSQL
- Permitir consultas eficientes por similaridade e por historico de arquivos enviados

### 4.3 Inteligencia Artificial (LLM + RAG)
- Implementar pipeline de ingestao para embeddings
- Utilizar RAG para respostas contextualizadas
- Garantir que respostas sejam baseadas nos dados fornecidos

### 4.4 Interface Conversacional
- Disponibilizar chatbot via Telegram
- Permitir consultas em linguagem natural
- Retornar respostas claras e contextualizadas

### 4.5 Orquestracao e Integracao
- Garantir comunicacao entre servicos via APIs REST
- Utilizar arquitetura de microsservicos
- Orquestrar servicos via Docker Compose
- Operar PostgreSQL 17 em Docker para metadados de arquivo
- Centralizar no `api-portal` a orquestracao de upload, persistencia em S3 e reconciliacao de metadados

### 4.6 Expansao da Plataforma
- Evoluir o portal web (api-portal)
- Centralizar funcionalidades de upload e observabilidade do processamento
- Permitir futuras integracoes e novas features

---

## 5. Escopo do Sistema

### 5.1 Incluido
- Upload e processamento de arquivos
- Conversao e estruturacao de dados
- Indexacao em banco vetorial
- Persistencia de metadados de arquivo (id, nome, hash, created_at, updated_at, links AWS/S3)
- Persistencia de arquivo original em `Arquivos/` e JSON processado em `Json/`
- Validacao de existencia em banco + S3 antes de create/overwrite
- Consulta via chatbot
- Arquitetura baseada em servicos independentes

### 5.2 Nao Incluido (Atual)
- Integracao com sensores IoT em tempo real
- Automacao direta de sistemas hidroponicos
- Interface mobile dedicada
- Versionamento completo de conteudo de arquivo (diff/rollback por versao)

---

## 6. Arquitetura de Alto Nivel

O sistema e composto pelos seguintes servicos:

### 6.1 api-portal
Responsavel por:
- Interface web
- Receber upload inicial do usuario
- Calcular hash do arquivo enviado
- Verificar existencia de arquivo no banco e no S3 para decidir create/overwrite/reconciliacao
- Persistir arquivo original no S3 em `Arquivos/`
- Persistir metadados e links (`link_arquivo_AWS` e `link_json_aws`) no PostgreSQL
- Encaminhar arquivo para o api-extractor e receber payload JSON processado
- Persistir JSON retornado no S3 em `Json/`

### 6.2 api-extractor
Responsavel por:
- Receber arquivo para processamento
- Processar e transformar dados
- Gerar JSONs estruturados
- Retornar payload JSON para o `api-portal`

### 6.3 api-llm
Responsavel por:
- Ingestao de dados
- Geracao de embeddings
- Implementacao de RAG
- Respostas inteligentes

### 6.4 bd-vetorial
Responsavel por:
- Armazenamento vetorial
- Indexacao semantica
- Busca por similaridade

### 6.5 postgres-arquivos (PostgreSQL 17)
Responsavel por:
- Persistencia relacional de metadados de arquivos enviados
- Garantia de integridade de registros de upload
- Suporte a rastreabilidade via hash + links de objetos em S3/MinIO

### 6.6 minio (abstracao S3)
Responsavel por:
- Armazenamento de objetos de upload original e JSON processado
- Exposicao de endpoint interno para servicos (`S3_ENDPOINT`) e URL publica para links persistidos (`S3_PUBLIC_ENDPOINT`)

### 6.7 api-telegram
Responsavel por:
- Interface de mensagens com usuario
- Receber perguntas
- Consultar api-llm
- Retornar respostas

---

## 7. Fluxo Principal de Dados

1. Usuario envia arquivo via portal web
2. api-portal recebe o arquivo
3. api-portal calcula hash e valida existencia logica no banco + S3
4. api-portal salva/sobrescreve arquivo no S3 em `Arquivos/` e persiste metadados
5. api-portal encaminha arquivo para api-extractor
6. api-extractor processa o arquivo e retorna JSON ao api-portal
7. api-portal salva/sobrescreve JSON no S3 em `Json/` e atualiza metadados
8. (Etapa separada) dados processados podem ser encaminhados para fluxo de ingestao no api-llm
9. api-llm gera embeddings
10. Dados sao indexados no banco vetorial
11. Usuario realiza pergunta via Telegram ou Web
12. Interface encaminha para api-llm
13. LLM consulta banco vetorial (RAG)
14. Resposta e gerada e retornada ao usuario

---

## 8. Requisitos Nao Funcionais

### 8.1 Escalabilidade
- Servicos independentes e desacoplados
- Capacidade de escalar horizontalmente

### 8.2 Performance
- Processamento eficiente de arquivos
- Respostas rapidas do chatbot
- Persistencia de metadados com baixo impacto no tempo de upload

### 8.3 Confiabilidade
- Tratamento de erros em todas as APIs
- Garantia de integridade dos dados
- Confirmacao de upload apenas apos persistencia de metadados
- Reconciliacao automatica para divergencias entre banco e S3
- Politica de overwrite para reprocessamento do mesmo arquivo logico

### 8.4 Manutenibilidade
- Codigo modular
- Separacao clara de responsabilidades
- Migrations versionadas para evolucao de schema relacional

### 8.5 Observabilidade (futuro)
- Logs centralizados
- Monitoramento de servicos
- Indicadores de upload e persistencia de metadados

---

## 9. Diretrizes de Evolucao

- Integracao com sensores IoT
- Expansao do modelo de IA
- Dashboard analitico no portal web
- Multiusuario e autenticacao
- Historico de consultas e relatorios
- Evolucao do modelo de metadados para versionamento completo de arquivos

---

## 10. Criterios de Sucesso

O sistema sera considerado bem-sucedido se:

- Usuarios conseguirem enviar dados sem erros
- Metadados de upload forem persistidos corretamente no PostgreSQL
- Dados forem corretamente processados e indexados
- O chatbot responder com base nos dados fornecidos
- A arquitetura suportar expansao futura

---

## 11. Consideracoes Finais

O AgroBOT e projetado como plataforma modular e evolutiva, com foco em suporte inteligente ao cultivo hidroponico. A combinacao de microsservicos, IA e persistencia relacional para rastreabilidade de arquivos aumenta confiabilidade e prepara o sistema para versionamento futuro.
