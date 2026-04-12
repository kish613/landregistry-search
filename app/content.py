"""Filesystem-backed content loader for SEO resources and blog posts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, List, Optional


CONTENT_ROOT = Path(__file__).resolve().parent.parent / "content"
REQUIRED_FIELDS = {
    "title",
    "slug",
    "description",
    "published_at",
    "updated_at",
    "author",
    "primary_keyword",
    "intent",
    "cta_variant",
    "schema_type",
    "canonical_path",
}


@dataclass(frozen=True)
class ContentItem:
    """Normalized content item used by templates and SEO feeds."""

    section: str
    title: str
    slug: str
    description: str
    published_at: str
    updated_at: str
    author: str
    primary_keyword: str
    intent: str
    cta_variant: str
    schema_type: str
    canonical_path: str
    body_html: str

    @property
    def published_dt(self) -> datetime:
        return datetime.fromisoformat(self.published_at)

    @property
    def updated_dt(self) -> datetime:
        return datetime.fromisoformat(self.updated_at)


def _parse_content_file(path: Path, section: str) -> ContentItem:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError(f"Content file {path} is missing JSON front matter")

    try:
        end_idx = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"Content file {path} is missing a closing front matter marker") from exc

    metadata = json.loads("\n".join(lines[1:end_idx]))
    missing = REQUIRED_FIELDS - set(metadata)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Content file {path} is missing required fields: {missing_list}")

    body_html = "\n".join(lines[end_idx + 1 :]).strip()

    return ContentItem(
        section=section,
        title=metadata["title"],
        slug=metadata["slug"],
        description=metadata["description"],
        published_at=metadata["published_at"],
        updated_at=metadata["updated_at"],
        author=metadata["author"],
        primary_keyword=metadata["primary_keyword"],
        intent=metadata["intent"],
        cta_variant=metadata["cta_variant"],
        schema_type=metadata["schema_type"],
        canonical_path=metadata["canonical_path"],
        body_html=body_html,
    )


def _load_section(section: str) -> List[ContentItem]:
    section_dir = CONTENT_ROOT / section
    if not section_dir.exists():
        return []

    items = [_parse_content_file(path, section) for path in sorted(section_dir.glob("*.md"))]
    return sorted(items, key=lambda item: (item.updated_dt, item.published_dt), reverse=True)


@lru_cache(maxsize=1)
def load_content_index() -> Dict[str, List[ContentItem]]:
    """Load all available content once per process."""

    return {
        "resources": _load_section("resources"),
        "blog": _load_section("blog"),
    }


def list_content(section: str) -> List[ContentItem]:
    """Return a section list."""

    return load_content_index().get(section, [])


def get_content(section: str, slug: str) -> Optional[ContentItem]:
    """Return a content item by section and slug."""

    for item in list_content(section):
        if item.slug == slug:
            return item
    return None


def all_content() -> List[ContentItem]:
    """Flatten all content into one list for feeds and sitemaps."""

    index = load_content_index()
    return index["resources"] + index["blog"]
