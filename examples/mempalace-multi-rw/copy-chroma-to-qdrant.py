#!/usr/bin/env python3
"""Copy a frozen Chroma palace into Qdrant with stored vectors (no re-mine).

Source is a snapshot directory (chroma.sqlite3 + HNSW segments), never the
live systemd hub palace. Destination palace path must match the compose
service --palace so Qdrant collection names (hash of PalaceRef.id) agree.

Idempotent: skips the first dest.count() rows in sqlite id order, then upserts.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

SRC_DEFAULT = Path.home() / ".var/mempalace/chroma-snapshot"
DEST_DEFAULT = Path.home() / ".var/mempalace/palace"
PROGRESS_DEFAULT = Path.home() / ".var/mempalace/copy-progress.json"
BATCH = 100
COLLECTIONS = ("mempalace_drawers", "mempalace_closets")


def _log(msg: str) -> None:
    print(msg, flush=True)


def _sqlite_backup(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    src_uri = f"file:{src}?mode=ro"
    src_conn = sqlite3.connect(src_uri, uri=True)
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()


def _copy_sidecar_sqlite(snapshot: Path, dest_palace: Path) -> None:
    for name in ("knowledge_graph.sqlite3", "logstream.sqlite3"):
        src = snapshot / name
        if not src.is_file():
            _log(f"skip missing {name}")
            continue
        _sqlite_backup(src, dest_palace / name)
        _log(f"copied {name}")
    sidecar = snapshot / "mempalace_embedder.json"
    if sidecar.is_file():
        shutil.copy2(sidecar, dest_palace / sidecar.name)
        _log("copied mempalace_embedder.json")


def _open_src(snapshot: Path, collection_name: str):
    from mempalace.palace import get_collection

    return get_collection(
        str(snapshot),
        collection_name=collection_name,
        create=False,
        backend="chroma",
        read_only=True,
        _skip_identity_check=True,
    )


def _open_dest(dest_palace: Path, palace_id: str, collection_name: str):
    from mempalace.backends.base import PalaceRef
    from mempalace.backends.embedding_wrapper import EmbeddingCollection
    from mempalace.backends.qdrant import QdrantBackend

    backend = QdrantBackend()
    palace = PalaceRef(id=palace_id, local_path=str(dest_palace))
    inner = backend.get_collection(
        palace=palace,
        collection_name=collection_name,
        create=True,
    )
    return EmbeddingCollection(inner)


def _vectors(raw: Any, n: int) -> list[list[float]]:
    if raw is None:
        raise RuntimeError(
            "chroma get returned no embeddings; snapshot HNSW is unusable"
        )
    out: list[list[float]] = []
    for vec in raw:
        if vec is None:
            raise RuntimeError("a drawer is missing its stored embedding")
        if hasattr(vec, "tolist"):
            vec = vec.tolist()
        floats = [float(x) for x in vec]
        if len(floats) != 384:
            raise RuntimeError(f"embedding dim {len(floats)} != 384")
        out.append(floats)
    if len(out) != n:
        raise RuntimeError(f"embedding count {len(out)} != id count {n}")
    return out


def _copy_collection(src, dest, collection_name: str, progress: dict[str, Any]) -> int:
    from mempalace.backends.base import CollectionNotInitializedError
    from mempalace.repair import extract_via_sqlite, sqlite_drawer_count

    snapshot = Path(os.environ.get("SRC_PALACE", str(SRC_DEFAULT)))
    expected = sqlite_drawer_count(str(snapshot), collection_name) or 0
    try:
        already = int(dest.count() or 0)
    except CollectionNotInitializedError:
        already = 0
    _log(f"{collection_name}: chroma sqlite={expected} qdrant={already}")
    if expected == 0:
        return 0

    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_meta: list[dict] = []
    skipped = 0
    copied = 0
    seen = 0

    def flush() -> None:
        nonlocal copied, batch_ids, batch_docs, batch_meta
        if not batch_ids:
            return
        got = src.get(ids=batch_ids, include=["documents", "metadatas", "embeddings"])
        id_to_idx = {i: n for n, i in enumerate(got.ids)}
        docs: list[str] = []
        metas: list[dict] = []
        ordered_ids: list[str] = []
        raw_vecs: list[Any] = []
        missing = []
        for i, doc, meta in zip(batch_ids, batch_docs, batch_meta):
            idx = id_to_idx.get(i)
            if idx is None:
                missing.append(i)
                continue
            ordered_ids.append(i)
            docs.append(got.documents[idx] if got.documents else doc)
            metas.append(got.metadatas[idx] if got.metadatas else meta)
            raw_vecs.append(got.embeddings[idx] if got.embeddings else None)
        if missing:
            raise RuntimeError(
                f"{collection_name}: {len(missing)} ids in sqlite missing from chroma get "
                f"(first {missing[0]})"
            )
        dest.upsert(
            documents=docs,
            ids=ordered_ids,
            metadatas=metas,
            embeddings=_vectors(raw_vecs, len(ordered_ids)),
        )
        copied += len(ordered_ids)
        batch_ids, batch_docs, batch_meta = [], [], []
        progress[collection_name] = {"copied": already + copied, "expected": expected}
        Path(os.environ.get("PROGRESS_FILE", str(PROGRESS_DEFAULT))).write_text(
            json.dumps(progress, indent=2) + "\n"
        )
        _log(f"{collection_name}: upserted {already + copied}/{expected}")

    for embedding_id, document, metadata in extract_via_sqlite(
        str(snapshot), collection_name
    ):
        if skipped < already:
            skipped += 1
            continue
        seen += 1
        batch_ids.append(embedding_id)
        batch_docs.append(document or "")
        batch_meta.append(metadata or {})
        if len(batch_ids) >= BATCH:
            flush()
    flush()
    final = int(dest.count() or 0)
    _log(f"{collection_name}: done qdrant={final} sqlite={expected}")
    if expected and final < expected:
        raise RuntimeError(f"{collection_name}: qdrant {final} < sqlite {expected}")
    return final


def main() -> int:
    snapshot = Path(os.environ.get("SRC_PALACE", str(SRC_DEFAULT)))
    dest_palace = Path(os.environ.get("DEST_PALACE", str(DEST_DEFAULT)))
    palace_id = os.environ.get("DEST_PALACE_ID", str(dest_palace))
    qdrant_url = os.environ.get("MEMPALACE_QDRANT_URL", "http://127.0.0.1:6333")
    os.environ.setdefault("MEMPALACE_QDRANT_URL", qdrant_url)
    os.environ.setdefault("MEMPALACE_QDRANT_TIMEOUT", "120")
    os.environ["MEMPALACE_BACKEND"] = "qdrant"

    if not (snapshot / "chroma.sqlite3").is_file():
        _log(f"missing snapshot chroma.sqlite3 under {snapshot}")
        return 1
    dest_palace.mkdir(parents=True, exist_ok=True)

    progress_path = Path(os.environ.get("PROGRESS_FILE", str(PROGRESS_DEFAULT)))
    progress: dict[str, Any] = {}
    if progress_path.is_file():
        try:
            progress = json.loads(progress_path.read_text())
        except json.JSONDecodeError:
            progress = {}

    _log(f"src={snapshot}")
    _log(f"dest={dest_palace} palace_id={palace_id}")
    _log(f"qdrant={qdrant_url}")
    started = time.monotonic()
    _copy_sidecar_sqlite(snapshot, dest_palace)

    totals: dict[str, int] = {}
    for name in COLLECTIONS:
        src = _open_src(snapshot, name)
        dest = _open_dest(dest_palace, palace_id, name)
        try:
            totals[name] = _copy_collection(src, dest, name, progress)
        finally:
            src.close()
            dest.close()

    elapsed = time.monotonic() - started
    marker_url = os.environ.get("QDRANT_MARKER_URL")
    if marker_url:
        marker_path = dest_palace / "qdrant_backend.json"
        marker = json.loads(marker_path.read_text())
        marker.setdefault("qdrant", {})["url"] = marker_url
        marker_path.write_text(json.dumps(marker, indent=2) + "\n")
        _log(f"marker url set to {marker_url}")
    _log(json.dumps({"ok": True, "seconds": round(elapsed, 1), "counts": totals}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
