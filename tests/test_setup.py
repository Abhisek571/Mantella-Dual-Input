"""Run with Python 3.11: python -m unittest discover -s tests -v.

Set MANTELLA_ORIGINAL to enable the real executable build test.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup_backend


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / 'Source', self.root / 'Source')
        self.contract_path = self.root / 'Source/backend/build-contract.json'
        self.contract = json.loads(self.contract_path.read_text())
        self.original = self.root / 'original.exe'
        self.original.write_bytes(b'unsupported test fixture')
        self.output = self.root / 'output/Mantella.exe'

    def test_rejects_original_as_output(self):
        before = self.original.read_bytes()
        with self.assertRaisesRegex(ValueError, 'original'):
            setup_backend.build(self.original, self.original, self.root)
        self.assertEqual(self.original.read_bytes(), before)

    def test_rejects_unsupported_input(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            setup_backend.build(self.original, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_rejects_tampered_source(self):
        (self.root / 'Source/backend/src/dual_input.py').write_text('pass\n')
        with self.assertRaisesRegex(ValueError, 'source'):
            setup_backend.build(self.original, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_rejects_source_path_escape(self):
        next(iter(self.contract['modules'].values()))['source'] = '../outside.py'
        self.contract_path.write_text(json.dumps(self.contract))
        with self.assertRaisesRegex(ValueError, 'source path'):
            setup_backend.build(self.original, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_preserves_existing_output_on_failure(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b'existing')
        with self.assertRaises(ValueError):
            setup_backend.build(self.original, self.output, self.root)
        self.assertEqual(self.output.read_bytes(), b'existing')

    @unittest.skipUnless(os.environ.get('MANTELLA_ORIGINAL'), 'Set MANTELLA_ORIGINAL for build test')
    def test_build_matches_release_and_preserves_original(self):
        original = Path(os.environ['MANTELLA_ORIGINAL'])
        before = sha(original)
        setup_backend.build(original, self.output, self.root)
        self.assertEqual(sha(self.output), self.contract['patched_sha256'])
        self.assertEqual(sha(original), before)


if __name__ == '__main__':
    unittest.main()
