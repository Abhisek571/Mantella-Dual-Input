# Mantella duel input

Type or speak in the same Mantella conversation, with separate configurable keys.

## Install

1. Download the ZIP from [Releases](https://github.com/Abhisek571/Mantella-duel-input/releases/latest) and install it as a separate MO2 mod, after Mantella.
2. Open the mod folder and run **Setup Backend.cmd** with **Python 3.11** installed. Select the original Mantella executable if prompted.
3. Enable the mod. In Mantella's MCM, enable **Duel Input**, set **Type Reply** and **Speak Reply**, then start a new conversation.

Requires a working Mantella installation and its dependencies. Setup supports one exact Windows backend build and rejects others. It creates a patched copy without changing the original or your settings. See [INSTALL.txt](INSTALL.txt) for compatibility and removal.

**Limits:** Windows keyboard only; VR/controllers are untested. Immediate cancellation of speech capture is not fully implemented.

## Source and license

Unofficial patch of [Mantella](https://github.com/art-from-the-machine/Mantella). Backend changes and setup tools use **AGPL-3.0-or-later**; game scripts retain Mantella's **MIT** license. Source and original notices are included; see [SOURCE-AND-LICENSES.txt](SOURCE-AND-LICENSES.txt).

No Mantella executable, voice models, or personal configuration is bundled.
