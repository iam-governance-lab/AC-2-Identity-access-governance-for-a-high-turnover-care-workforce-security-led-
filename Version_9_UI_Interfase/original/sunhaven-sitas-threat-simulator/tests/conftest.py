import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIRECTORY)
)

# Fixtures added for automatic comparison/reporting tests.
import json as _json
from pathlib import Path as _Path


@__import__("pytest").fixture
def real_environment():
    return _json.loads(_Path("config/environment.json").read_text(encoding="utf-8"))


@__import__("pytest").fixture
def real_controls():
    return _json.loads(_Path("config/controls.json").read_text(encoding="utf-8"))


@__import__("pytest").fixture
def real_risk_model():
    return _json.loads(_Path("config/risk-model.json").read_text(encoding="utf-8"))


@__import__("pytest").fixture
def real_scenario_01():
    return _json.loads(
        _Path("scenarios/scenario-01-stolen-nurse-credential.json").read_text(
            encoding="utf-8"
        )
    )
