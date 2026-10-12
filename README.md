# Mantella Dual Input

Type or speak in the same Mantella conversation, with separate configurable keys.

For **Mantella 0.14** (the current Nexus release).

## Install

1. Download the ZIP from [Releases](https://github.com/Abhisek571/Mantella-Dual-Input/releases/latest) and install it as a separate MO2 mod, after Mantella.
2. Open the mod folder and run **Setup Backend.cmd** with **Python 3.11** installed. Select the original Mantella executable if prompted.
3. Enable the mod. In Mantella's MCM, enable **Dual Input**, set **Type Reply** and **Speak Reply**, then start a new conversation.

Requires a working Mantella installation and its dependencies. Setup supports one exact Windows backend build and rejects others. It creates a patched copy without changing the original or your settings. See [INSTALL.txt](INSTALL.txt) for compatibility and removal.

**Limits:** Windows keyboard only; VR/controllers are untested. A speech capture that has started can't be cancelled; it ends when you stop talking or after the silence timeout.

## Changes

**1.1**
- The Speak Reply model now loads once instead of every conversation.
- "No speech heard" message when Speak Reply hears nothing.
- Turning Dual Input on or off mid-conversation no longer disables a key until the conversation ends.
- The Listen action's longer pause now works with Speak Reply.
- Mantella's MCM keeps its own name and version number, so future Mantella updates apply their settings normally.
- Renamed from "Mantella duel input".

**1.0**
- First release.

## Build

See [BUILD.md](BUILD.md) for Python 3.11 setup, backend build commands, tests, optional Papyrus compilation, and MO2 assembly.

## Source and license

Unofficial patch of [Mantella](https://github.com/art-from-the-machine/Mantella). Backend changes and setup tools use **AGPL-3.0-or-later**; game scripts retain Mantella's **MIT** license. Source and original notices are included; see [SOURCE-AND-LICENSES.txt](SOURCE-AND-LICENSES.txt).

No Mantella executable, voice models, or personal configuration is bundled.
