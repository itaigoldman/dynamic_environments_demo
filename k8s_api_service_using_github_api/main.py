from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

import github_client as gh  # noqa: E402 — import after load_dotenv so env vars are set


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Helm Repo Inspector", lifespan=lifespan)


async def _resolve_service(service_name: str) -> str:
    path = await gh.find_service_path(service_name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found in helm_repo")
    return path


@app.get("/services/{service_name}/path")
async def get_service_path(service_name: str):
    """Return the full repo path for the given service."""
    path = await _resolve_service(service_name)
    return {"service": service_name, "path": path}


@app.get("/services/{service_name}/redis")
async def check_redis(service_name: str):
    """Return whether 'redis' appears anywhere in the service's values.yaml."""
    path = await _resolve_service(service_name)
    try:
        content = await gh.get_values_yaml(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch values.yaml: {exc}")
    has_redis = "redis" in content.lower()
    return {"service": service_name, "redis": has_redis}


@app.get("/services/{service_name}/connection")
async def get_connections(service_name: str):
    """Return the 'connections' list from the service's values.yaml."""
    path = await _resolve_service(service_name)
    try:
        values = await gh.parse_values_yaml(path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not parse values.yaml: {exc}")
    connections = values.get("connections")
    if connections is None:
        raise HTTPException(status_code=404, detail=f"No 'connections' key found in {path}/values.yaml")
    return {"service": service_name, "connections": connections}
