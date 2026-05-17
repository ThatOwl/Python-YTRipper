from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaggingSourceSnapshot:
    url: str = ""
    video_id: str = ""
    title: str = ""
    author: str = ""
    channel_id: str = ""
    publish_date: str = ""
    thumbnail_url: str = ""
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    metadata: Any = None
    captions_available: bool = False
    caption_track_count: int | None = None
    chapters: Any = None


@dataclass
class TaggingPackage:
    package_version: int
    job_id: str
    state: str
    requested_actions: list[str]
    created_at: str
    final_output_path: str
    download_directory: str
    container: str
    playlist_title: str = ""
    source: TaggingSourceSnapshot = field(default_factory=TaggingSourceSnapshot)
    download_options: dict[str, Any] = field(default_factory=dict)
    normalization: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
