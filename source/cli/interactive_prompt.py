import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import utility.preferences as preferences
from utility.logger import get_logger
from utility.utils import COMMON_AUDIO_ABR, COMMON_VIDEO_RESOLUTIONS, QUALITY_ALIAS_MAP

logger = get_logger(__name__, "interactive_prompt_debug.log")

BOOLEAN_SUGGESTIONS = ("true", "false")
FPS_SUGGESTIONS = ("true", "false", "0", "any", "none")
LOGLEVEL_SUGGESTIONS = ("debug", "info", "warning", "error", "critical")
PRESET_SUGGESTIONS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "ah", "vh", "vl", "test", "ds")
QUALITY_SUGGESTIONS = tuple(sorted(set(QUALITY_ALIAS_MAP.values())))
SCAN_SCOPE_SUGGESTIONS = ("missing-any", "untagged", "missing-artist", "missing-title", "all")
OVERWRITE_MODE_SUGGESTIONS = ("missing", "all")
PATH_FLAGS = {"-f", "--file", "-o", "--download_directory", "--directory", "--report-csv", "--csv", "--queue-dir"}
FLAG_VALUE_SUGGESTIONS = {
    "-a": BOOLEAN_SUGGESTIONS,
    "--audio_only": BOOLEAN_SUGGESTIONS,
    "-a3": BOOLEAN_SUGGESTIONS,
    "--audio_mp3": BOOLEAN_SUGGESTIONS,
    "-q": QUALITY_SUGGESTIONS,
    "--preferred_quality": QUALITY_SUGGESTIONS,
    "-r": tuple(COMMON_VIDEO_RESOLUTIONS.keys()),
    "--preferred_resolution": tuple(COMMON_VIDEO_RESOLUTIONS.keys()),
    "-au": tuple(COMMON_AUDIO_ABR.keys()),
    "--preferred_abr": tuple(COMMON_AUDIO_ABR.keys()),
    "-hf": FPS_SUGGESTIONS,
    "--high_fps": FPS_SUGGESTIONS,
    "-lp": PRESET_SUGGESTIONS,
    "-ld": PRESET_SUGGESTIONS,
    "--load_preset": PRESET_SUGGESTIONS,
    "-sc": PRESET_SUGGESTIONS + BOOLEAN_SUGGESTIONS,
    "--save-config": PRESET_SUGGESTIONS + BOOLEAN_SUGGESTIONS,
    "-sp": BOOLEAN_SUGGESTIONS,
    "--show_preset": BOOLEAN_SUGGESTIONS,
    "-nd": BOOLEAN_SUGGESTIONS,
    "--no_dir_date": BOOLEAN_SUGGESTIONS,
    "-at": BOOLEAN_SUGGESTIONS,
    "--autotag": BOOLEAN_SUGGESTIONS,
    "--prepare-tagging": BOOLEAN_SUGGESTIONS,
    "-sr": BOOLEAN_SUGGESTIONS,
    "--save-results": BOOLEAN_SUGGESTIONS,
    "-vl": LOGLEVEL_SUGGESTIONS,
    "--visible-loglevel": LOGLEVEL_SUGGESTIONS,
    "--scan-scope": SCAN_SCOPE_SUGGESTIONS,
    "--overwrite-mode": OVERWRITE_MODE_SUGGESTIONS,
}


def _tokenize_for_completion(text: str) -> list[str]:
    try:
        lexer = shlex.shlex(text, posix=False)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return text.split()


@dataclass(frozen=True)
class CompletionContext:
    prior_tokens: tuple[str, ...]
    current_token: str
    active_flag: str | None

    @property
    def expects_path(self) -> bool:
        return self.active_flag in PATH_FLAGS

    @property
    def expects_value(self) -> bool:
        return self.active_flag in FLAG_VALUE_SUGGESTIONS

    @property
    def wants_flag_suggestions(self) -> bool:
        return self.current_token.startswith("-") or not self.current_token


def parse_completion_context(text_before_cursor: str) -> CompletionContext:
    tokens = _tokenize_for_completion(text_before_cursor)

    if text_before_cursor.endswith((" ", "\t")):
        prior_tokens = tuple(tokens)
        current_token = ""
    elif tokens:
        prior_tokens = tuple(tokens[:-1])
        current_token = tokens[-1]
    else:
        prior_tokens = ()
        current_token = ""

    active_flag = prior_tokens[-1] if prior_tokens and prior_tokens[-1].startswith("-") else None
    return CompletionContext(
        prior_tokens=prior_tokens,
        current_token=current_token,
        active_flag=active_flag,
    )


class InteractivePrompt:
    def __init__(
        self,
        parser_getter: Callable[[], argparse.ArgumentParser],
        prompt_label: str = "yt-ripper> ",
        history_path: Path | None = None,
    ) -> None:
        self._parser_getter = parser_getter
        self.prompt_label = prompt_label
        self.history_path = history_path or (preferences.CONFIG_DIR / "yt_ripper_history.txt")
        self.uses_prompt_toolkit = False
        self._session = None
        self._fallback_notice_shown = False

        if self._can_use_prompt_toolkit():
            self._session = self._build_prompt_toolkit_session()
            self.uses_prompt_toolkit = self._session is not None

    def prompt(self) -> str:
        if self._session is not None:
            return self._session.prompt(
                self.prompt_label,
                auto_suggest=self._build_auto_suggest(),
                enable_history_search=True,
            )

        self._log_fallback_once()
        return input(self.prompt_label)

    def _can_use_prompt_toolkit(self) -> bool:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return False

        try:
            import prompt_toolkit  # noqa: F401
        except ImportError:
            return False

        return True

    def _build_prompt_toolkit_session(self):
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
        except ImportError:
            return None

        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        return PromptSession(
            history=FileHistory(str(self.history_path)),
            completer=_ParserAwareCompleter(self._parser_getter),
            complete_while_typing=True,
        )

    def _build_auto_suggest(self):
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        return AutoSuggestFromHistory()

    def _log_fallback_once(self) -> None:
        if self._fallback_notice_shown:
            return

        logger.info(
            "Interactive prompt is using basic input fallback. "
            "Install prompt_toolkit and run in a TTY for history search and completions."
        )
        self._fallback_notice_shown = True


class _ParserAwareCompleter:
    def __init__(self, parser_getter: Callable[[], argparse.ArgumentParser]) -> None:
        from prompt_toolkit.completion import PathCompleter

        self._parser_getter = parser_getter
        self._path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        from prompt_toolkit.completion import Completion
        from prompt_toolkit.document import Document

        context = parse_completion_context(document.text_before_cursor)
        token_prefix = context.current_token.lstrip("\"'").lower()

        if context.expects_path:
            path_document = Document(
                text=context.current_token,
                cursor_position=len(context.current_token),
            )
            yield from self._path_completer.get_completions(path_document, complete_event)
            return

        if context.expects_value:
            for value in FLAG_VALUE_SUGGESTIONS[context.active_flag]:
                if value.lower().startswith(token_prefix):
                    yield Completion(value, start_position=-len(context.current_token))
            return

        if not context.wants_flag_suggestions:
            return

        for option in self._collect_option_strings():
            if option.startswith(context.current_token):
                yield Completion(option, start_position=-len(context.current_token))

    async def get_completions_async(self, document, complete_event):
        for completion in self.get_completions(document, complete_event):
            yield completion

    def _collect_option_strings(self) -> tuple[str, ...]:
        parser = self._parser_getter()
        option_strings: list[str] = []

        for action in parser._actions:
            for option in action.option_strings:
                option_strings.append(option)

        return tuple(dict.fromkeys(option_strings))
