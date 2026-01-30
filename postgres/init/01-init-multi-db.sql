-- Doc manager
CREATE USER user_doc_manager WITH PASSWORD 'Pa$$w0rd';
CREATE DATABASE db_doc_manager OWNER user_doc_manager;
GRANT ALL PRIVILEGES ON DATABASE db_doc_manager TO user_doc_manager;
