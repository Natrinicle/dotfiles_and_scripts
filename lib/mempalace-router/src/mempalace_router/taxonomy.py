"""Per-target wing/room alias mapping.

Each MemPalace target keeps its own taxonomy. The router maps local names to
a target's existing names and never renames anything on either side.
"""

from __future__ import annotations

from pathlib import Path

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


class TaxonomyMap:
    """Alias table between local names and one target's remote names.

    ``to_remote`` auto-saves: whenever it records a new alias row it calls
    ``save()`` so the mapping survives a crash between the call and the
    write it guides. Callers need not save manually.
    """

    def __init__(self, target_name: str, state_dir: Path):
        self.target_name = target_name
        self.path = Path(state_dir) / "taxonomy" / f"{target_name}.yaml"
        self.wings: dict[str, str] = {}
        self.rooms: dict[str, dict[str, str]] = {}

    def load(self) -> None:
        if not self.path.exists():
            self.wings, self.rooms = {}, {}
            return
        data = yaml.safe_load(self.path.read_text()) or {}
        self.wings = dict(data.get("wings") or {})
        self.rooms = {w: dict(r) for w, r in (data.get("rooms") or {}).items()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump({"wings": self.wings, "rooms": self.rooms}, sort_keys=True)
        )

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
        created = False
        rw = self.wings.get(wing)
        if rw is None:
            taken = {r for l, r in self.wings.items() if l != wing}
            rw = self._match(wing, remote_taxonomy, taken)
            self.wings[wing] = rw
            created = True
        room_map = self.rooms.setdefault(wing, {})
        rr = room_map.get(room)
        if rr is None:
            taken = {r for l, r in room_map.items() if l != room}
            rr = self._match(room, remote_taxonomy.get(rw, {}), taken)
            room_map[room] = rr
            created = True
        if created:
            self.save()
        return rw, rr, created

    def to_local(self, wing: str, room: str) -> tuple[str, str]:
        """Reverse lookup of remote names; identity when unknown."""
        for local_wing, remote_wing in self.wings.items():
            if remote_wing != wing:
                continue
            for local_room, remote_room in self.rooms.get(local_wing, {}).items():
                if remote_room == room:
                    return local_wing, local_room
        local_wing = next((l for l, r in self.wings.items() if r == wing), wing)
        return local_wing, room
