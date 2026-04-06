# file-metadata-registry Specification

## Purpose
TBD - created by archiving change bd-arquivos. Update Purpose after archive.
## Requirements
### Requirement: Persist file metadata for uploaded files
The system SHALL persist metadata for every file received for processing, including AWS link fields used to locate the binary in S3.

#### Scenario: New uploaded file is registered with S3 link
- **WHEN** a user uploads a new file for processing
- **THEN** the system SHALL store the file in S3 under `Arquivos/`
- **AND** the system SHALL persist metadata including `link_arquivo_AWS` in the relational database

### Requirement: Use PostgreSQL 17 in Docker for metadata persistence
The metadata persistence layer SHALL use PostgreSQL version 17 running in Docker as the standard relational database for this capability.

#### Scenario: Environment is started for metadata persistence
- **WHEN** the project environment is started with this capability enabled
- **THEN** a Docker PostgreSQL 17 instance SHALL be available for the service responsible for upload and processing

### Requirement: Update metadata when file content changes
The system SHALL update metadata when the same logical file is uploaded again with changed content, replacing the S3 object and refreshing persisted links.

#### Scenario: Re-upload replaces existing source file in S3
- **WHEN** a previously known logical file is uploaded again
- **AND** the file must be replaced according to overwrite policy
- **THEN** the system SHALL overwrite the object in `Arquivos/`
- **AND** the system SHALL update `link_arquivo_AWS` and modification metadata in the database

### Requirement: Persist metadata before confirming accepted upload
The upload flow SHALL only confirm accepted processing after metadata persistence succeeds.

#### Scenario: Upload success implies persisted metadata
- **WHEN** the service returns successful upload acceptance
- **THEN** the metadata record for the uploaded file SHALL already be persisted in PostgreSQL

### Requirement: Validate existence in database and AWS before create or overwrite
The system SHALL verify file existence in both relational metadata and AWS S3 before deciding whether to create a new object or overwrite an existing one.

#### Scenario: File exists in database and S3
- **WHEN** the upload flow resolves a logical file key that already exists in the database
- **AND** the corresponding object exists in S3
- **THEN** the system SHALL apply overwrite behavior instead of creating a duplicate record

#### Scenario: File exists in database but not in S3
- **WHEN** metadata exists but S3 object is missing
- **THEN** the system SHALL recreate the object in S3 and reconcile metadata with the new valid link

### Requirement: Return extractor JSON to portal and persist in S3 Json folder
The `api-extractor` SHALL return generated JSON payloads to `portal-agrobot`, and the portal SHALL persist those JSON artifacts in AWS S3 under `Json/`.

#### Scenario: Extractor returns generated JSON
- **WHEN** `api-extractor` finishes processing an uploaded file
- **THEN** it SHALL return the generated JSON to `portal-agrobot`
- **AND** `portal-agrobot` SHALL store the JSON in S3 under `Json/`
- **AND** the JSON AWS link SHALL be persisted in the database

### Requirement: Replace existing JSON artifact for same logical file
The system SHALL overwrite JSON artifact objects in S3 when the same logical file is reprocessed.

#### Scenario: Reprocessing same logical file updates Json object
- **WHEN** `portal-agrobot` receives a new JSON output for a previously processed logical file
- **THEN** the existing object in `Json/` SHALL be replaced
- **AND** the persisted JSON link metadata SHALL be updated to the latest object reference

### Requirement: Stop direct extractor-to-llm file forwarding
The extraction pipeline SHALL no longer forward uploaded files directly from `api-extractor` to `api-llm`.

#### Scenario: Processing completes without direct file forwarding
- **WHEN** `api-extractor` finishes file processing
- **THEN** it SHALL not send the file directly to `api-llm`
- **AND** it SHALL return processing output to `portal-agrobot` for next-step orchestration

### Requirement: Excluir metadado e artefatos AWS de forma coordenada
The system SHALL remover metadado e artefatos AWS relacionados em um fluxo unico de exclusao.

#### Scenario: Exclusao completa de arquivo registrado
- **WHEN** uma requisicao de exclusao for recebida para um arquivo registrado
- **THEN** o sistema SHALL excluir o objeto original em `Arquivos/`
- **AND** SHALL excluir o objeto JSON correspondente em `Json/`
- **AND** SHALL remover o metadado correspondente no banco relacional

#### Scenario: Falha antes da conclusao da exclusao
- **WHEN** uma ou mais etapas falharem durante o fluxo de exclusao
- **THEN** o sistema SHALL retornar resposta de falha
- **AND** SHALL NOT retornar sucesso enquanto banco e storage estiverem inconsistentes

#### Scenario: Registro inexistente para exclusao
- **WHEN** uma requisicao de exclusao for recebida para `id` nao existente
- **THEN** o sistema SHALL retornar resposta de arquivo nao encontrado

