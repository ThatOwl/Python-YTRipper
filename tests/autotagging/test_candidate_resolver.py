import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.core.candidate_resolver import CandidateResolver


class TestCandidateResolver(unittest.TestCase):
    def test_prefers_explicit_youtube_metadata(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Ignored Playlist",
            "source": {
                "metadata": {
                    "music": {
                        "artist": "Odd Chap",
                        "song": "Swing Theory",
                        "album": "Electro Swing Essentials",
                    }
                }
            },
            "normalization": {},
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Odd Chap")
        self.assertEqual(candidate.title, "Swing Theory")
        self.assertEqual(candidate.album, "Electro Swing Essentials")
        self.assertEqual(candidate.source, "youtube_metadata")
        self.assertTrue(candidate.write_allowed)

    def test_author_matched_title_analysis_is_auto_writable(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Electro Swing",
            "source": {"author": "Caro Emerald"},
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Caro Emerald",
                    "guessed_title": "Tangled Up Odd Chap Bootleg",
                    "split_confidence": "author_matched_left",
                    "lookup_title": "Tangled Up Odd Chap Bootleg",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Caro Emerald")
        self.assertEqual(candidate.title, "Tangled Up Odd Chap Bootleg")
        self.assertEqual(candidate.album, "")
        self.assertEqual(candidate.source, "title_author_match")
        self.assertTrue(candidate.write_allowed)

    def test_unconfirmed_dash_split_stays_non_destructive(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Electro Swing",
            "source": {"author": "Unrelated Channel"},
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Odd Chap, Alanna Lyes",
                    "guessed_title": "Blaze Electro Swing",
                    "split_confidence": "dash_split",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertFalse(candidate.write_allowed)
        self.assertEqual(candidate.source, "title_dash_split")

    def test_official_uploader_alias_upgrades_clean_dash_split_to_auto_writable(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Rammstein_Mix",
            "source": {
                "author": "Rammstein Official",
                "title": "Rammstein - Ich Will (Official Video)",
                "keywords": [
                    "Rammstein",
                    "Ich Will",
                    "Official Video",
                ],
                "description": "Single: Ich Will\nFrom the album: Mutter",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Rammstein",
                    "guessed_title": "Ich Will",
                    "split_confidence": "dash_split",
                    "lookup_title": "Rammstein - Ich Will",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Rammstein")
        self.assertEqual(candidate.title, "Ich Will")
        self.assertEqual(candidate.album, "Mutter")
        self.assertEqual(candidate.source, "description_structured")
        self.assertTrue(candidate.write_allowed)
        self.assertGreaterEqual(candidate.confidence, 0.9)

    def test_description_release_parsing_makes_official_audio_auto_writable(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Rammstein_Mix",
            "source": {
                "author": "RHINO",
                "title": "Black Sabbath - Paranoid (Official Audio)",
                "keywords": [
                    "black sabbath",
                    "paranoid",
                ],
                "description": (
                    "You're listening to the official audio for Black Sabbath - \"Paranoid\" "
                    "from the album 'Paranoid' (1970)."
                ),
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Black Sabbath",
                    "guessed_title": "Paranoid",
                    "split_confidence": "dash_split",
                    "lookup_title": "Black Sabbath - Paranoid",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Black Sabbath")
        self.assertEqual(candidate.title, "Paranoid")
        self.assertEqual(candidate.album, "Paranoid")
        self.assertEqual(candidate.source, "description_structured")
        self.assertTrue(candidate.write_allowed)

    def test_topic_channel_release_description_beats_title_only_musicbrainz_path(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Rammstein_Mix",
            "source": {
                "author": "Rammstein - Topic",
                "title": "Reise, Reise",
                "keywords": [
                    "Rammstein",
                    "Reise, Reise",
                ],
                "description": (
                    "Provided to YouTube by Universal Music Group\n\n"
                    "Reise, Reise · Rammstein\n\n"
                    "Reise, Reise\n\n"
                    "℗ 2004 Vertigo/Capitol"
                ),
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "",
                    "guessed_title": "",
                    "split_confidence": "",
                    "lookup_title": "Reise, Reise",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Rammstein")
        self.assertEqual(candidate.title, "Reise, Reise")
        self.assertEqual(candidate.album, "Reise, Reise")
        self.assertEqual(candidate.source, "description_structured")
        self.assertTrue(candidate.write_allowed)

    def test_collaboration_title_is_auto_writable_when_author_and_keywords_support_artists(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "The Tech Thieves",
            "source": {
                "author": "Besomorph",
                "title": "Besomorph & The Tech Thieves - Anxiety [Lyric Video]",
                "keywords": [
                    "Besomorph",
                    "the tech thieves",
                    "anxiety",
                ],
                "description": "Stream & Download Anxiety",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Besomorph & The Tech Thieves",
                    "guessed_title": "Anxiety",
                    "split_confidence": "dash_split",
                    "lookup_title": "Besomorph & The Tech Thieves - Anxiety",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Besomorph & The Tech Thieves")
        self.assertEqual(candidate.title, "Anxiety")
        self.assertEqual(candidate.source, "title_uploader_match")
        self.assertTrue(candidate.write_allowed)

    def test_description_song_by_artist_recovers_fan_upload_pair(self):
        resolver = CandidateResolver()
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
                "description": "A Kiss To Build A Dream On by Louis Armstrong",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "A Kiss To Build A Dream On",
                    "guessed_title": "Louis Armstrong",
                    "split_confidence": "dash_split",
                    "lookup_title": "A Kiss To Build A Dream On - Louis Armstrong",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Louis Armstrong")
        self.assertEqual(candidate.title, "A Kiss To Build A Dream On")
        self.assertEqual(candidate.source, "description_structured")
        self.assertTrue(candidate.write_allowed)

    def test_contextual_dash_split_is_blocked_from_auto_writing_fake_artist(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Best Fallout Songs",
            "source": {
                "author": "Człowiek Drzewo",
                "title": "Fallout 76 - Take Me Home, Country Roads (Original Trailer Soundtrack)",
                "keywords": [
                    "Fallout 76",
                    "Soundtrack",
                    "OST",
                    "HQ",
                    "Trailer",
                    "Song",
                ],
                "description": "Buy the song on iTunes and support the Habitat for Humanity charity.",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Fallout 76",
                    "guessed_title": "Take Me Home, Country Roads",
                    "split_confidence": "dash_split",
                    "lookup_title": "Fallout 76 - Take Me Home, Country Roads",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "")
        self.assertEqual(candidate.title, "Take Me Home, Country Roads")
        self.assertEqual(candidate.source, "contextual_dash_split")
        self.assertFalse(candidate.write_allowed)

    def test_reverse_hint_does_not_override_author_matched_title(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "The Tech Thieves",
            "source": {
                "author": "The Tech Thieves",
                "title": "The Tech Thieves - Before You Go",
                "keywords": [
                    "The Tech Thieves",
                    "Before You Go",
                ],
                "description": "",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "The Tech Thieves",
                    "guessed_title": "Before You Go",
                    "split_confidence": "author_matched_left",
                    "lookup_title": "The Tech Thieves - Before You Go",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "The Tech Thieves")
        self.assertEqual(candidate.title, "Before You Go")
        self.assertEqual(candidate.source, "title_author_match")
        self.assertTrue(candidate.write_allowed)

    def test_generic_uploaded_by_description_is_not_treated_as_song_metadata(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Best Fallout Songs",
            "source": {
                "author": "Dagre",
                "title": "Fallout New Vegas Radio - In The Shadow Of The Valley",
                "keywords": [
                    "Fallout",
                    "New",
                    "Vegas",
                    "OST",
                ],
                "description": (
                    'Songs from the game "Fallout New Vegas"\\n'
                    "Uploaded by a fan due of the incredible lack of these awesome songs."
                ),
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Fallout New Vegas Radio",
                    "guessed_title": "In The Shadow Of The Valley",
                    "split_confidence": "dash_split",
                    "lookup_title": "Fallout New Vegas Radio - In The Shadow Of The Valley",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.source, "contextual_dash_split")
        self.assertFalse(candidate.write_allowed)

    def test_accented_uploader_alias_still_confirms_collaboration_artist(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Today's Hits",
            "source": {
                "author": "ROSÉ",
                "title": "ROSÉ & Bruno Mars - APT. (Official Music Video)",
                "keywords": [
                    "Rosé",
                    "bruno mars",
                    "APT.",
                    "apt",
                ],
                "description": "ROSÉ & Bruno Mars - APT.",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "ROSE & Bruno Mars",
                    "guessed_title": "APT.",
                    "split_confidence": "dash_split",
                    "lookup_title": "ROSE & Bruno Mars - APT.",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "ROSE & Bruno Mars")
        self.assertEqual(candidate.title, "APT.")
        self.assertEqual(candidate.source, "title_uploader_match")
        self.assertTrue(candidate.write_allowed)

    def test_title_by_pattern_does_not_hijack_song_titles_with_by_inside_name(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "House Music 2025",
            "source": {
                "author": "Robin Schulz",
                "title": "Robin Schulz & Topic ft. Oaks - One By One (Official Music Video)",
                "keywords": [
                    "Robin Schulz",
                    "Topic",
                    "Oaks",
                    "One By One",
                ],
                "description": "Listen to One By One now.",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Robin Schulz & Topic ft. Oaks",
                    "guessed_title": "One By One",
                    "split_confidence": "dash_split",
                    "lookup_title": "Robin Schulz & Topic ft. Oaks - One By One",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Robin Schulz & Topic ft. Oaks")
        self.assertEqual(candidate.title, "One By One")
        self.assertEqual(candidate.source, "title_uploader_match")
        self.assertTrue(candidate.write_allowed)

    def test_prod_by_suffix_is_not_misread_as_title_by_artist(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Top 100 Germany",
            "source": {
                "author": "385idéal",
                "title": "Amo x Aymen - Love all night (prod. by SVRN BEATS) [official video]",
                "keywords": [
                    "Amo",
                    "Aymen",
                    "Love all night",
                ],
                "description": 'Das offizielle Video zur Single "Love all night" von Amo x Aymen.',
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Amo x Aymen",
                    "guessed_title": "Love all night prod. by SVRN BEATS",
                    "split_confidence": "dash_split",
                    "lookup_title": "Amo x Aymen - Love all night prod. by SVRN BEATS",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertNotEqual(candidate.source, "title_by_pattern")
        self.assertEqual(candidate.artist, "Amo x Aymen")
        self.assertIn(candidate.title, {"Love all night", "Love all night prod. by SVRN BEATS"})

    def test_keyword_supported_label_channel_split_can_be_auto_writable(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "House Music 2025",
            "source": {
                "author": "Spinnin' Records",
                "title": "VINAI - Rise Up (feat. Vamero) [Official Lyric Video]",
                "keywords": [
                    "vinai",
                    "rise up",
                    "vamero",
                    "vinai rise up feat vamero",
                ],
                "description": "VINAI - Rise Up (feat. Vamero) is OUT NOW!",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "VINAI",
                    "guessed_title": "Rise Up feat. Vamero",
                    "split_confidence": "dash_split",
                    "lookup_title": "VINAI - Rise Up feat. Vamero",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "VINAI")
        self.assertEqual(candidate.title, "Rise Up feat. Vamero")
        self.assertEqual(candidate.source, "title_keyword_match")
        self.assertTrue(candidate.write_allowed)

    def test_music_video_by_performing_description_is_trusted(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Today's Hits",
            "source": {
                "author": "PostMaloneVEVO",
                "title": "Post Malone - I Had Some Help (feat. Morgan Wallen) (Official Video)",
                "keywords": [
                    "Post Malone",
                    "Morgan Wallen",
                    "Country",
                ],
                "description": "Music video by Post Malone performing I Had Some Help.",
            },
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Post Malone",
                    "guessed_title": "I Had Some Help feat. Morgan Wallen",
                    "split_confidence": "dash_split",
                    "lookup_title": "Post Malone - I Had Some Help feat. Morgan Wallen",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Post Malone")
        self.assertEqual(candidate.title, "I Had Some Help")
        self.assertEqual(candidate.source, "description_structured")
        self.assertTrue(candidate.write_allowed)


if __name__ == "__main__":
    unittest.main()
