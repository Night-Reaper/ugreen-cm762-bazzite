import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ArchiveSafetyTests(unittest.TestCase):
    def invoke(self, archive, output):
        with patch('sys.argv', ['build.py', str(archive), '--prepare-only', '--output', str(output)]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                builder.main()
            self.assertEqual(result.exception.code, 2)

    def test_unknown_archive_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'unknown.zip'
            archive.write_bytes(b'not the verified vendor archive')
            self.invoke(archive, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_traversal_rejected_even_if_hash_were_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('../escape', 'must not be written')
            with patch.object(builder, 'ARCHIVE_SHA256', builder.digest(archive)):
                self.invoke(archive, root / 'output')
            self.assertFalse((root / 'escape').exists())
            self.assertFalse((root / 'output').exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'fixture.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('dummy', 'fixture')
            output = root / 'output'
            output.mkdir()
            sentinel = output / 'keep.txt'
            sentinel.write_text('keep')
            with patch.object(builder, 'ARCHIVE_SHA256', builder.digest(archive)):
                self.invoke(archive, output)
            self.assertEqual(sentinel.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
