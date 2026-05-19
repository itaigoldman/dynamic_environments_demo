import base64
import os
from functools import lru_cache

import httpx
import yaml

GITHUB_API = "https://api.github.com"
REPO = os.getenv("GITHUB_REPO", "itaigoldman/dynamic_environments_demo")
HELM_ROOT = os.getenv("HELM_ROOT", "helm_repo")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def get_tree(ref: str = "HEAD") -> list[dict]:
    url = f"{GITHUB_API}/repos/{REPO}/git/trees/{ref}?recursive=1"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json().get("tree", [])


async def find_service_path(service_name: str) -> str | None:
    """Return the full repo path for a service directory inside helm_repo."""
    tree = await get_tree()
    for item in tree:
        path: str = item["path"]
        if item["type"] == "tree" and path.startswith(HELM_ROOT + "/") and path.split("/")[-1] == service_name:
            return path
    return None


async def get_file_content(path: str) -> str:
    url = f"{GITHUB_API}/repos/{REPO}/contents/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
    return base64.b64decode(data["content"]).decode()


async def get_values_yaml(service_path: str) -> str:
    return await get_file_content(f"{service_path}/values.yaml")


async def parse_values_yaml(service_path: str) -> dict:
    raw = await get_values_yaml(service_path)
    return yaml.safe_load(raw) or {}
