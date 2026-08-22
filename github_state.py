"""Small JSON persistence layer for GitHub-backed Streamlit state."""

import base64
import json
from pathlib import Path
from urllib.parse import quote

import requests

REPO = "harshad22491/forty-degrees"
BRANCH = "main"

_ROOT = Path(__file__).resolve().parent
_API = f"https://api.github.com/repos/{REPO}/contents"


def _token():
    """GH_TOKEN from the environment (HF Spaces) or Streamlit secrets."""
    import os

    token = os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        import streamlit as st

        return st.secrets.get("GH_TOKEN")
    except Exception:
        return None


def _headers(token):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _local_path(path):
    target = (_ROOT / path).resolve()
    target.relative_to(_ROOT)
    return target


def read_json(path):
    """Read a JSON object from GitHub, or from disk when running locally."""
    token = _token()
    if token:
        response = requests.get(
            f"{_API}/{quote(path, safe='/')}",
            headers=_headers(token),
            params={"ref": BRANCH},
            timeout=20,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        raw = base64.b64decode(response.json()["content"])
        return json.loads(raw.decode("utf-8"))

    target = _local_path(path)
    if not target.exists():
        return None
    with target.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj, commit_message):
    """Write JSON through the contents API, or to disk in local dev mode."""
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    token = _token()
    if token:
        url = f"{_API}/{quote(path, safe='/')}"
        current = requests.get(
            url,
            headers=_headers(token),
            params={"ref": BRANCH},
            timeout=20,
        )
        if current.status_code not in (200, 404):
            current.raise_for_status()
        payload = {
            "message": commit_message,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": BRANCH,
        }
        if current.status_code == 200:
            payload["sha"] = current.json()["sha"]
        response = requests.put(url, headers=_headers(token), json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    target = _local_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return None
