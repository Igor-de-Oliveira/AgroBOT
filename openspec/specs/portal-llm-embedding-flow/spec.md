## ADDED Requirements

### Requirement: Portal SHALL enviar JSON processado para ingestao no api-llm
The `portal-agrobot` SHALL acionar o `api-llm` para ingestao apos persistir o JSON processado do arquivo, executando essa etapa de forma assincrona via `BackgroundTasks`.

#### Scenario: Fluxo de processamento conclui persistencia do JSON
- **WHEN** `portal-agrobot` persistir com sucesso o JSON em `Json/`
- **THEN** o portal SHALL registrar `status_processamento = em_processamento`
- **AND** SHALL agendar em `BackgroundTasks` a chamada ao endpoint de ingestao do `api-llm`
- **AND** SHALL incluir identificadores de correlacao do arquivo processado

### Requirement: Api-llm SHALL gerar embeddings a partir do JSON referenciado
The `api-llm` SHALL consumir o JSON referenciado pelo portal e executar geracao de embeddings.

#### Scenario: Requisicao de ingestao valida recebida
- **WHEN** `api-llm` receber uma requisicao valida de ingestao do portal
- **THEN** o `api-llm` SHALL processar o JSON correspondente
- **AND** SHALL gerar/atualizar embeddings para o arquivo correlacionado

### Requirement: Falha de ingestao SHALL ser reportada sem remover artefatos persistidos
The system SHALL reportar falhas da etapa de ingestao no `api-llm` preservando metadados e JSON ja persistidos, por meio da atualizacao de `status_processamento`.

#### Scenario: Api-llm indisponivel ou erro de processamento no task assincrono
- **WHEN** a chamada assincrona do portal para ingestao no `api-llm` falhar
- **THEN** o sistema SHALL atualizar `status_processamento` para `erro`
- **AND** SHALL NOT remover o arquivo original nem o JSON persistido

### Requirement: Conclusao da ingestao assincrona SHALL atualizar status para processado
The system SHALL atualizar o status de processamento para `processado` quando a etapa assincrona de ingestao no `api-llm` finalizar com sucesso.

#### Scenario: Ingestao assincrona concluida com sucesso
- **WHEN** o `api-llm` retornar sucesso na ingestao disparada em `BackgroundTasks`
- **THEN** o sistema SHALL atualizar `status_processamento` para `processado`

### Requirement: Reprocessamento SHALL reiniciar ciclo de status de processamento
The system SHALL reiniciar o ciclo de status em reprocessamentos do mesmo arquivo logico.

#### Scenario: Mesmo arquivo logico e reprocessado
- **WHEN** um arquivo logico previamente processado gerar novo JSON
- **THEN** o portal SHALL atualizar `status_processamento` para `em_processamento` antes da nova ingestao assincrona
- **AND** SHALL atualizar para `processado` ou `erro` conforme o resultado da nova ingestao
