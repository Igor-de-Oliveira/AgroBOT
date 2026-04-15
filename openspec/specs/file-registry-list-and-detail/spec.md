# file-registry-list-and-detail Specification

## Purpose
TBD - created by archiving change listagem-arquivos-e-detalhes. Update Purpose after archive.
## Requirements
### Requirement: Exibir arquivos registrados em lista paginada
The system SHALL display, na tela de arquivos, uma lista de arquivos registrados no banco de metadados.

#### Scenario: Arquivos registrados disponiveis
- **WHEN** o usuario abrir a tela de arquivos
- **THEN** o sistema SHALL retornar e renderizar a pagina atual de arquivos registrados

#### Scenario: Nenhum arquivo registrado
- **WHEN** o usuario abrir a tela de arquivos
- **AND** nao existirem registros no banco
- **THEN** o sistema SHALL exibir estado de lista vazia

### Requirement: Atualizar listagem ao recarregar a pagina
The system SHALL buscar os dados mais recentes da listagem sempre que a pagina for recarregada.

#### Scenario: Recarregar tela de arquivos
- **WHEN** o usuario recarregar a tela de arquivos
- **THEN** o sistema SHALL consultar novamente o backend
- **AND** SHALL renderizar os registros mais recentes persistidos

### Requirement: Suportar selecao de tamanho de pagina
The system SHALL permitir selecao de tamanho de pagina com valores `25`, `50` ou `100`.

#### Scenario: Usuario seleciona tamanho de pagina valido
- **WHEN** o usuario selecionar `25`, `50` ou `100`
- **THEN** o sistema SHALL consultar a listagem com o tamanho selecionado
- **AND** SHALL renderizar os resultados conforme o novo limite

#### Scenario: Tamanho de pagina invalido
- **WHEN** a requisicao de listagem receber `page_size` diferente de `25`, `50` ou `100`
- **THEN** o sistema SHALL rejeitar a requisicao com erro de validacao

### Requirement: Suportar navegacao entre paginas de resultados
The system SHALL permitir navegacao entre todas as paginas quando o total exceder o tamanho selecionado.

#### Scenario: Total de registros maior que limite da pagina
- **WHEN** a quantidade total de arquivos for maior que o `page_size` selecionado
- **THEN** o sistema SHALL exibir controles de navegacao de pagina

#### Scenario: Usuario navega para proxima pagina
- **WHEN** o usuario acionar a navegacao para proxima pagina
- **THEN** o sistema SHALL consultar e exibir os registros da proxima pagina

#### Scenario: Usuario navega para pagina anterior
- **WHEN** o usuario acionar a navegacao para pagina anterior
- **THEN** o sistema SHALL consultar e exibir os registros da pagina anterior

### Requirement: Abrir pagina de detalhes a partir da lista
The system SHALL disponibilizar, na listagem, acao por arquivo para abrir a pagina de detalhes do item selecionado.

#### Scenario: Usuario abre detalhes do arquivo
- **WHEN** o usuario clicar na acao de visualizar em um item da lista
- **THEN** o sistema SHALL navegar para a pagina de detalhes do arquivo correspondente

### Requirement: Exibir metadados do arquivo na pagina de detalhes
The system SHALL exibir os metadados do arquivo selecionado na pagina de detalhes.

#### Scenario: Detalhes exibem campos obrigatorios
- **WHEN** o usuario acessar a pagina de detalhes
- **THEN** o sistema SHALL exibir `id`, `name`, `hash` e `created_at` do arquivo

### Requirement: Permitir download de arquivo e JSON na pagina de detalhes
The system SHALL oferecer acoes de download para o arquivo original e para o JSON processado.

#### Scenario: Baixar arquivo original
- **WHEN** o usuario clicar no botao de download do arquivo original
- **THEN** o sistema SHALL iniciar download do arquivo no link `link_arquivo_AWS`

#### Scenario: Baixar JSON do arquivo
- **WHEN** o usuario clicar no botao de download do JSON
- **THEN** o sistema SHALL iniciar download do JSON no link `link_json_aws`

#### Scenario: Link de download ausente ou invalido
- **WHEN** o usuario solicitar download e o link registrado estiver ausente ou invalido
- **THEN** o sistema SHALL retornar erro de operacao sem informar sucesso de download

### Requirement: Permitir exclusao a partir da listagem
The system SHALL disponibilizar acao de exclusao por item na lista, acionando remocao completa dos artefatos persistidos.

#### Scenario: Usuario exclui arquivo na lista
- **WHEN** o usuario clicar na acao de excluir de um arquivo na lista
- **THEN** o sistema SHALL executar o fluxo de exclusao do arquivo
- **AND** SHALL atualizar a lista para refletir o estado atual persistido


### Requirement: Exibir status de processamento por arquivo na listagem
The system SHALL exibir, na tela de arquivos, um label de `status_processamento` para cada item da lista.

#### Scenario: Arquivo em processamento
- **WHEN** um item da listagem tiver `status_processamento = em_processamento`
- **THEN** a interface SHALL exibir label "Em processamento" ao lado do arquivo

#### Scenario: Arquivo processado com sucesso
- **WHEN** um item da listagem tiver `status_processamento = processado`
- **THEN** a interface SHALL exibir label "Processado" ao lado do arquivo

#### Scenario: Arquivo com falha de processamento
- **WHEN** um item da listagem tiver `status_processamento = erro`
- **THEN** a interface SHALL exibir label "Erro" ao lado do arquivo
