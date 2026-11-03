"""A tiny read-only document store backed by a bundled JSON file.

In a real server this is where you'd talk to your database or API. Keeping it
behind a small class like this makes the tools easy to test and easy to swap.
"""

from __future__ import annotations

import json
from importlib import resources

from pydantic import BaseModel, TypeAdapter


class Doc(BaseModel):
    slug: str
    title: str
    tags: list[str]
    updated: str
    body: str


_DOCS = TypeAdapter(list[Doc])


class DocStore:
    def __init__(self, docs: list[Doc]) -> None:
        self._docs = docs
        self._by_slug = {doc.slug: doc for doc in docs}

    @classmethod
    def from_package(cls) -> DocStore:
        raw = resources.files("mcp_starter.data").joinpath("docs.json").read_text("utf-8")
        return cls(_DOCS.validate_python(json.loads(raw)))

    def get(self, slug: str) -> Doc | None:
        return self._by_slug.get(slug)

    def slugs(self) -> list[str]:
        return list(self._by_slug)

    def search(self, query: str = "", tag: str | None = None) -> list[Doc]:
        """Case-insensitive substring match on title and body, optionally filtered by tag."""
        needle = query.strip().lower()
        results: list[Doc] = []
        for doc in self._docs:
            if tag and tag.lower() not in (t.lower() for t in doc.tags):
                continue
            if needle and needle not in doc.title.lower() and needle not in doc.body.lower():
                continue
            results.append(doc)
        return results
