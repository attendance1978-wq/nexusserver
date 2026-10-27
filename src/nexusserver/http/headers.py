"""HTTP header utilities."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping


def _check(text: str) -> str:
    text = str(text)
    if "\r" in text or "\n" in text:
        raise ValueError("Header names and values must not contain CR or LF")
    return text


class Headers(MutableMapping[str, str]):
    """A case-insensitive, multi-value HTTP header container.

    ``headers["Name"]`` returns all values joined with ", ". Use
    :meth:`get_all` / :meth:`raw_items` when each value must stay separate
    (``Set-Cookie`` can never be comma-joined).
    """

    def __init__(self, items: Iterable[tuple[str, str]] | None = None) -> None:
        self._store: dict[str, tuple[str, list[str]]] = {}
        if items:
            for key, value in items:
                self.add(key, value)

    @staticmethod
    def _key(name: str) -> str:
        return name.lower()

    def add(self, name: str, value: str) -> None:
        name, value = _check(name), _check(value)
        key = self._key(name)
        if key in self._store:
            self._store[key][1].append(value)
        else:
            self._store[key] = (name, [value])

    def set(self, name: str, value: str) -> None:
        name, value = _check(name), _check(value)
        self._store[self._key(name)] = (name, [value])

    def get_all(self, name: str) -> list[str]:
        entry = self._store.get(self._key(name))
        return [] if entry is None else list(entry[1])

    def raw_items(self) -> Iterator[tuple[str, str]]:
        """Yield one ``(name, value)`` pair per header line (use this on the wire)."""
        for name, values in self._store.values():
            for value in values:
                yield name, value

    # MutableMapping protocol
    def __getitem__(self, name: str) -> str:
        return ", ".join(self._store[self._key(name)][1])

    def __setitem__(self, name: str, value: str) -> None:
        self.set(name, value)

    def __delitem__(self, name: str) -> None:
        del self._store[self._key(name)]

    def __iter__(self):
        for original, _ in self._store.values():
            yield original

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self._key(name) in self._store

    def __repr__(self) -> str:
        return f"Headers({list(self.raw_items())!r})"
