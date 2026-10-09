import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

RELEASE_VERSION = "9.0-final"
DEMO_PROFILE = os.getenv("SUNHAVEN_DEMO_PROFILE", "standard")
if DEMO_PROFILE not in ("standard", "expanded"):raise RuntimeError("Demo profile must be standard or expanded")

APP_NAME = "Sunhaven Care IAM"
HOST = os.getenv("SUNHAVEN_HOST", "127.0.0.1")
PORT = int(os.getenv("SUNHAVEN_PORT", "8000"))
DB_PATH = Path(os.getenv("SUNHAVEN_DB_PATH", str(BASE_DIR / "data" / "sunhaven.db")))
SESSION_MINUTES = int(os.getenv("SUNHAVEN_SESSION_MINUTES", str(60 * int(os.getenv("SUNHAVEN_SESSION_HOURS", "0")) or 15)))
if not 1 <= SESSION_MINUTES <= 480:
    raise RuntimeError("SUNHAVEN_SESSION_MINUTES must be 1 to 480")

# local = built-in demo login; entra = Microsoft Entra ID login through MSAL
AUTH_MODE = os.getenv("SUNHAVEN_AUTH_MODE", "local").lower()
# mock = fully local lifecycle simulation; real = Microsoft Graph operations
GRAPH_MODE = os.getenv("SUNHAVEN_GRAPH_MODE", "mock").lower()

TENANT_ID = os.getenv("SUNHAVEN_TENANT_ID", "")
CLIENT_ID = os.getenv("SUNHAVEN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SUNHAVEN_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SUNHAVEN_REDIRECT_URI", f"http://{HOST}:{PORT}/auth/callback")

# Optional Entra role-group mapping. Configure only if using real Graph mode.
ROLE_GROUP_IDS = {
    "CareWorker": os.getenv("SUNHAVEN_GROUP_CAREWORKER", ""),
    "Nurse": os.getenv("SUNHAVEN_GROUP_NURSE", ""),
    "Manager": os.getenv("SUNHAVEN_GROUP_MANAGER", ""),
    "AgencyWorker": os.getenv("SUNHAVEN_GROUP_AGENCY", ""),
    "Auditor": os.getenv("SUNHAVEN_GROUP_AUDITOR", ""),
    "IAMOperator": os.getenv("SUNHAVEN_GROUP_IAMOPERATOR", ""),
}

ALLOWED_ROLES = ["CareWorker", "Nurse", "Manager", "AgencyWorker", "Auditor", "IAMOperator", "SiteDelegate"]
NORMAL_CARE_ROLES = ["CareWorker", "Nurse", "Manager", "AgencyWorker"]
WORKER_TYPES = ["Permanent", "Casual", "Agency", "ThirdParty"]
STATUSES = ["Active", "Inactive", "Leaver", "Suspended"]
FACILITIES = ["Ashford Main", "North Wing", "South Wing"]

# The system is a student laboratory proof of concept using synthetic data only.
LAB_ONLY = True
ENVIRONMENT = os.getenv("SUNHAVEN_ENV", "development")
SECRET_KEY = os.getenv("SUNHAVEN_SECRET_KEY", "")
SECURE_COOKIES = ENVIRONMENT == "production"
SEED_DEMO = os.getenv("SUNHAVEN_SEED_DEMO", "1" if ENVIRONMENT == "development" else "0") == "1"

def validate_config():
    if ENVIRONMENT not in ("development", "production"):
        raise RuntimeError("SUNHAVEN_ENV must be development or production")
    if AUTH_MODE not in ("local", "entra") or GRAPH_MODE not in ("mock", "real"):
        raise RuntimeError("Invalid authentication or Graph mode")
    if GRAPH_MODE == "real":
        raise RuntimeError("Real Graph mutations are disabled in this release pending tenant integration and partial-failure testing. Use mock mode.")
    if ENVIRONMENT == "production":
        if AUTH_MODE != "entra" or SEED_DEMO:
            raise RuntimeError("Production requires Entra authentication and SUNHAVEN_SEED_DEMO=0")
        if len(SECRET_KEY) < 32:
            raise RuntimeError("Production requires a random SUNHAVEN_SECRET_KEY of at least 32 characters")
        if not all((TENANT_ID, CLIENT_ID, CLIENT_SECRET)) or not REDIRECT_URI.startswith("https://"):
            raise RuntimeError("Production requires Entra credentials and an HTTPS redirect URI")

