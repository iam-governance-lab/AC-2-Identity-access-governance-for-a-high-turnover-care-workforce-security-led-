"""Rebuild the dependency-free CSS bundle after editing styles."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'portal'/'static'
(root/'app.bundle.css').write_text('\n'.join((root/name).read_text() for name in ('style.css','workspace.css','unified.css','final.css','v10.css','v11.css','v12.css')))
