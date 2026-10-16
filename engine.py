"""Search, ranking, and persistent picker state, independent of GTK."""
from __future__ import annotations

from difflib import SequenceMatcher
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

from catalog import build_catalog


def normalize(value: str) -> str:
    value = value.strip()
    if len(value) == 1 or "{" in value or value.startswith("\\"):
        return value
    suffix = re.fullmatch(r"(.*?)\s([A-Za-z])", value)
    if suffix:
        return re.sub(r"\s+", " ", suffix[1].lower().replace("-", " ")) + " " + suffix[2]
    return re.sub(r"\s+", " ", value.lower().replace("-", " ").replace("_", " "))


class SearchIndex:
    def __init__(self):
        self.symbols = build_catalog()
        self.by_glyph = {symbol["glyph"]: symbol for symbol in self.symbols}
        self.categories = list(dict.fromkeys(symbol["category"] for symbol in self.symbols))
        self.aliases = {}
        self.words = {}
        for symbol in self.symbols:
            values = [symbol["label"], *symbol["aliases"], symbol["glyph"],
                      symbol["codepoint"], symbol["name"]]
            self.aliases[symbol["glyph"]] = list(dict.fromkeys(normalize(x) for x in values))
            for alias in self.aliases[symbol["glyph"]]:
                self.words[alias] = re.findall(r"\w+", alias)

    def search(self, query: str, *, category: str = "All", favorites=(), recent=(), limit: int = 80):
        query = normalize(query)
        explicit_category = query.startswith("/") or category != "All"
        if query.startswith("/"):
            filter_text = query[1:]
            match = next((x for x in sorted(self.categories, key=len, reverse=True)
                          if filter_text == normalize(x) or filter_text.startswith(normalize(x) + " ")), None)
            if match:
                category = match
                query = filter_text[len(normalize(match)):].strip()
            else:
                return []
        if not explicit_category and query in {"favorites", "favourites", "starred"}:
            category, query = "Favorites", ""
        if not explicit_category and query in {"recent", "recents"}:
            category, query = "Recent", ""
        if not explicit_category and any(normalize(x) == query for x in self.categories):
            category = next(x for x in self.categories if normalize(x) == query)
            query = ""
        starred = set(favorites)
        recency = {glyph: len(recent) - i for i, glyph in enumerate(recent)}
        ranked = []
        for symbol in self.symbols:
            glyph = symbol["glyph"]
            if category == "Favorites" and glyph not in starred:
                continue
            if category == "Recent" and glyph not in recency:
                continue
            if category not in {"All", "Favorites", "Recent"} and normalize(symbol["category"]) != normalize(category):
                continue
            if query:
                score = self._score(query, symbol)
                if not score:
                    continue
                # Semantic relevance dominates favorites/recency. Neither can
                # bury an exact match beneath a fuzzy approximation.
                rank = (score, glyph in starred, recency.get(glyph, 0), symbol["priority"])
            else:
                rank = (glyph in starred, recency.get(glyph, 0), symbol["priority"], 0)
            ranked.append((rank, symbol))
        ranked.sort(key=lambda pair: tuple(-int(v) for v in pair[0]) + (pair[1]["label"], pair[1]["codepoint"]))
        return [symbol for _, symbol in ranked[:limit]]

    def _score(self, query: str, symbol: dict) -> int:
        aliases = self.aliases[symbol["glyph"]]
        if query == normalize(symbol["latex"]) and symbol["latex"]:
            return 1500
        if query == normalize(symbol["label"]):
            return 1450
        if query in aliases:
            return 1400
        # TeX expressions, explicit glyphs, and one-letter queries are exact.
        # This avoids confusing \Sigma with \sigma or R with arbitrary words.
        if query.startswith("\\") or "{" in query or len(query) == 1:
            return 0
        best = 0
        words = query.split()
        for alias in aliases:
            if alias.startswith(query):
                best = max(best, 1100 - min(len(alias) - len(query), 80))
            elif all(any(part.startswith(word) for part in self.words[alias]) for word in words):
                best = max(best, 950 - min(len(alias), 100))
            elif len(query) >= 4:
                # Bounded typo tolerance: compare whole aliases, avoiding the
                # surprising unrelated subsequences produced by Unicode names.
                if abs(len(alias) - len(query)) <= max(2, len(query) // 4):
                    ratio = SequenceMatcher(None, query, alias, autojunk=False).ratio()
                    if ratio >= 0.78:
                        best = max(best, int(ratio * 700))
        return best


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "elephant-math/state.json"

    def read(self) -> dict:
        if not self.path.exists():
            return {"favorites": [], "recent": []}
        value = json.loads(self.path.read_text())
        if not isinstance(value, dict) or any(not isinstance(value.get(key, []), list) or
                not all(isinstance(x, str) for x in value.get(key, [])) for key in ("favorites", "recent")):
            raise ValueError(f"Invalid picker state: {self.path}")
        return {"favorites": value.get("favorites", []), "recent": value.get("recent", [])}

    def update(self, glyph: str, *, favorite: bool = False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = self.read()
            if favorite:
                values = set(state["favorites"])
                values.symmetric_difference_update({glyph})
                state["favorites"] = sorted(values)
            else:
                state["recent"] = [glyph] + [x for x in state["recent"] if x != glyph][:49]
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, delete=False) as file:
                temporary = Path(file.name)
                try:
                    json.dump(state, file, ensure_ascii=False)
                    file.write("\n")
                    file.flush()
                    os.fsync(file.fileno())
                    os.replace(temporary, self.path)
                finally:
                    temporary.unlink(missing_ok=True)
            return state
