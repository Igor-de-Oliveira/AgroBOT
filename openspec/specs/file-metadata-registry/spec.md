# file-metadata-registry Specification

## Purpose
TBD - created by archiving change bd-arquivos. Update Purpose after archive.
## Requirements
### Requirement: Persist file metadata for uploaded files
The system SHALL persist metadata for every file received for processing in a relational table containing, at minimum, ID, file name, file hash, created_at, and updated_at.

#### Scenario: New file is registered
- **WHEN** a user uploads a new file for processing
- **THEN** the system SHALL calculate the file hash and create a record with unique ID, file name, file hash, created_at, and updated_at

### Requirement: Use PostgreSQL 17 in Docker for metadata persistence
The metadata persistence layer SHALL use PostgreSQL version 17 running in Docker as the standard relational database for this capability.

#### Scenario: Environment is started for metadata persistence
- **WHEN** the project environment is started with this capability enabled
- **THEN** a Docker PostgreSQL 17 instance SHALL be available for the service responsible for upload and processing

### Requirement: Update metadata when file content changes
The system SHALL update file metadata when a new upload represents content changes, reflecting the new hash and updated_at timestamp.

#### Scenario: Re-upload with changed content
- **WHEN** a previously known file is uploaded again with a different hash
- **THEN** the system SHALL update the stored hash and updated_at for the corresponding record

### Requirement: Persist metadata before confirming accepted upload
The upload flow SHALL only confirm accepted processing after metadata persistence succeeds.

#### Scenario: Upload success implies persisted metadata
- **WHEN** the service returns successful upload acceptance
- **THEN** the metadata record for the uploaded file SHALL already be persisted in PostgreSQL

