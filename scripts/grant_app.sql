-- Least-privilege grants for the app's service principal role (replace the role id for your app).
GRANT USAGE ON SCHEMA public TO "{role}";
GRANT SELECT ON fragrances TO "{role}";
GRANT SELECT, INSERT, UPDATE, DELETE ON my_collection, wear_log TO "{role}";
GRANT USAGE, SELECT ON SEQUENCE wear_log_id_seq TO "{role}";
GRANT SELECT, INSERT, UPDATE ON chat_usage TO "{role}";
