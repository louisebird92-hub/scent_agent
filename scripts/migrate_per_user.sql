-- One-off: make my_collection / wear_log per user, add chat_usage. Existing rows go to {owner}.
ALTER TABLE my_collection ADD COLUMN IF NOT EXISTS user_email TEXT;
UPDATE my_collection SET user_email = '{owner}' WHERE user_email IS NULL;
ALTER TABLE my_collection ALTER COLUMN user_email SET NOT NULL;
ALTER TABLE my_collection DROP CONSTRAINT IF EXISTS my_collection_pkey;
ALTER TABLE my_collection ADD PRIMARY KEY (user_email, fragrance_id);
ALTER TABLE wear_log ADD COLUMN IF NOT EXISTS user_email TEXT;
UPDATE wear_log SET user_email = '{owner}' WHERE user_email IS NULL;
ALTER TABLE wear_log ALTER COLUMN user_email SET NOT NULL;
CREATE INDEX IF NOT EXISTS wear_log_user ON wear_log (user_email, fragrance_id);
CREATE TABLE IF NOT EXISTS chat_usage (
    user_email TEXT NOT NULL,
    day        DATE NOT NULL DEFAULT CURRENT_DATE,
    messages   INT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_email, day)
);
