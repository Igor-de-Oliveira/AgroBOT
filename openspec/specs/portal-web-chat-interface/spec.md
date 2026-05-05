# portal-web-chat-interface Specification

## Purpose
TBD - created by archiving change interface-chat-web. Update Purpose after archive.
## Requirements
### Requirement: Disponibilizar canal de chat web no portal
The system SHALL disponibilizar uma interface de chat web no `api-portal` para usuarios autenticados conversarem com o bot.

#### Scenario: Acesso ao chat web pela navegacao principal
- **WHEN** o usuario autenticado clicar em "Chat Web" na navbar
- **THEN** o sistema SHALL abrir a pagina de chat web
- **AND** SHALL exibir area de mensagens, campo de entrada e acao de envio

#### Scenario: Bloqueio de acesso sem autenticacao
- **WHEN** um usuario sem sessao valida tentar acessar a pagina de chat web
- **THEN** o sistema SHALL redirecionar para login
- **AND** SHALL impedir acesso ao conteudo da conversa

### Requirement: Encaminhar perguntas do chat web para `/chat` da api-llm
The system SHALL enviar cada pergunta submetida no chat web para o endpoint `/chat` da `api-llm` por meio do `api-portal`.

#### Scenario: Envio de pergunta valida
- **WHEN** o usuario enviar uma pergunta nao vazia no chat web
- **THEN** o `api-portal` SHALL receber a pergunta
- **AND** SHALL encaminhar a requisicao para `/chat` da `api-llm`

#### Scenario: Validacao de pergunta vazia
- **WHEN** o usuario tentar enviar pergunta vazia ou apenas com espacos
- **THEN** o sistema SHALL rejeitar o envio
- **AND** SHALL exibir feedback de validacao ao usuario

### Requirement: Renderizar resposta da LLM como mensagem no chat web
The system SHALL representar a resposta retornada pela `api-llm` como mensagem do bot na conversa web.

#### Scenario: Resposta bem-sucedida da api-llm
- **WHEN** o `api-portal` receber resposta valida do `/chat`
- **THEN** o frontend SHALL adicionar uma mensagem do bot no historico
- **AND** SHALL manter visivel a mensagem da pergunta enviada pelo usuario

#### Scenario: Falha na chamada da api-llm
- **WHEN** ocorrer erro, timeout ou indisponibilidade ao chamar `/chat`
- **THEN** o sistema SHALL exibir mensagem de erro amigavel no chat web
- **AND** SHALL nao remover mensagens ja exibidas na conversa

### Requirement: Preservar compatibilidade com canal Telegram
The system SHALL manter o fluxo de chat via Telegram funcional apos a introducao do chat web.

#### Scenario: Operacao simultanea dos canais
- **WHEN** o chat web estiver habilitado no portal
- **THEN** o sistema SHALL continuar aceitando perguntas e retornando respostas no Telegram sem regressao funcional

