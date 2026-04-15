ALTER TABLE file_metadata
ADD COLUMN IF NOT EXISTS status_processamento TEXT;

UPDATE file_metadata
SET status_processamento = 'processado'
WHERE status_processamento IS NULL;

ALTER TABLE file_metadata
ALTER COLUMN status_processamento SET DEFAULT 'processado';

ALTER TABLE file_metadata
ALTER COLUMN status_processamento SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_file_metadata_status_processamento'
    ) THEN
        ALTER TABLE file_metadata
        ADD CONSTRAINT chk_file_metadata_status_processamento
        CHECK (status_processamento IN ('em_processamento', 'processado', 'erro'));
    END IF;
END $$;
