"""Tiger Data / PostgreSQL hybrid retrieval with revision-scoped RRF."""

import json

import psycopg
from psycopg.rows import dict_row

from .config import Settings
from .git_history import Repository
from .models import Evidence
from .ollama import Ollama
from .telemetry import Trace


class SearchError(ValueError):
    pass


SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS poltergit_evidence (
    repo_key text NOT NULL,
    source_id text NOT NULL,
    revision text NOT NULL,
    model text NOT NULL,
    content text NOT NULL,
    source jsonb NOT NULL,
    embedding vector(768) NOT NULL,
    keywords tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    PRIMARY KEY (repo_key, source_id)
);
CREATE INDEX IF NOT EXISTS poltergit_repo_idx ON poltergit_evidence (repo_key, revision, model);
CREATE INDEX IF NOT EXISTS poltergit_keyword_idx ON poltergit_evidence USING gin (keywords);
CREATE INDEX IF NOT EXISTS poltergit_vector_idx ON poltergit_evidence USING hnsw (embedding vector_cosine_ops);
"""

# Both ranking branches see the same repository, revision, and embedding model.
HYBRID = """
WITH scoped AS MATERIALIZED (
  SELECT source_id, source, keywords, embedding FROM poltergit_evidence
  WHERE repo_key = %(repo)s AND revision = %(revision)s AND model = %(model)s
), semantic AS (
  SELECT source_id, row_number() OVER (ORDER BY embedding <=> %(vector)s::vector, source_id) AS rank
  FROM scoped ORDER BY embedding <=> %(vector)s::vector, source_id LIMIT 30
), lexical AS (
  SELECT source_id, row_number() OVER (
    ORDER BY ts_rank_cd(keywords, plainto_tsquery('english', %(query)s)) DESC, source_id
  ) AS rank
  FROM scoped WHERE keywords @@ plainto_tsquery('english', %(query)s)
  ORDER BY ts_rank_cd(keywords, plainto_tsquery('english', %(query)s)) DESC, source_id LIMIT 30
), ranked AS (
  SELECT source_id, sum(score) AS score FROM (
    SELECT source_id, 1.0 / (60 + rank) AS score FROM semantic
    UNION ALL
    SELECT source_id, 1.0 / (60 + rank) AS score FROM lexical
  ) scores GROUP BY source_id
)
SELECT scoped.source FROM ranked JOIN scoped USING (source_id)
ORDER BY ranked.score DESC, source_id LIMIT %(limit)s
"""


def connect(settings: Settings):
    if not settings.database_url:
        raise SearchError("Set POLTERGIT_DATABASE_URL to a free Tiger Cloud or local pgvector database.")
    try:
        return psycopg.connect(settings.database_url, connect_timeout=8, row_factory=dict_row,
                               options="-c statement_timeout=30000")
    except psycopg.Error as exc:
        # Never expose a connection string or server diagnostics containing secrets.
        raise SearchError("PostgreSQL could not be reached. Check POLTERGIT_DATABASE_URL and TLS settings.") from exc


def index_repository(repo: Repository, settings: Settings, limit: int = 100) -> tuple[int, list[str]]:
    warnings = []
    with Trace(settings, "index") as trace:
        with trace.step("Collect commit evidence", "git.history"):
            sources = repo.recent(limit)
        if settings.github:
            from .github import enrich
            with trace.step("Read related GitHub discussions", "http.client"):
                additions, warnings = enrich(repo.remote, sources, settings.github_token)
                sources.extend(additions)
        sources = list({s.id: s for s in sources}.values())
        texts = [s.title + "\n" + s.body for s in sources]
        vectors = []
        # Fail early on configuration, before doing expensive embedding work.
        with connect(settings) as conn:
            with trace.step("Embed history", "gen_ai.embeddings",
                            **{"gen_ai.request.model": settings.embedding_model,
                               "gen_ai.operation.name": "embeddings", "gen_ai.system": "ollama"}):
                ollama = Ollama(settings)
                for start in range(0, len(texts), 16):
                    vectors.extend(ollama.embed(texts[start:start + 16]))
            try:
                with trace.step("Store vector and keyword index", "db.query"):
                    conn.execute(SCHEMA)
                    conn.execute("DELETE FROM poltergit_evidence WHERE repo_key = %s", (repo.key,))
                    with conn.cursor() as cursor:
                        cursor.executemany("""INSERT INTO poltergit_evidence
                            (repo_key, source_id, revision, model, content, source, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)""",
                            [(repo.key, s.id, repo.revision, settings.embedding_model, text,
                              s.model_dump_json(), json.dumps(vector))
                             for s, text, vector in zip(sources, texts, vectors, strict=True)])
            except psycopg.Error as exc:
                raise SearchError("Indexing failed. Verify pgvector is installed and this user can create tables/extensions.") from exc
    return len(sources), warnings


def search(repo: Repository, query: str, settings: Settings, limit: int = 8) -> list[Evidence]:
    with connect(settings) as conn:
        try:
            exists = conn.execute("""SELECT 1 FROM poltergit_evidence
                WHERE repo_key=%s AND revision=%s AND model=%s LIMIT 1""",
                (repo.key, repo.revision, settings.embedding_model)).fetchone()
            if not exists:
                raise SearchError("The evidence index is missing or stale. Run poltergit index for this HEAD and model.")
            vector = Ollama(settings).embed([query], query=True)[0]
            rows = conn.execute(HYBRID, {"repo": repo.key, "revision": repo.revision,
                "model": settings.embedding_model, "query": query[:2000],
                "vector": json.dumps(vector), "limit": max(1, min(limit, 30))}).fetchall()
        except psycopg.Error as exc:
            raise SearchError("The evidence index is unavailable. Run poltergit index and check pgvector.") from exc
    return [Evidence.model_validate(row["source"]) for row in rows]
