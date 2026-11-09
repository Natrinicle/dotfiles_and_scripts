"""Per-target wing/room alias mapping.

Each MemPalace target keeps its own taxonomy. The router maps local names to
a target's existing names and never renames anything on either side.
"""

from __future__ import annotations

from pathlib import Path

import os
import tempfile
import threading

import yaml

_ABBREVIATIONS = {
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "pg": "postgres",
    "postgresql": "postgres",
    "obs": "observability",
    "infra": "infrastructure",
}
_ABBREVIATION_VALUES = frozenset(_ABBREVIATIONS.values())


def canonical(name: str) -> str:
    """Return a comparison key for a wing or room name.

    Lowercase, strip a leading ``wing_``, turn ``-``/space into ``_``, apply
    the abbreviation table, strip one trailing ``s`` (len > 3), and apply the
    table once more. Table values are exempt from the plural strip so that
    ``kubernetes`` and ``postgres`` stay intact and equal their abbreviations.
    """
    token = name.lower()
    if token.startswith("wing_"):
        token = token[len("wing_"):]
    token = token.replace("-", "_").replace(" ", "_")
    token = _ABBREVIATIONS.get(token, token)
    if token not in _ABBREVIATION_VALUES and len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    return _ABBREVIATIONS.get(token, token)


class TaxonomyError(ValueError):
    """Raised when a persisted taxonomy file is unreadable or malformed."""


class TaxonomyMap:
    """Alias table between local names and one target's remote names.

    ``to_remote`` auto-saves: whenever it records a new alias row it calls
    ``save()`` so the mapping survives a crash between the call and the
    write it guides. Callers need not save manually.

    All methods hold an internal lock, so one map may be shared by the
    router's worker threads. Read through :meth:`known` / :meth:`alias_count`
    rather than iterating ``wings`` / ``rooms`` from another thread.
    """

    def __init__(self, target_name: str, state_dir: Path):
        self.target_name = target_name
        self.path = Path(state_dir) / "taxonomy" / f"{target_name}.yaml"
        self.wings: dict[str, str] = {}
        self.rooms: dict[str, dict[str, str]] = {}
        self._lock = threading.RLock()

    def known(self, wing: str, room: str | None = None) -> tuple[str | None, str | None]:
        """Recorded ``(remote wing, remote room)`` aliases; ``None`` when unknown."""
        with self._lock:
            remote_room = self.rooms.get(wing, {}).get(room) if room is not None else None
            return self.wings.get(wing), remote_room

    def alias_count(self) -> int:
        """Number of recorded wing plus room aliases."""
        with self._lock:
            return len(self.wings) + sum(len(r) for r in self.rooms.values())

    def load(self) -> None:
        with self._lock:
            self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.wings, self.rooms = {}, {}
            return
        try:
            data = yaml.safe_load(self.path.read_text())
        except yaml.YAMLError as exc:
            raise TaxonomyError(f"{self.path}: invalid YAML: {exc}") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise TaxonomyError(f"{self.path}: top level must be a mapping")
        wings = data.get("wings") or {}
        rooms = data.get("rooms") or {}
        if not isinstance(wings, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in wings.items()
        ):
            raise TaxonomyError(f"{self.path}: 'wings' must map str to str")
        if not isinstance(rooms, dict) or not all(
            isinstance(w, str)
            and isinstance(r, dict)
            and all(isinstance(k, str) and isinstance(v, str) for k, v in r.items())
            for w, r in rooms.items()
        ):
            raise TaxonomyError(f"{self.path}: 'rooms' must map str to str-to-str mappings")
        self.wings = dict(wings)
        self.rooms = {w: dict(r) for w, r in rooms.items()}

    def save(self) -> None:
        """Atomically write the YAML (temp file, fsync, rename)."""
        with self._lock:
            self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump({"wings": self.wings, "rooms": self.rooms}, sort_keys=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp",
            delete=False,
        ) as tmp:
            try:
                tmp.write(text)
                tmp.flush()
                os.fsync(tmp.fileno())
            except BaseException:
                os.unlink(tmp.name)
                raise
        os.replace(tmp.name, self.path)

    @staticmethod
    def _match(local: str, candidates, taken: set[str]) -> str:
        """Canonical match among remote names not claimed by another local name."""
        key = canonical(local)
        for cand in sorted(candidates):
            if canonical(cand) == key and cand not in taken:
                return cand
        return local

    def to_remote(
        self, wing: str, room: str, remote_taxonomy: dict[str, dict[str, int]]
    ) -> tuple[str, str, bool]:
        with self._lock:
            return self._to_remote(wing, room, remote_taxonomy)

    def _to_remote(
        self, wing: str, room: str, remote_taxonomy: dict[str, dict[str, int]]
    ) -> tuple[str, str, bool]:
        created = False
        rw = self.wings.get(wing)
        if rw is None:
            taken = {r for lw, r in self.wings.items() if lw != wing}
            rw = self._match(wing, remote_taxonomy, taken)
            self.wings[wing] = rw
            created = True
        room_map = self.rooms.setdefault(wing, {})
        rr = room_map.get(room)
        if rr is None:
            taken = {r for lr, r in room_map.items() if lr != room}
            rr = self._match(room, remote_taxonomy.get(rw, {}), taken)
            room_map[room] = rr
            created = True
        if created:
            self._save()
        return rw, rr, created

    def to_local(self, wing: str, room: str) -> tuple[str, str]:
        """Reverse lookup of remote names; identity when unknown."""
        with self._lock:
            return self._to_local(wing, room)

    def _to_local(self, wing: str, room: str) -> tuple[str, str]:
        for local_wing, remote_wing in self.wings.items():
            if remote_wing != wing:
                continue
            for local_room, remote_room in self.rooms.get(local_wing, {}).items():
                if remote_room == room:
                    return local_wing, local_room
        local_wing = next((lw for lw, r in self.wings.items() if r == wing), wing)
        return local_wing, room
