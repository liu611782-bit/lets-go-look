"""领域模型 → JSON 可序列化字典。"""

from __future__ import annotations

from typing import Any, Dict

from platform.models import Chapter, Episode, MediaItem, ResolvedSource, SourceMeta


def meta_to_dict(meta: SourceMeta) -> Dict[str, Any]:
    return {
        "adapter_id": meta.adapter_id,
        "display_name": meta.display_name,
        "media_types": [mt.value for mt in meta.media_types],
        "status": meta.status.value,
        "upstream_repo": meta.upstream_repo,
        "license": meta.license,
        "note": meta.note,
        "ready": meta.status.value == "active",
    }


def item_to_dict(item: MediaItem) -> Dict[str, Any]:
    return {
        "source": item.source,
        "external_id": item.external_id,
        "title": item.title,
        "media_type": item.media_type.value,
        "cover_url": item.cover_url,
        "summary": item.summary,
        "author": item.author,
        "status": item.status,
        "rating": item.rating,
        "extra": dict(item.extra),
    }


def episode_to_dict(episode: Episode) -> Dict[str, Any]:
    return {
        "external_id": episode.external_id,
        "index": episode.index,
        "title": episode.title,
        "duration_seconds": episode.duration_seconds,
        "is_finished": episode.is_finished,
    }


def chapter_to_dict(chapter: Chapter) -> Dict[str, Any]:
    return {
        "external_id": chapter.external_id,
        "index": chapter.index,
        "title": chapter.title,
        "word_count": chapter.word_count,
    }


def resolved_to_dict(resolved: ResolvedSource) -> Dict[str, Any]:
    return {
        "url": resolved.url,
        "media_type": resolved.media_type.value,
        "quality": resolved.quality,
        "format": resolved.format,
        "headers": dict(resolved.headers),
        "expires_in_seconds": resolved.expires_in_seconds,
        "note": resolved.note,
    }
