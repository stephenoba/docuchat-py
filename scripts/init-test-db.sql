-- Enable vector extension on the primary database
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the test database
CREATE DATABASE docuchat_test;

-- Connect to the test database and enable the vector extension
\c docuchat_test
CREATE EXTENSION IF NOT EXISTS vector;
