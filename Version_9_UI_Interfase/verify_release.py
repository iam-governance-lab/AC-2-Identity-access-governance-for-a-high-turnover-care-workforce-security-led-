"""Verify packaged files. Newly generated runtime data is not in the manifest."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text())
bad=[]
for item in manifest['files']:
 p=root/item['path']
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:bad.append(item['path'])
print(json.dumps({'version':manifest['version'],'files_checked':len(manifest['files']),'status':'FAIL' if bad else 'PASS','missing_or_changed':bad},indent=2))
raise SystemExit(bool(bad))
