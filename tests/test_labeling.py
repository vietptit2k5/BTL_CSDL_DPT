"""Blind form validation must preserve IDs and never invent or reveal labels."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('blind_form_check',Path(__file__).resolve().parents[1]/'scripts/labels/check.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


class LabelForms(unittest.TestCase):
    def test_partial_is_not_a_complete_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'form.csv'
            path.write_text('anh,lop,muc_do,ghi_chu\nX01.jpg,,,\n',encoding='utf-8-sig')
            self.assertEqual(check.validate(path,['X01.jpg'],partial=True)['completed'],0)
            with self.assertRaises(ValueError):check.validate(path,['X01.jpg'])

    def test_valid_notes_roundtrip_and_ambiguous_reason_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'form.csv'
            def write(notes):
                with path.open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.writer(f);w.writerow(check.FIELDS);w.writerow(['X01.jpg','KHONG_RO','phan_van',notes])
            write('Núi, hồ;\nkhó chọn "chủ thể"')
            self.assertEqual(check.validate(path,['X01.jpg'])['completed'],1)
            write('')
            with self.assertRaises(ValueError):check.validate(path,['X01.jpg'])

    def test_wrong_duplicate_or_missing_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'form.csv'
            for content in ('X01.jpg,SEA,chac,\nX01.jpg,SEA,chac,\n','X02.jpg,SEA,chac,\n'):
                path.write_text('anh,lop,muc_do,ghi_chu\n'+content,encoding='utf-8')
                with self.assertRaises(ValueError):check.validate(path,['X01.jpg'])


if __name__=='__main__':unittest.main()
