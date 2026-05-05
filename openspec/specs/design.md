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
- Persistir `status_processamento` com valores controlados (`em_processamento`, `processado`, `erro`)
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
- Acionar no `api-portal` a ingestao no `api-llm` de forma assincrona via `BackgroundTasks` apos persistencia do JSON em `Json/`
- Utilizar contrato de ingestao com identificadores de correlacao (`file_id`, `file_hash`, `logical_file_key`, referencias JSON)
- Atualizar status de processamento no ciclo de ingestao (`em_processamento` -> `processado` ou `erro`)

### 4.6 Expansao da Plataforma
- Evoluir o portal web (api-portal)
- Centralizar funcionalidades de upload e observabilidade do processamento
- Disponibilizar listagem paginada de arquivos com `page_size` 25/50/100
- Disponibilizar tela de detalhes do arquivo com metadados e downloads
- Exibir status de processamento por item na listagem com labels de interface
- Permitir exclusao coordenada de artefatos (`Arquivos/`, `Json/`) e metadado relacional
- Permitir futuras integracoes e novas features

### 4.7 Autenticacao e Gestao de Usuarios
- Exigir login previo para acesso as rotas protegidas do portal web
- Manter sessao server-side com cookie seguro (`HttpOnly`, `SameSite`, expiracao e `Secure` por ambiente)
- Disponibilizar login, logout e status de sessao no `api-portal`
- Persistir usuarios em tabela dedicada `portal_users` com `username` unico, `credential`, `password_hash`, `is_active` e metadados de auditoria
- Permitir CRUD de usuarios somente para contas com `credential=admin`
- Permitir inativacao logica e remocao fisica de contas conforme necessidade operacional
- Garantir nao exposicao de senha e `password_hash` em APIs, templates e logs

---

## 5. Escopo do Sistema

### 5.1 Incluido
- Upload e processamento de arquivos
- Login obrigatorio para navegacao no portal
- Controle de sessao autenticada com redirecionamento para `/login` em rotas protegidas
- Persistencia de usuarios e credenciais em `portal_users`
- CRUD administrativo de usuarios com perfis iniciais `admin` e `usuario`
- Seed de usuario administrativo inicial com senha hasheada
- Inativacao logica (`is_active=false`) e remocao fisica de usuarios
- Conversao e estruturacao de dados
- Indexacao em banco vetorial
- Persistencia de metadados de arquivo (id, nome, hash, created_at, updated_at, links AWS/S3)
- Persistencia de estado de processamento da ingestao (`status_processamento`)
- Persistencia de arquivo original em `Arquivos/` e JSON processado em `Json/`
- Validacao de existencia em banco + S3 antes de create/overwrite
- Listagem paginada de arquivos registrados com total de registros
- Consulta de detalhe por arquivo com `id`, `name`, `hash`, `created_at`, links AWS e `status_processamento`
- Exclusao completa de arquivo (S3 + banco) com retorno de falha em caso de inconsistencia
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
- Renderizar tela de login e tela administrativa de usuarios
- Validar credenciais (`username` + `password`) e criar sessao autenticada
- Invalidar sessao em logout e em conta inativa/removida
- Aplicar guarda de rotas protegidas e redirecionar para `/login` quando necessario
- Aplicar autorizacao para operacoes administrativas de usuarios (`credential=admin`)
- Expor endpoints de autenticacao (`/api/auth/login`, `/api/auth/logout`, `/api/auth/session`)
- Expor endpoints de gestao de usuarios (`/api/users`, detalhe, edicao, inativacao, remocao)
- Receber upload inicial do usuario
- Calcular hash do arquivo enviado
- Verificar existencia de arquivo no banco e no S3 para decidir create/overwrite/reconciliacao
- Persistir arquivo original no S3 em `Arquivos/`
- Persistir metadados e links (`link_arquivo_AWS` e `link_json_aws`) no PostgreSQL
- Persistir e atualizar `status_processamento` no PostgreSQL durante o ciclo de ingestao
- Encaminhar arquivo para o api-extractor e receber payload JSON processado
- Persistir JSON retornado no S3 em `Json/`
- Agendar em `BackgroundTasks` a chamada `POST /ingest_json_reference` no `api-llm`
- Enviar contrato de ingestao com `file_id`, `file_hash`, `logical_file_key`, `json_reference` e `json_internal_reference`
- Registrar logs estruturados de tentativa, sucesso e falha da etapa de embeddings
- Atualizar `status_processamento` para `processado` em sucesso e `erro` em falha da ingestao assincrona
- Expor endpoint de listagem paginada (`page`, `page_size`) com total de registros
- Expor endpoint de detalhe por `id`
- Expor endpoint de exclusao coordenada entre S3 e PostgreSQL
- Renderizar listagem web com controles de paginacao, tamanho de pagina, status por item e acoes de item
- Renderizar pagina de detalhes com botoes de download de arquivo original e JSON

### 6.2 api-extractor
Responsavel por:
- Receber arquivo para processamento
- Processar e transformar dados
- Gerar JSONs estruturados
- Retornar payload JSON para o `api-portal`

### 6.3 api-llm
Responsavel por:
- Ingestao de dados por referencia JSON enviada pelo portal
- Geracao de embeddings
- Geracao/atualizacao de embeddings no reprocessamento do mesmo arquivo logico
- Implementacao de RAG
- Respostas inteligentes
- Registrar logs estruturados para correlacao da ingestao com o arquivo processado

### 6.4 bd-vetorial
Responsavel por:
- Armazenamento vetorial
- Indexacao semantica
- Busca por similaridade

### 6.5 postgres-arquivos (PostgreSQL 17)
Responsavel por:
- Persistencia relacional de metadados de arquivos enviados
- Persistencia relacional de usuarios do portal em `portal_users`
- Garantia de integridade de registros de upload
- Garantia de unicidade de `username` e integridade de estado de conta (`is_active`)
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
8. api-portal define `status_processamento = em_processamento` e agenda task assincrona para ingestao no `api-llm`
9. api-portal retorna sucesso do upload apos persistencia e agendamento, sem bloquear no processamento de embeddings
10. task assincrona chama `POST /ingest_json_reference` no `api-llm` com dados de correlacao e referencias do JSON
11. api-llm busca o JSON preferencialmente por `json_internal_reference` e usa `json_reference` como fallback
12. api-llm gera embeddings e envia para indexacao no banco vetorial
13. em sucesso da task, `status_processamento` e atualizado para `processado`
14. em falha da task, `status_processamento` e atualizado para `erro` sem remover artefatos ja persistidos
12. Usuario realiza pergunta via Telegram ou Web
13. Interface encaminha para api-llm
14. LLM consulta banco vetorial (RAG)
15. Resposta e gerada e retornada ao usuario

### 7.1 Fluxo de consulta e gestao de arquivos registrados

1. Usuario abre a tela de arquivos no portal
2. Frontend consulta `GET /api/files` com `page` e `page_size`
3. Backend retorna itens da pagina com `status_processamento` e total de registros
4. Usuario pode alterar `page_size` (25/50/100) e navegar entre paginas
5. Usuario pode abrir detalhes de um item (`GET /api/files/{id}`)
6. Portal exibe `id`, `name`, `hash`, `created_at`, `status_processamento` e disponibiliza downloads por links AWS
7. Usuario pode excluir arquivo na listagem (`DELETE /api/files/{id}`)
8. Backend remove objetos em `Arquivos/` e `Json/` e remove metadado no PostgreSQL
9. Em falha parcial, backend retorna erro e nao sinaliza sucesso falso

### 7.2 Fluxo de autenticacao e gestao de usuarios

1. Usuario acessa o portal sem sessao valida
2. Backend redireciona para `/login` e bloqueia conteudo protegido
3. Usuario informa `username` e `password`
4. `api-portal` valida senha contra `password_hash` armazenado em `portal_users`
5. Em sucesso, sistema cria sessao, atualiza `last_login_at` e libera rotas protegidas
6. Em falha, sistema retorna erro amigavel sem expor detalhes sensiveis
7. Usuario administrador acessa `/usuarios` pela navbar e executa cadastro/edicao/inativacao/remocao
8. Endpoints de usuarios retornam somente campos nao sensiveis (nunca senha nem `password_hash`)
9. Em logout, sessao e invalidada e novo acesso exige autenticacao

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
- Regras de validacao para paginacao (`page >= 1` e `page_size` permitido)
- Exclusao coordenada com tratamento de erro para evitar sucesso com estado inconsistente
- Falha de rede/timeout na ingestao do `api-llm` sem perda de artefatos ja persistidos
- Padronizacao de erros da etapa de embeddings para diagnostico operacional
- Transicao de status rastreavel para monitoramento de itens em processamento, processados e com erro

### 8.4 Seguranca
- Senhas persistidas exclusivamente com hash forte (PBKDF2-HMAC-SHA256 com salt)
- Bloqueio de acesso a rotas protegidas sem sessao valida
- Restricao de CRUD de usuarios ao perfil administrativo
- Sanitizacao de logs de autenticacao para nao registrar senha enviada
- Controle de cookie de sessao com atributos de seguranca por ambiente

### 8.5 Manutenibilidade
- Codigo modular
- Separacao clara de responsabilidades
- Migrations versionadas para evolucao de schema relacional

### 8.6 Observabilidade (futuro)
- Logs centralizados
- Monitoramento de servicos
- Indicadores de upload e persistencia de metadados
- Logs estruturados no `api-portal` para tentativas e resultado de ingestao no `api-llm`
- Logs estruturados no `api-llm` para correlacionar requisicao de ingestao com o arquivo processado

---

## 9. Diretrizes de Evolucao

- Integracao com sensores IoT
- Expansao do modelo de IA
- Dashboard analitico no portal web
- Evolucao do modelo de autorizacao para novos tipos de `credential`
- Historico de consultas e relatorios
- Evolucao do modelo de metadados para versionamento completo de arquivos

---

## 10. Criterios de Sucesso

O sistema sera considerado bem-sucedido se:

- Usuarios nao conseguirem acessar rotas protegidas sem autenticacao
- Usuarios conseguirem realizar login/logout com controle de sessao consistente
- Usuarios administradores conseguirem cadastrar, editar, inativar e remover usuarios
- Usuarios nao administradores forem bloqueados no CRUD de usuarios
- Nenhum endpoint/template expuser senha ou `password_hash`
- Usuarios conseguirem enviar dados sem erros
- Usuarios conseguirem consultar arquivos registrados com navegacao paginada
- Usuarios conseguirem visualizar detalhes e baixar artefatos do arquivo selecionado
- Usuarios conseguirem acompanhar o status de processamento (`em_processamento`, `processado`, `erro`) na listagem e no detalhe
- Usuarios conseguirem excluir registros com consistencia entre S3 e banco
- Metadados de upload forem persistidos corretamente no PostgreSQL
- Dados forem corretamente processados e indexados
- O chatbot responder com base nos dados fornecidos
- A arquitetura suportar expansao futura

---

## 11. Consideracoes Finais

O AgroBOT e projetado como plataforma modular e evolutiva, com foco em suporte inteligente ao cultivo hidroponico. A combinacao de microsservicos, IA e persistencia relacional para rastreabilidade de arquivos aumenta confiabilidade e prepara o sistema para versionamento futuro.
