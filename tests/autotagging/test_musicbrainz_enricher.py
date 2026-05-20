import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.core.candidate_resolver import CandidateResolver
from autotagging.core.musicbrainz_enricher import MusicBrainzEnricher


class _StubMusicBrainzClient:
    def __init__(self):
        self.calls = []

    def search_recordings(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("recording") == "A Kiss To Build A Dream On" and kwargs.get("artist") == "Louis Armstrong":
            return {
                "recording-list": [
                    {
                        "ext:score": "100",
                        "title": "A Kiss to Build a Dream On",
                        "artist-credit-phrase": "Louis Armstrong",
                        "release-list": [{"title": "The Decca Singles 1935-1946"}],
                    }
                ]
            }
        return {"recording-list": []}


class TestMusicBrainzEnricher(unittest.TestCase):
    def test_load_client_returns_none_for_incomplete_module_stub(self):
        incomplete_stub = types.ModuleType("musicbrainzngs")

        with patch.dict(sys.modules, {"musicbrainzngs": incomplete_stub}):
            self.assertIsNone(MusicBrainzEnricher._load_client())

    def test_enricher_queries_recovered_title_artist_hint_before_title_only(self):
        payload = {
            "playlist_title": "Best Fallout Songs",
            "source": {
                "author": "Powell Yap",
                "title": "A Kiss To Build A Dream On - Louis Armstrong",
                "keywords": [
                    "Kiss",
                    "To",
                    "Build",
                    "Dream",
                    "On",
                    "Fallout",
                    "soundtrack",
                    "Louis",
                    "Armstrong",
                ],
                "description": "",
            },
            "normalization": {
                "title_analysis": {
                    "cleaned_title": "A Kiss To Build A Dream On - Louis Armstrong",
                    "guessed_artist": "A Kiss To Build A Dream On",
                    "guessed_title": "Louis Armstrong",
                    "split_confidence": "dash_split",
                    "lookup_title": "A Kiss To Build A Dream On - Louis Armstrong",
                }
            },
        }

        resolver = CandidateResolver()
        current_candidate = resolver.resolve(payload)

        client = _StubMusicBrainzClient()
        enricher = MusicBrainzEnricher(request_delay=0.0, max_queries=4)
        enricher._load_client = lambda: client

        enriched = enricher.enrich(payload, current_candidate)

        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.artist, "Louis Armstrong")
        self.assertEqual(enriched.title, "A Kiss to Build a Dream On")
        self.assertEqual(enriched.source, "musicbrainz_confirmed")
        self.assertTrue(
            any(
                call.get("recording") == "A Kiss To Build A Dream On" and call.get("artist") == "Louis Armstrong"
                for call in client.calls
            )
        )
        self.assertTrue(all(call.get("release") != "Best Fallout Songs" for call in client.calls))

    def test_enricher_exposes_timeout_details_for_failed_lookup(self):
        payload = {
            "playlist_title": "",
            "source": {"author": "Example Artist", "title": "Example Song", "keywords": [], "description": ""},
            "normalization": {"title_analysis": {"lookup_title": "Example Song"}},
        }
        current_candidate = CandidateResolver().resolve(payload)

        client = _StubMusicBrainzClient()
        client.search_recordings = lambda **kwargs: (_ for _ in ()).throw(TimeoutError("timed out"))

        enricher = MusicBrainzEnricher(request_delay=0.0)
        enricher._load_client = lambda: client
        enricher._configure_client_network_limits = lambda: None

        enriched = enricher.enrich(payload, current_candidate)

        self.assertIsNone(enriched)
        self.assertEqual(enricher.last_lookup_details["status"], "query_failed")
        self.assertTrue(enricher.last_lookup_details["timed_out"])


if __name__ == "__main__":
    unittest.main()
