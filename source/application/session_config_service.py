from __future__ import annotations

import argparse
from pathlib import Path

import utility.preferences as preferences
from application.state_models import SessionConfigState
from infrastructure.os_interactions import OSInteractions
from utility.logger import get_logger, set_visible_log_level
from utility.utils import (
    BOOLEAN_FALSE_VALUES,
    BOOLEAN_TRUE_VALUES,
    COMMON_AUDIO_ABR,
    COMMON_VIDEO_RESOLUTIONS,
    LOGLEVEL_ALIAS_MAP,
    QUALITY_ALIAS_MAP,
    DownloadOptions,
    parse_bool_string,
)

logger = get_logger(__name__, "session_config_service_debug.log")


class SessionConfigService:
    """Shared config/preset behavior for CLI and future GUI adapters."""

    def __init__(self, os_handler: OSInteractions | None = None):
        self.os = os_handler or OSInteractions()

    def read_state(
        self,
        prefs_path: Path | None = None,
        *,
        loaded_preset_path: Path | None = None,
        apply_runtime: bool = False,
    ) -> SessionConfigState:
        prefs = self.os.read_preferences(prefs_path=prefs_path)
        options = DownloadOptions.from_preferences(prefs)
        self.normalize_options(options, apply_runtime=apply_runtime)
        return SessionConfigState(
            preferences=prefs,
            options=options,
            loaded_preset_path=loaded_preset_path,
        )

    def load_preset(
        self,
        preset_identifier: str,
        *,
        apply_runtime: bool = False,
    ) -> SessionConfigState:
        preset_path = self.resolve_load_preset(preset_identifier)
        if preset_path is None:
            return self.read_state(apply_runtime=apply_runtime)
        return self.read_state(
            prefs_path=preset_path,
            loaded_preset_path=preset_path,
            apply_runtime=apply_runtime,
        )

    @staticmethod
    def list_available_presets() -> list[dict[str, str]]:
        presets: list[dict[str, str]] = []
        for preset_id, preset_path in enumerate(preferences.PATHS_TO_CUSTOM_PRESETS):
            presets.append(
                {
                    "id": str(preset_id),
                    "kind": "custom",
                    "label": f"Custom {preset_id}",
                    "path": str(preset_path),
                }
            )
        for preset_id, preset_path in preferences.PATHS_TO_IMMUTABLE_PRESETS.items():
            presets.append(
                {
                    "id": preset_id,
                    "kind": "immutable",
                    "label": preset_id,
                    "path": str(preset_path),
                }
            )
        return presets

    @staticmethod
    def clone_options(options: DownloadOptions) -> DownloadOptions:
        return DownloadOptions.from_preferences(options.to_dict())

    @staticmethod
    def parse_fps_preference(
        value: str | None,
        options: DownloadOptions,
    ) -> int:
        if value is None:
            return options.preferred_fps

        normalized = str(value).strip().lower()
        if normalized in ("", "0", "any", "none"):
            return 0
        if parse_bool_string(normalized):
            return 60
        return 30

    @staticmethod
    def resolve_load_preset(value: str | None) -> Path | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None

        if normalized.isdigit() and len(normalized) == 1:
            return preferences.PATHS_TO_CUSTOM_PRESETS[int(normalized)]

        preset_path = preferences.PATHS_TO_IMMUTABLE_PRESETS.get(normalized)
        if preset_path is not None:
            return preset_path

        raise ValueError("Unknown preset identifier. Use custom ids 0-9 or immutable presets ah/vh/vl/t.")

    @staticmethod
    def resolve_save_config_path(
        value: str | None,
        *,
        loaded_preset_path: Path | None = None,
    ) -> Path | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if not normalized or normalized in BOOLEAN_FALSE_VALUES:
            return None

        if normalized in BOOLEAN_TRUE_VALUES:
            if loaded_preset_path in preferences.PATHS_TO_CUSTOM_PRESETS:
                return loaded_preset_path

            if loaded_preset_path in preferences.PATHS_TO_IMMUTABLE_PRESETS.values():
                logger.warning(
                    "Loaded preset is immutable; -sc true will save the current "
                    "session options to the default config instead. Use -sc 0..9 "
                    "to save to a custom preset."
                )

            return preferences.PATH_TO_DEFAULT_PREFERENCES

        if normalized.isdigit() and len(normalized) == 1:
            return preferences.PATHS_TO_CUSTOM_PRESETS[int(normalized)]

        raise ValueError("Unknown save-config value. Use true/false or a custom preset id 0-9.")

    def apply_args(
        self,
        args: argparse.Namespace,
        options: DownloadOptions,
        *,
        apply_runtime: bool = False,
    ) -> DownloadOptions:
        updates: dict[str, object] = {}

        if getattr(args, "audio_only", None) is not None:
            updates["audio_only"] = parse_bool_string(args.audio_only)

        if getattr(args, "audio_mp3", None) is not None:
            updates["audio_mp3"] = parse_bool_string(args.audio_mp3)

        if getattr(args, "preferred_quality", None) is not None:
            updates["preferred_video_quality"] = args.preferred_quality
            updates["preferred_audio_quality"] = args.preferred_quality

        if getattr(args, "preferred_resolution", None) is not None:
            updates["preferred_resolution"] = args.preferred_resolution

        if getattr(args, "preferred_abr", None) is not None:
            updates["preferred_abr"] = args.preferred_abr

        if getattr(args, "high_fps", None) is not None:
            updates["preferred_fps"] = self.parse_fps_preference(args.high_fps, options)

        if getattr(args, "download_directory", None) is not None:
            updates["default_download_directory"] = self.os.expand_path(args.download_directory)

        if getattr(args, "show_preset", None) is not None:
            updates["show_preset"] = parse_bool_string(args.show_preset)

        if getattr(args, "no_dir_date", None) is not None:
            updates["no_dir_date"] = parse_bool_string(args.no_dir_date)

        if getattr(args, "visible_loglevel", None) is not None:
            updates["visible_loglevel"] = args.visible_loglevel

        if getattr(args, "autotag", None) is not None:
            updates["autotag"] = parse_bool_string(args.autotag)

        if getattr(args, "prepare_tagging", None) is not None:
            updates["prepare_tagging"] = parse_bool_string(args.prepare_tagging)

        if getattr(args, "save_results", None) is not None:
            updates["save_results"] = parse_bool_string(args.save_results)

        return self.apply_updates(
            options,
            updates,
            apply_runtime=apply_runtime,
        )

    def apply_updates(
        self,
        options: DownloadOptions,
        updates: dict[str, object],
        *,
        apply_runtime: bool = False,
    ) -> DownloadOptions:
        options.update_from_dict(updates)
        self.normalize_options(options, apply_runtime=apply_runtime)
        return options

    def normalize_options(self, options: DownloadOptions, apply_runtime: bool = False) -> None:
        self.normalize_boolean_options(options)
        if options.autotag:
            options.save_results = True
        self.normalize_quality_options(options)
        self.normalize_audio_bitrate(options)
        self.normalize_resolution(options)
        self.normalize_visible_loglevel(options)
        self.normalize_download_directory(options)

        if apply_runtime:
            self.apply_runtime_options(options)

    @staticmethod
    def normalize_boolean_options(options: DownloadOptions) -> None:
        boolean_fields = (
            "audio_only",
            "audio_mp3",
            "show_preset",
            "donotconvert",
            "no_dir_date",
            "autotag",
            "prepare_tagging",
            "save_results",
        )

        for field_name in boolean_fields:
            raw_value = getattr(options, field_name)

            if isinstance(raw_value, bool):
                continue

            normalized_value = None
            if isinstance(raw_value, str):
                normalized = raw_value.strip().lower()
                if normalized in BOOLEAN_TRUE_VALUES:
                    normalized_value = True
                elif normalized in BOOLEAN_FALSE_VALUES:
                    normalized_value = False
            elif raw_value in (0, 1):
                normalized_value = bool(raw_value)

            if normalized_value is None:
                fallback_value = preferences.DEFAULT_PREFS[field_name]
                logger.warning(
                    "Invalid boolean config for '%s': %r. Falling back to default %r.",
                    field_name,
                    raw_value,
                    fallback_value,
                )
                normalized_value = fallback_value

            setattr(options, field_name, normalized_value)

    def normalize_download_directory(self, options: DownloadOptions) -> None:
        if not options.default_download_directory:
            options.default_download_directory = str(
                self.os.expand_path("~/Downloads/RipperDownloads")
            )
            return

        options.default_download_directory = str(
            self.os.expand_path(options.default_download_directory)
        )

    @staticmethod
    def normalize_quality_options(options: DownloadOptions) -> None:
        if options.preferred_video_quality:
            raw_value = options.preferred_video_quality.strip().lower()
            mapped_quality = QUALITY_ALIAS_MAP.get(raw_value)
            if mapped_quality:
                options.preferred_video_quality = mapped_quality
            else:
                logger.warning(
                    "Unknown video quality alias '%s'; ignoring.",
                    options.preferred_video_quality,
                )
                options.preferred_video_quality = ""

        if options.preferred_audio_quality:
            raw_value = options.preferred_audio_quality.strip().lower()
            mapped_quality = QUALITY_ALIAS_MAP.get(raw_value)
            if mapped_quality:
                options.preferred_audio_quality = mapped_quality
            else:
                logger.warning(
                    "Unknown audio quality alias '%s'; ignoring.",
                    options.preferred_audio_quality,
                )
                options.preferred_audio_quality = ""

    @staticmethod
    def normalize_audio_bitrate(options: DownloadOptions) -> None:
        if not options.preferred_abr:
            return

        raw_value = options.preferred_abr.strip().lower()
        mapped_abr = COMMON_AUDIO_ABR.get(raw_value)
        if mapped_abr:
            options.preferred_abr = mapped_abr
        else:
            logger.warning("Unknown audio bitrate '%s'; ignoring.", options.preferred_abr)
            options.preferred_abr = ""

    @staticmethod
    def normalize_resolution(options: DownloadOptions) -> None:
        if not options.preferred_resolution:
            return

        raw_value = options.preferred_resolution.strip().lower()
        mapped_resolution = COMMON_VIDEO_RESOLUTIONS.get(raw_value)
        if mapped_resolution:
            options.preferred_resolution = mapped_resolution
        else:
            logger.warning("Unknown resolution '%s'; ignoring.", options.preferred_resolution)
            options.preferred_resolution = ""

    @staticmethod
    def normalize_visible_loglevel(options: DownloadOptions) -> None:
        raw_level = options.visible_loglevel or "WARNING"
        level_key = str(raw_level).strip().upper()
        mapped_level = LOGLEVEL_ALIAS_MAP.get(level_key)
        if mapped_level is None:
            logger.warning(
                "Unknown visible log level '%s'; falling back to WARNING.",
                raw_level,
            )
            mapped_level = "WARNING"
        options.visible_loglevel = mapped_level

    @staticmethod
    def apply_runtime_options(options: DownloadOptions) -> None:
        try:
            set_visible_log_level(options.visible_loglevel)
        except ValueError as exc:
            logger.error("Failed to set visible log level '%s': %s", options.visible_loglevel, exc)
