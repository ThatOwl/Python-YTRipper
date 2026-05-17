from dataclasses import dataclass
from pathlib import Path

from .candidate_resolver import TagCandidate


@dataclass
class TagWriteResult:
    success: bool
    status: str
    wrote_fields: list[str]

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status,
            "wrote_fields": list(self.wrote_fields),
        }


class TagWriter:
    """Conservative metadata writer for finalized audio files."""

    def write_candidate(self, path: Path | str, candidate: TagCandidate) -> TagWriteResult:
        audio_path = Path(path)
        suffix = audio_path.suffix.lower()

        if suffix not in {".mp3", ".m4a", ".mp4"}:
            return TagWriteResult(False, f"unsupported container: {suffix or '<none>'}", [])

        wrote_fields: list[str] = []
        try:
            imports = self._load_mutagen()
            if imports is None:
                return TagWriteResult(False, "mutagen not installed", [])
            if suffix == ".mp3":
                wrote_fields = self._write_mp3(audio_path, candidate, imports)
            else:
                wrote_fields = self._write_mp4(audio_path, candidate, imports)
            return TagWriteResult(True, "ok", wrote_fields)
        except Exception as exc:
            return TagWriteResult(False, str(exc), wrote_fields)

    @staticmethod
    def _load_mutagen():
        try:
            from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK
            from mutagen.mp4 import MP4
        except ImportError:
            return None
        return {
            "ID3": ID3,
            "ID3NoHeaderError": ID3NoHeaderError,
            "TALB": TALB,
            "TIT2": TIT2,
            "TPE1": TPE1,
            "TRCK": TRCK,
            "MP4": MP4,
        }

    @staticmethod
    def _write_mp3(path: Path, candidate: TagCandidate, imports: dict) -> list[str]:
        ID3 = imports["ID3"]
        ID3NoHeaderError = imports["ID3NoHeaderError"]
        TALB = imports["TALB"]
        TIT2 = imports["TIT2"]
        TPE1 = imports["TPE1"]
        TRCK = imports["TRCK"]

        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()

        wrote_fields: list[str] = []
        if candidate.title:
            tags["TIT2"] = TIT2(encoding=3, text=candidate.title)
            wrote_fields.append("title")
        if candidate.artist:
            tags["TPE1"] = TPE1(encoding=3, text=candidate.artist)
            wrote_fields.append("artist")
        if candidate.album:
            tags["TALB"] = TALB(encoding=3, text=candidate.album)
            wrote_fields.append("album")
        if candidate.track:
            tags["TRCK"] = TRCK(encoding=3, text=str(candidate.track))
            wrote_fields.append("track")
        tags.save(path)
        return wrote_fields

    @staticmethod
    def _write_mp4(path: Path, candidate: TagCandidate, imports: dict) -> list[str]:
        MP4 = imports["MP4"]
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()

        wrote_fields: list[str] = []
        if candidate.title:
            audio.tags["\xa9nam"] = [candidate.title]
            wrote_fields.append("title")
        if candidate.artist:
            audio.tags["\xa9ART"] = [candidate.artist]
            wrote_fields.append("artist")
        if candidate.album:
            audio.tags["\xa9alb"] = [candidate.album]
            wrote_fields.append("album")
        if candidate.track:
            try:
                track_number = int(str(candidate.track).split("/")[0])
                audio.tags["trkn"] = [(track_number, 0)]
                wrote_fields.append("track")
            except (TypeError, ValueError):
                pass

        audio.save()
        return wrote_fields
