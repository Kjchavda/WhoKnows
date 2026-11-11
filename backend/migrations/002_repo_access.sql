BEGIN;
ALTER TABLE repositories
  ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'public'
      CHECK (visibility IN ('public','private')),
  ADD COLUMN IF NOT EXISTS indexed_by bigint REFERENCES users(id);
COMMIT;
