from ...core.models import Query, ScoredChunk, Metadata
from ..interfaces import BaseRetriever
from psycopg.rows import dict_row
from psycopg import sql
from typing import List
import psycopg
import re


class PostgresBM25Retriever(BaseRetriever):
    """
    Performs a high-performance BM25 search in Postgres using the 'pg_search' extension (ParadeDB).
    This provides true BM25 relevance scoring instead of native ts_rank approximations.
    """
    def __init__(self, dsn: str, table_name: str, **kwargs):
        super().__init__(**kwargs)
        self.dsn = dsn
        self.table_name = table_name

    def retrieve(self, query: Query, top_k: int = 100) -> List[ScoredChunk]:
        """
        Executes BM25 retrieval using pg_search's @@@ operator and score function.
        """
        # 1. Base Query with pg_search @@@ operator and score() function
        # Use alias 'd' to safely reference ctid for the score function
        safe_query_text = re.sub(r'[^\w\s]', ' ', query.text).lower()

        query_sql = sql.SQL("""
            SELECT
                document_id,
                source_id,
                page_content, 
                metadata, 
                paradedb.score(d.ctid) AS score
            FROM {} AS d
            WHERE d.page_content @@@ %s
        """).format(sql.Identifier(self.table_name))

        # 2. Dynamic Filtering (JSONB or source_id)
        # Note: Must use the alias 'd' if use one in the FROM clause
        where_clauses: list[sql.Composable] = []
        params: list[object] = [safe_query_text]

        if query.filters:
            for key, value in query.filters.items():
                if key == "source_id":
                    if isinstance(value, list):
                        where_clauses.append(sql.SQL("d.source_id = ANY(%s)"))
                        params.append(value)
                    else:
                        where_clauses.append(sql.SQL("d.source_id = %s"))
                        params.append(str(value))
                else:
                    where_clauses.append(sql.SQL("d.metadata ->> %s = %s"))
                    params.extend([key, str(value)])

        if where_clauses:
            query_sql = sql.Composed([query_sql, sql.SQL(" AND "), sql.SQL(" AND ").join(where_clauses)])

        # 3. Final ordering and limit
        query_sql = sql.Composed([query_sql, sql.SQL(" ORDER BY score DESC LIMIT %s;")])
        params.append(top_k)

        scored_chunks = []

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query_sql, params)
                results = cur.fetchall()

                for rank, row in enumerate(results, start=1):
                    # Validate metadata
                    metadata_obj = Metadata.model_validate(row['metadata'])

                    chunk = ScoredChunk(document_id=str(row['document_id']),
                                        page_content=row['page_content'],
                                        metadata=metadata_obj,
                                        embedding=None,
                                        score=float(row['score']),
                                        rank=rank,
                                        db_similarity_score=float(row['score']),
                                        source_id=row['source_id'])
                    scored_chunks.append(chunk)

        return scored_chunks
