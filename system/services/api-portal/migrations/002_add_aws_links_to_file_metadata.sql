ALTER TABLE file_metadata
ADD COLUMN IF NOT EXISTS link_arquivo_AWS TEXT;

ALTER TABLE file_metadata
ADD COLUMN IF NOT EXISTS link_json_aws TEXT;
