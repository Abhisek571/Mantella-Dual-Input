"""One-time installer for Mantella Dual Input. Requires Python 3.11."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent


def build(original, output, root=ROOT):
    if sys.version_info[:2] != (3, 11):
        raise ValueError('Use Python 3.11 to match the Mantella runtime.')
    original, output, root = Path(original).resolve(), Path(output).resolve(), Path(root).resolve()
    if original == output or (output.exists() and original.samefile(output)):
        raise ValueError('Refusing to replace the original Mantella executable.')
    sys.path.insert(0, str(root / 'Source/backend'))
    from frozen_patch import compile_source, patch_executable, sha256
    contract = json.loads((root / 'Source/backend/build-contract.json').read_text(encoding='utf-8'))
    replacements = {}
    for name, item in contract['modules'].items():
        source_path = (root / 'Source/backend' / item['source']).resolve()
        if not source_path.is_relative_to(root / 'Source/backend'):
            raise ValueError('Invalid source path.')
        source = source_path.read_bytes()
        if sha256(source) != item['sha256']:
            raise ValueError('Modified source file: ' + item['source'])
        replacements[name] = compile_source(source, item['compile_filename'])
    from frozen_patch import parse_carchive, parse_pyz, code_fingerprint
    raw = original.read_bytes()
    if sha256(raw) != contract['original_sha256']:
        raise ValueError('Unsupported Mantella executable. Nothing changed.')
    pyz = parse_pyz(parse_carchive(raw).entry_data('PYZ.pyz'))
    gates = {name: code_fingerprint(pyz.code(name)) for name in replacements if name in pyz.toc}
    data, report = patch_executable(raw, replacements=replacements, expected_exe_sha256=contract['original_sha256'], expected_module_fingerprints=gates)
    if sha256(data) != contract['patched_sha256']:
        raise ValueError('Built executable does not match the verified release. Nothing changed.')
    output.parent.mkdir(parents=True, exist_ok=True)
    import os, tempfile
    fd, temporary = tempfile.mkstemp(prefix='.mdi-', suffix='.tmp', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        Path(temporary).replace(output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, help='Path to the original Mantella.exe')
    args = parser.parse_args()
    output = ROOT / 'SKSE/Plugins/MantellaSoftware/Mantella.exe'
    original = args.original
    if original is None:
        candidates = [p for p in ROOT.parent.glob('*/SKSE/Plugins/MantellaSoftware/Mantella.exe') if p.resolve() != output.resolve()]
        if len(candidates) == 1:
            original = candidates[0]
        else:
            raw = input('Full path to ORIGINAL Mantella.exe (not the Dual Input copy): ').strip().strip('"')
            if not raw:
                raise ValueError('No original executable selected. Nothing changed.')
            original = Path(raw)
    build(original, output)
    print('Mantella Dual Input v1.1 backend ready: ' + str(output))
    print('Original Mantella and your settings were not changed.')
    print('Enable this mod after Mantella in MO2, then start a new conversation.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as error:
        print('Setup stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
