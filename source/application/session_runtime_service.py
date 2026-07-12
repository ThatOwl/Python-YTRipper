from __future__ import annotations

from pathlib import Path

from application.session_config_service import SessionConfigService
from application.state_models import SessionConfigState
from utility.logger import get_logger

logger = get_logger(__name__, "session_runtime_service_debug.log")


class SessionRuntimeService:
    """Mutable in-process session config state for the future web backend."""

    def __init__(
        self,
        *,
        config_service: SessionConfigService | None = None,
        initial_state: SessionConfigState | None = None,
    ):
        self.config_service = config_service or SessionConfigService()
        self._state = initial_state or self.config_service.read_state(apply_runtime=False)

    def get_state(self) -> SessionConfigState:
        options_copy = self.config_service.clone_options(self._state.options)
        return SessionConfigState(
            preferences=dict(self._state.preferences),
            options=options_copy,
            loaded_preset_path=self._state.loaded_preset_path,
        )

    def update_options(self, updates: dict[str, object]) -> SessionConfigState:
        cloned = self.config_service.clone_options(self._state.options)
        self.config_service.apply_updates(cloned, dict(updates or {}), apply_runtime=False)
        self._state.options = cloned
        self._state.preferences = cloned.to_dict()
        return self.get_state()

    def load_preset(self, preset_identifier: str) -> SessionConfigState:
        self._state = self.config_service.load_preset(
            preset_identifier,
            apply_runtime=False,
        )
        return self.get_state()

    def save_config(self, save_config_value: str) -> Path | None:
        save_path = self.config_service.resolve_save_config_path(
            save_config_value,
            loaded_preset_path=self._state.loaded_preset_path,
        )
        if save_path is None:
            return None

        self._state.preferences = self._state.options.to_dict()
        if not self.config_service.os.write_preferences(self._state.preferences, prefs_path=save_path):
            raise IOError(f"Failed to save config to {save_path}")
        return save_path
