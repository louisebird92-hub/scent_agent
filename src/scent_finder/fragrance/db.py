"""Lakebase connection and embedding helpers shared by the seed scripts and MCP server."""

import os
from typing import Any, LiteralString, cast

import psycopg
from openai import OpenAI
from databricks.sdk import WorkspaceClient
from pgvector.psycopg import register_vector

# Unset in a Databricks App (service principal env auth); locally falls back to the SDK default chain.
PROFILE = os.environ.get("DATABRICKS_PROFILE") or None
ENDPOINT = os.environ.get(
    "LAKEBASE_ENDPOINT", "projects/scent-finder/branches/production/endpoints/primary"
)
DATABASE = os.environ.get("LAKEBASE_DATABASE", "databricks_postgres")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "system.ai.gte-large-en")  # Unity Gateway model service
EMBED_DIM = 1024

_ws: WorkspaceClient | None = None


def ws() -> WorkspaceClient:
    global _ws
    if _ws is None:
        _ws = WorkspaceClient(profile=PROFILE)
    return _ws


def _endpoint_name() -> str:
    """LAKEBASE_ENDPOINT may be an endpoint or (from an app resource) a branch; resolve to an endpoint."""
    if "/endpoints/" in ENDPOINT:
        return ENDPOINT
    branch = ENDPOINT if "/branches/" in ENDPOINT else f"{ENDPOINT}/branches/production"
    for ep in ws().postgres.list_endpoints(parent=branch):
        if ep.name:
            return ep.name
    raise RuntimeError(f"No Lakebase endpoint under {branch}")


def connect(register: bool = True) -> psycopg.Connection:
    """Open a connection using a short-lived OAuth token (valid ~1h).

    In a Databricks App the postgres resource injects PGHOST/PGDATABASE/PGUSER; locally they
    are resolved from the endpoint and the caller's identity.
    """
    w = ws()
    endpoint = _endpoint_name()
    host = os.environ.get("PGHOST")
    if not host:
        status = w.postgres.get_endpoint(endpoint).status
        if not status or not status.hosts or not status.hosts.host:
            raise RuntimeError(f"Lakebase endpoint {endpoint} has no host yet")
        host = status.hosts.host
    token = w.postgres.generate_database_credential(endpoint=endpoint).token
    conn = psycopg.connect(
        host=host,
        dbname=os.environ.get("PGDATABASE") or DATABASE,
        user=os.environ.get("PGUSER") or w.current_user.me().user_name,
        password=token,
        sslmode="require",
        autocommit=True,
    )
    if register:
        register_vector(conn)
    return conn


def gateway() -> OpenAI:
    """OpenAI-compatible client for Unity Gateway (system.ai.* models), with a fresh Databricks token."""
    w = ws()
    token = w.config.authenticate()["Authorization"].split(" ", 1)[1]
    return OpenAI(base_url=f"{w.config.host}/ai-gateway/mlflow/v1", api_key=token)


def _embed_batch(batch: list[str]) -> list[list[float]]:
    resp = gateway().embeddings.create(model=EMBED_MODEL, input=batch)
    return [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]


def embed(texts: list[str], batch_size: int = 128, workers: int = 4) -> list[list[float]]:
    """Embed texts with a Databricks Foundation Model endpoint, in parallel batches."""
    from concurrent.futures import ThreadPoolExecutor

    batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
    with ThreadPoolExecutor(workers) as pool:
        return [v for vs in pool.map(_embed_batch, batches) for v in vs]


def q(sql: str) -> LiteralString:
    """Mark SQL built from trusted, in-repo fragments (never user input) for psycopg's typing."""
    return cast(LiteralString, sql)


Row = dict[str, Any]
