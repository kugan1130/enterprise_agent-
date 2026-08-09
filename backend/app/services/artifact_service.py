"""Artifact management service handling document lifecycle, history, and metadata."""

import time
import uuid
from typing import Any, Dict, List, Optional

_SESSION_ARTIFACT_STORE: Dict[str, Dict[str, Any]] = {}
_SESSION_ARTIFACT_HISTORY: Dict[str, List[Dict[str, Any]]] = {}


def create_artifact(
    artifact_type: str,
    title: str,
    content: str,
    artifact_format: str = "markdown",
    source_documents: Optional[List[str]] = None,
    file_path: Optional[str] = None,
    download_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Creates a structured artifact representation."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    artifact_id = f"art_{uuid.uuid4().hex[:10]}"

    return {
        "artifact_id": artifact_id,
        "type": artifact_type,
        "title": title,
        "content": content,
        "format": artifact_format,
        "created_at": now_str,
        "updated_at": now_str,
        "source_documents": source_documents or [],
        "metadata": metadata or {},
        "file_path": file_path,
        "download_url": download_url,
    }


def save_session_artifact(session_id: str, artifact: Dict[str, Any]) -> None:
    """Saves active artifact to session store and appends to artifact history."""
    _SESSION_ARTIFACT_STORE[session_id] = artifact

    if session_id not in _SESSION_ARTIFACT_HISTORY:
        _SESSION_ARTIFACT_HISTORY[session_id] = []

    # Update or append
    history = _SESSION_ARTIFACT_HISTORY[session_id]
    existing_idx = next((i for i, a in enumerate(history) if a.get("artifact_id") == artifact.get("artifact_id")), -1)
    if existing_idx >= 0:
        history[existing_idx] = artifact
    else:
        history.append(artifact)


def get_active_artifact(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves current active artifact for session."""
    return _SESSION_ARTIFACT_STORE.get(session_id)


def get_session_artifact_history(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves complete artifact history for session."""
    return _SESSION_ARTIFACT_HISTORY.get(session_id, [])
