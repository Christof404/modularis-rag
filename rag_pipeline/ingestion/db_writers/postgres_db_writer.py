from psycopg.conninfo import conninfo_to_dict
from ..interfaces import BaseDatabaseWriter
from psycopg_pool import ConnectionPool
from ...core.models import Chunk
from typing import List
from psycopg import sql
from enum import Enum
import psycopg
import json


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

class PostgresWriter(BaseDatabaseWriter):
    def __init__(self, dsn: str, table_name: str, vector_dimension: int, **kwargs):
        super().__init__(**kwargs)
        self.dsn = dsn
        self.table_name = table_name
        self.vector_dimension = vector_dimension
        self.pool = ConnectionPool(conninfo=self.dsn, min_size=1, max_size=10)

        self._setup_database()

    def _setup_database(self):
        """Creates the database (if necessary) and a new pgvector table."""

        # get destination database name
        conn_dict = conninfo_to_dict(self.dsn)
        target_dbname = conn_dict.get("dbname", "postgres")

        # Make a copy of the connection data and redirect it to the ‘postgres’ admin DB.
        admin_conn_dict = conn_dict.copy()
        admin_conn_dict["dbname"] = "postgres"

        # 1. Connect to the default database “postgres” to create a new DB
        try:
            with psycopg.connect(**admin_conn_dict, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_dbname,))
                    if not cur.fetchone():
                        # Database does not exist -> create it
                        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                        print(f"Database '{target_dbname}' has been created.")
        except Exception as e:
            print(f"[ERROR] Unable to create Database: {e}")

        # 2. Connect wit (new) Database and create (new) Table
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Enable vector and uuid extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_search;")

                # 2. Crate Embedding Table
                create_table_query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        source_id TEXT NOT NULL,
                        document_id UUID NOT NULL,
                        page_content TEXT NOT NULL,
                        metadata JSONB NOT NULL,
                        embedding vector({}),
                        tsv_content tsvector
                    );
                """).format(sql.Identifier(self.table_name), sql.Literal(self.vector_dimension))
                cur.execute(create_table_query)

                # 3. Create Indexes for Performance
                # HNSW Index for Vector Search
                cur.execute(sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {} USING hnsw (embedding vector_cosine_ops);
                """).format(sql.Identifier(f"idx_{self.table_name}_embedding"), sql.Identifier(self.table_name)))

                # GIN Index for JSONB Metadata Filtering
                cur.execute(sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {} USING GIN (metadata);
                """).format(sql.Identifier(f"idx_{self.table_name}_metadata"), sql.Identifier(self.table_name)))

                # GIN Index for Full-Text Search (Keyword Search)
                cur.execute(sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {} USING GIN (tsv_content);
                """).format(sql.Identifier(f"idx_{self.table_name}_tsv"), sql.Identifier(self.table_name)))

                # B-Tree Index for Source ID Lookups
                cur.execute(sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {} (source_id);
                """).format(sql.Identifier(f"idx_{self.table_name}_source_id"), sql.Identifier(self.table_name)))

                # BM25 Index for pg_search
                cur.execute(sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {} USING bm25 (page_content);
                """).format(sql.Identifier(f"idx_{self.table_name}_bm25"), sql.Identifier(self.table_name)))

    def write(self, chunks: List[Chunk]) -> None:
        """Writes a list of chunks to the database."""
        if not chunks:
            return

        insert_query = sql.SQL("""
            INSERT INTO {} (document_id, source_id, page_content, metadata, embedding, tsv_content)
            VALUES (%s, %s, %s, %s, %s, to_tsvector('simple', %s))
        """).format(sql.Identifier(self.table_name))

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    # Convert metadata Pydantic model to JSON string
                    metadata_json = json.dumps(chunk.metadata.model_dump(), cls=CustomJSONEncoder)

                    # Postgres vector columns accept lists in string format (e.g., “[0.1, 0.2]”).
                    embedding_str = str(chunk.embedding)

                    cur.execute(insert_query, (chunk.document_id,
                                               chunk.source_id,
                                               chunk.page_content,
                                               metadata_json,
                                               embedding_str,
                                               chunk.page_content))

    def is_processed(self, source_id: str) -> bool:
        """Checks if at least one chunk for this source_id is already in the DB."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                check_query = sql.SQL("SELECT 1 FROM {} WHERE source_id = %s LIMIT 1").format(sql.Identifier(self.table_name))
                cur.execute(check_query, (source_id,))
                return cur.fetchone() is not None
