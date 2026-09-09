# SPDX-License-Identifier: AGPL-3.0-or-later
# Added for Mantella duel input; released as v1.0 on 2026-09-09.
# Source target: Mantella v0.14 (c5449f3c8b081c722212c496c298c16277394ae1).
"""Small, source-only adapter for explicit one-shot dual-input capture."""

from __future__ import annotations

from typing import Any


class DualInputConfigProxy:
    """Read-only view that changes only per-Transcriber microphone modes."""

    __slots__ = ("__wrapped",)

    def __init__(self, wrapped: Any) -> None:
        object.__setattr__(self, "_DualInputConfigProxy__wrapped", wrapped)

    @property
    def ptt_enabled(self) -> bool:
        return False

    @property
    def proactive_mic_mode(self) -> bool:
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped, name)


def dual_input_silence_timeout(config: Any) -> float:
    """Return a positive no-speech bound supported by v0.14 Transcriber."""
    for name in ("silence_auto_response_timeout", "listen_timeout"):
        try:
            value = float(getattr(config, name))
        except (AttributeError, TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 15.0


def capture_dual_input_once(transcriber: Any, prompt: str, silence_timeout: float) -> str | None:
    """Capture once and finish microphone cleanup before returning or raising."""
    try:
        transcriber.start_listening(prompt)
        return transcriber.get_latest_transcription(silence_timeout=silence_timeout)
    finally:
        transcriber.stop_listening()


# Explicit offline diagnostic: exits before Mantella initialises configuration.
# The test double exercises adapter ordering, NOT physical device behaviour.
import sys
if "--mdi-self-test" in sys.argv:
    import json
    from types import SimpleNamespace
    class _DiagnosticTranscriber:
        def __init__(self):
            self.calls = []
        def start_listening(self, prompt):
            self.calls.append("start")
        def get_latest_transcription(self, silence_timeout):
            self.calls.append("read")
            return "adapter diagnostic fixture"
        def stop_listening(self):
            self.calls.append("stop")
    transcriber = _DiagnosticTranscriber()
    value = capture_dual_input_once(transcriber, "", 1.0)
    original = SimpleNamespace(ptt_enabled=True, proactive_mic_mode=True)
    view = DualInputConfigProxy(original)
    passed = (value == "adapter diagnostic fixture"
              and transcriber.calls == ["start", "read", "stop"]
              and not view.ptt_enabled and not view.proactive_mic_mode
              and original.ptt_enabled and original.proactive_mic_mode)
    print(json.dumps({"name": "Mantella duel input", "version": "0.1.0-prototype",
                      "adapter_cleanup_test": passed, "microphone_opened": False,
                      "gameplay_validated": False, "frozen": bool(getattr(sys, "frozen", False))}), flush=True)
    raise SystemExit(0 if passed else 1)
