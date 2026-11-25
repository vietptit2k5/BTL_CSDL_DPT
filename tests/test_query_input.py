import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from PIL import Image
from nhom12.core import ContractError,load_settings
from nhom12.querying import SearchSession,read_query
from nhom12.file_snapshot import FrozenFiles


class QueryInput(unittest.TestCase):
    def test_cli_batch_reports_each_bad_image_and_nonzero_status(self):
        from nhom12.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            out=io.StringIO()
            with patch('sys.argv',['nhom12','query-batch','--images',str(Path(tmp)/'a.png'),str(Path(tmp)/'b.png')]),redirect_stdout(out):
                status=main()
            self.assertEqual(status,2)
            self.assertEqual([r['status'] for r in json.loads(out.getvalue())],['error','error'])

    def test_bad_input_fails_before_database_or_model(self):
        spec,cfg=load_settings();cfg['database']={'backend':'mysql'}
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/'bad.jpg';bad.write_bytes(b'not an image')
            with patch('nhom12.querying.revisions.ensure_tracking',side_effect=AssertionError('DB should not be touched')):
                with SearchSession(spec,cfg) as session:
                    with self.assertRaises(ContractError):session.query(bad)
                    with self.assertRaises(ContractError):session.query(Path(tmp)/'missing.png')
                    self.assertFalse(session.started)

    def test_exif_rotation_and_small_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rotated.jpg';image=Image.new('RGB',(30,10));exif=Image.Exif();exif[274]=6
            image.save(path,exif=exif)
            self.assertEqual(read_query(path)[1].size,(10,30))
            tiny=Path(tmp)/'tiny.png';Image.new('RGB',(1,1)).save(tiny)
            with self.assertRaises(ContractError):read_query(tiny)

    @unittest.skipUnless(os.name=='nt','Windows sharing semantics')
    def test_read_lease_blocks_writes_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.bin';path.write_bytes(b'original')
            lease=FrozenFiles([path])
            try:
                self.assertEqual(path.read_bytes(),b'original')
                with self.assertRaises(PermissionError):path.write_bytes(b'changed!')
            finally:lease.close()
            path.write_bytes(b'changed!')
