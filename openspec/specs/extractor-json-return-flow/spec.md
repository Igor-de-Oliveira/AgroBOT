# extractor-json-return-flow Specification

## Purpose
TBD - created by archiving change salvamento-arquivos-aws. Update Purpose after archive.
## Requirements
### Requirement: Return generated JSON to portal-agrobot
The `api-extractor` SHALL return generated JSON outputs to `portal-agrobot` after processing completes.

#### Scenario: Extractor responds with JSON payload
- **WHEN** processing completes for an uploaded file
- **THEN** `api-extractor` SHALL respond to `portal-agrobot` with the generated JSON payload

### Requirement: Do not forward files directly to api-llm
The extraction flow SHALL stop direct file forwarding from `api-extractor` to `api-llm`.

#### Scenario: No direct extractor-to-llm forwarding
- **WHEN** `api-extractor` completes processing
- **THEN** the file SHALL not be forwarded directly to `api-llm`
- **AND** orchestration SHALL continue from `portal-agrobot`

### Requirement: Persist returned JSON through portal in AWS S3 Json folder
The `portal-agrobot` SHALL persist JSON outputs returned by `api-extractor` in AWS S3 under `Json/` and store the corresponding database link.

#### Scenario: Portal persists extractor JSON
- **WHEN** `portal-agrobot` receives a JSON payload from `api-extractor`
- **THEN** the portal SHALL save it in S3 under `Json/`
- **AND** persist the JSON AWS link in relational metadata

### Requirement: Replace Json object on same logical file reprocessing
For a reprocessed logical file, the portal SHALL overwrite the prior JSON object in `Json/` and update stored metadata.

#### Scenario: Reprocessing updates Json artifact
- **WHEN** a new JSON payload is produced for the same logical file key
- **THEN** the existing S3 object in `Json/` SHALL be replaced
- **AND** the metadata link SHALL be updated to reference the latest object

