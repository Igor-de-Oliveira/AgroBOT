## ADDED Requirements

### Requirement: Portal SHALL enviar JSON processado para ingestao no api-llm
The `portal-agrobot` SHALL acionar o `api-llm` para ingestao apos persistir o JSON processado do arquivo.

#### Scenario: Fluxo de processamento conclui persistencia do JSON
- **WHEN** `portal-agrobot` persistir com sucesso o JSON em `Json/`
- **THEN** o portal SHALL chamar o endpoint de ingestao do `api-llm`
- **AND** SHALL incluir identificadores de correlacao do arquivo processado

### Requirement: Api-llm SHALL gerar embeddings a partir do JSON referenciado
The `api-llm` SHALL consumir o JSON referenciado pelo portal e executar geracao de embeddings.

#### Scenario: Requisicao de ingestao valida recebida
- **WHEN** `api-llm` receber uma requisicao valida de ingestao do portal
- **THEN** o `api-llm` SHALL processar o JSON correspondente
- **AND** SHALL gerar/atualizar embeddings para o arquivo correlacionado

### Requirement: Falha de ingestao SHALL ser reportada sem remover artefatos persistidos
The system SHALL reportar falhas da etapa de ingestao no `api-llm` preservando metadados e JSON ja persistidos.

#### Scenario: Api-llm indisponivel ou erro de processamento
- **WHEN** a chamada do portal para ingestao no `api-llm` falhar
- **THEN** o sistema SHALL retornar erro da etapa de embeddings
- **AND** SHALL NOT remover o arquivo original nem o JSON persistido

### Requirement: Reprocessamento SHALL atualizar embeddings do mesmo arquivo logico
The system SHALL disparar nova ingestao no `api-llm` quando houver reprocessamento do mesmo arquivo logico.

#### Scenario: Mesmo arquivo logico e reprocessado
- **WHEN** um arquivo logico previamente processado gerar novo JSON
- **THEN** o portal SHALL enviar nova requisicao de ingestao ao `api-llm`
- **AND** o `api-llm` SHALL atualizar a representacao vetorial correspondente
