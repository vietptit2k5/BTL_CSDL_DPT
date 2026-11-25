import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nhom12.core import ContractError, digest, file_hash
from nhom12.provenance import archive_sources, check_extraction


class Provenance(unittest.TestCase):
    def test_certified_archive_accepts_storage_changes_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive_sources(root)
            manifest = json.loads((root / 'implementation_sources.json').read_text())
            recorded = digest(manifest)
            with patch('nhom12.building.implementation_hash', return_value='storage-only-change'):
                proof = check_extraction(root, recorded)
                self.assertEqual(proof['mode'], 'verified_extraction_archive')
                source = root / 'implementation_sources' / 'features.py'
                source.write_text('changed', encoding='utf-8')
                with self.assertRaisesRegex(ContractError, 'damaged'):
                    check_extraction(root, recorded)
