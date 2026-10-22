"""
Local studio store: brand kit JSON, uploaded images, generated posters and the
product-analysis cache, one folder per workspace.

This is the local-dev adapter (STUDIO_DATA_DIR, default <repo>/data/studio). The
interface is small on purpose so it can be swapped for MinIO/S3 later.
"""
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

WORKSPACE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
FILENAME_RE = re.compile(r"^[a-f0-9]{32}\.(png|jpg|mp4)$")
DOC_ID_RE = re.compile(r"^[a-f0-9]{16,32}$")
COLLECTIONS = {"campaigns", "reels", "designs"}
_EXT = {"image/png": "png", "image/jpeg": "jpg", "video/mp4": "mp4"}
_MIME = {"png": "image/png", "jpg": "image/jpeg", "mp4": "video/mp4"}

_DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "studio"


class StoreError(ValueError):
    pass


class StudioStore:
    def __init__(self, root: Optional[Path] = None, public_base: str = "/api/studio/assets"):
        self.root = Path(root or os.getenv("STUDIO_DATA_DIR") or _DEFAULT_ROOT)
        self.public_base = public_base

    def _ws_dir(self, workspace: str) -> Path:
        if not WORKSPACE_RE.match(workspace or ""):
            raise StoreError("Invalid workspace id")
        path = self.root / "workspaces" / workspace
        (path / "assets").mkdir(parents=True, exist_ok=True)
        return path

    # ---- assets -------------------------------------------------------
    def save_asset(self, workspace: str, data: bytes, mime: str) -> Dict[str, Any]:
        ext = _EXT.get(mime)
        if not ext:
            raise StoreError(f"Unsupported mime type {mime}")
        filename = f"{secrets.token_hex(16)}.{ext}"
        (self._ws_dir(workspace) / "assets" / filename).write_bytes(data)
        return {
            "asset_id": filename,
            "mime": mime,
            "sha256": hashlib.sha256(data).hexdigest(),
            "url": self.url_for(workspace, filename),
        }

    def url_for(self, workspace: str, filename: str) -> str:
        return f"{self.public_base}/{workspace}/{filename}"

    def read_asset(self, workspace: str, filename: str) -> Tuple[bytes, str]:
        if not FILENAME_RE.match(filename or ""):
            raise StoreError("Invalid asset id")
        path = self._ws_dir(workspace) / "assets" / filename
        if not path.is_file():
            raise StoreError("Asset not found")
        return path.read_bytes(), _MIME[filename.rsplit(".", 1)[1]]

    def delete_asset(self, workspace: str, filename: str) -> None:
        if FILENAME_RE.match(filename or ""):
            (self._ws_dir(workspace) / "assets" / filename).unlink(missing_ok=True)

    # ---- brand kit ----------------------------------------------------
    def load_brand_kit(self, workspace: str) -> Dict[str, Any]:
        path = self._ws_dir(workspace) / "brand_kit.json"
        return json.loads(path.read_text()) if path.is_file() else {}

    def save_brand_kit(self, workspace: str, kit: Dict[str, Any]) -> Dict[str, Any]:
        path = self._ws_dir(workspace) / "brand_kit.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(kit, indent=2))
        tmp.replace(path)
        return kit

    def asset_path(self, workspace: str, filename: str) -> Path:
        if not FILENAME_RE.match(filename or ""):
            raise StoreError("Invalid asset id")
        path = self._ws_dir(workspace) / "assets" / filename
        if not path.is_file():
            raise StoreError("Asset not found")
        return path

    # ---- JSON documents (campaigns) and workspace singletons (connections) -------
    def _doc_path(self, workspace: str, collection: str, doc_id: str) -> Path:
        if collection not in COLLECTIONS or not DOC_ID_RE.match(doc_id or ""):
            raise StoreError("Invalid document id")
        folder = self._ws_dir(workspace) / collection
        folder.mkdir(exist_ok=True)
        return folder / f"{doc_id}.json"

    def save_doc(self, workspace: str, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        path = self._doc_path(workspace, collection, doc_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        return data

    def load_doc(self, workspace: str, collection: str, doc_id: str) -> Dict[str, Any]:
        path = self._doc_path(workspace, collection, doc_id)
        if not path.is_file():
            raise StoreError("Not found")
        return json.loads(path.read_text())

    def list_docs(self, workspace: str, collection: str) -> list:
        if collection not in COLLECTIONS:
            raise StoreError("Invalid collection")
        folder = self._ws_dir(workspace) / collection
        if not folder.is_dir():
            return []
        return [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def work_dir(self, workspace: str, collection: str, doc_id: str) -> Path:
        """Scratch folder for one document's intermediate files (audio, frames, render inputs). Never served."""
        self._doc_path(workspace, collection, doc_id)  # validates collection and id
        folder = self._ws_dir(workspace) / "work" / collection / doc_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def load_private(self, workspace: str, name: str) -> Dict[str, Any]:
        """Workspace-level private JSON (e.g. connections with encrypted tokens). Never served over HTTP."""
        if name not in ("connections",):
            raise StoreError("Invalid private document")
        path = self._ws_dir(workspace) / f"{name}.json"
        return json.loads(path.read_text()) if path.is_file() else {}

    def save_private(self, workspace: str, name: str, data: Dict[str, Any]) -> None:
        if name not in ("connections",):
            raise StoreError("Invalid private document")
        path = self._ws_dir(workspace) / f"{name}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

    # ---- analysis cache (keyed by image sha256, shared across workspaces) --
    def cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self.root / "cache" / f"{key}.json"
        return json.loads(path.read_text()) if path.is_file() else None

    def cache_set(self, key: str, value: Dict[str, Any]) -> None:
        folder = self.root / "cache"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{key}.json").write_text(json.dumps(value))
