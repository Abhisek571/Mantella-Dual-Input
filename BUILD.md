# Build

## Backend override (Windows)

Install **CPython 3.11** and Git. You also need the original, supported Windows Mantella installation. No pip packages are required for this patch step.

Run in **Command Prompt**:

```bat
git clone https://github.com/Abhisek571/Mantella-duel-input.git
cd Mantella-duel-input
py -3.11 --version
py -3.11 -m unittest discover -s tests -v
py -3.11 setup_backend.py --original "C:\path\to\original\Mantella.exe"
```

Replace the example path with the original Mantella executable, not an already patched copy. The output is:

```text
SKSE/Plugins/MantellaSoftware/Mantella.exe
```

Setup checks the original executable, source files and resulting executable against `Source/backend/build-contract.json`. An unsupported executable is rejected; the original and your configuration are not changed. Do not disable these checks to make a different Mantella version install.

To run the integration test against your original executable:

```bat
set "MANTELLA_ORIGINAL=C:\path\to\original\Mantella.exe"
py -3.11 -m unittest discover -s tests -v
```

Without this variable, the real-executable test is skipped. These tests do not check microphone or in-game behavior.

## Recompile the game scripts (optional)

The release already includes compiled `.pex` files. To rebuild them, obtain:

- Skyrim Special Edition's Papyrus compiler and `TESV_Papyrus_Flags.flg` from the Creation Kit.
- Skyrim's base Papyrus sources, plus SKSE, SkyUI, UIExtensions and SKSE_HTTP script sources.
- The original [Mantella-Spell sources](https://github.com/art-from-the-machine/Mantella-Spell/tree/0c5f8513aff61cda1f32c81a962eee36ba74fdb7).

Extract dependency sources if they are archived; the compiler needs `.psc` imports, not just installed `.pex` files. Set the paths below to your source folders. Keep this repository's `Scripts\Source` first so its modified scripts take precedence.

Run from the repository root in **Command Prompt**:

```bat
set "COMPILER=C:\path\to\Papyrus Compiler\PapyrusCompiler.exe"
set "FLAGS=C:\path\to\TESV_Papyrus_Flags.flg"
set "IMPORTS=%CD%\Scripts\Source;C:\sources\Mantella;C:\sources\SKSE;C:\sources\Skyrim;C:\sources\SkyUI;C:\sources\UIExtensions;C:\sources\SKSE_HTTP"
mkdir build\Scripts
for %S in (MantellaRepository MantellaConversation MantellaMCM MantellaMCM_GeneralSettings) do "%COMPILER%" "%CD%\Scripts\Source\%S.psc" "-i=%IMPORTS%" "-o=%CD%\build\Scripts" "-f=%FLAGS%"
```

Use `%%S` instead of `%S` if saving that loop in a `.cmd` file. Require successful compilation of all four scripts and four new `.pex` files in `build\Scripts`; do not install partial output. Missing script/type errors mean the import set is incomplete. This dependency-based recipe is not a claim of byte-identical PEX reproduction: the release build used local compiler declarations, and PEX metadata can differ.

## Assemble a local MO2 override

1. Create a separate mod folder named **Mantella duel input**.
2. Copy `Scripts`, `meta.ini`, and the generated `SKSE` folder into it. If recompiling Papyrus, replace the four files in `Scripts` with your successful `build\Scripts` output.
3. Keep `Source`, `Licenses`, `LICENSE`, and `SOURCE-AND-LICENSES.txt` with the mod for source and notices.
4. Enable it after the original Mantella mod in MO2's left pane. Leave the original installed. Follow [INSTALL.txt](INSTALL.txt) for MCM setup and removal.

Do not distribute the locally generated executable without separately satisfying the licenses and source requirements of its bundled components. The public release intentionally distributes the patch sources and setup tool instead.

## Editing backend code

The setup tool reproduces the verified release, not arbitrary edited modules. Source hashes and the expected output hash are pinned in `Source/backend/build-contract.json`; edited source will be rejected. A development build must deliberately regenerate that contract and validate the resulting executable. This repository does not currently provide an automated contract-regeneration workflow or a full upstream Mantella rebuild; the instructions above rebuild the released override against its supported original.
