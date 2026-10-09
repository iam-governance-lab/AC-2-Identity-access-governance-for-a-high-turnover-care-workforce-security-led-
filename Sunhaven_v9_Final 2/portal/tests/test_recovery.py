"""Offline recovery must reject damage and never replace an existing destination."""
import json,tempfile
from pathlib import Path
from unittest.mock import patch
from test_web import WebTests
import recovery

class RecoveryTests(WebTests):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/'backup';out=Path(d)/'restored'
            self.assertEqual(recovery.create_bundle(b)['status'],'PASS')
            self.assertEqual(recovery.restore_bundle(b,out)['status'],'PASS')
            self.assertTrue((out/'sunhaven.db').is_file())
    def test_existing_destination_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'marker').write_text('preserve')
            with self.assertRaises(ValueError):recovery.create_bundle(p)
            self.assertEqual((p/'marker').read_text(),'preserve')
    def test_damaged_backup_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/'backup';recovery.create_bundle(b)
            with (b/'sunhaven.db').open('ab') as f:f.write(b'damage')
            with self.assertRaises(ValueError):recovery.restore_bundle(b,Path(d)/'out')
            self.assertFalse((Path(d)/'out').exists())
    def test_failed_verification_cleans_partial_backup(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(recovery,'_verify_database',side_effect=ValueError('verification failed')):
                with self.assertRaises(ValueError):recovery.create_bundle(Path(d)/'backup')
            self.assertEqual(list(Path(d).iterdir()),[])
    def test_manifest_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/'backup';recovery.create_bundle(b)
            p=b/'manifest.json';m=json.loads(p.read_text());m['files']['../escape']={};p.write_text(json.dumps(m))
            with self.assertRaises(ValueError):recovery.inspect_bundle(b)
    def test_restore_existing_destination_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/'backup';recovery.create_bundle(b)
            out=Path(d)/'out';out.mkdir();(out/'marker').write_text('preserve')
            with self.assertRaises(ValueError):recovery.restore_bundle(b,out)
            self.assertEqual((out/'marker').read_text(),'preserve')

for name in dir(WebTests):
    if name.startswith('test_') and name not in RecoveryTests.__dict__:setattr(RecoveryTests,name,None)
del WebTests
