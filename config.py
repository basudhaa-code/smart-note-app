import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

for directory in (UPLOAD_DIR, DATA_DIR, STATIC_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Load existing environment variables
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

# Active configuration state
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "gemini-3.8-flash").strip()
PORT = int(os.environ.get("PORT", "8000"))

def get_api_key() -> str:
    global GEMINI_API_KEY
    return GEMINI_API_KEY

def set_api_key(key: str, persist: bool = True) -> bool:
    global GEMINI_API_KEY
    clean_key = key.strip()
    GEMINI_API_KEY = clean_key
    os.environ["GEMINI_API_KEY"] = clean_key
    
    if persist:
        try:
            env_content = f"GEMINI_API_KEY={clean_key}\nDEFAULT_MODEL={DEFAULT_MODEL}\n"
            ENV_FILE.write_text(env_content, encoding="utf-8")
        except Exception as e:
            print(f"[config] Failed to persist .env: {e}")
            
    return bool(clean_key)

def get_gemini_client():
    key = get_api_key()
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception as e:
        print(f"[config] Error initializing Gemini client: {e}")
        return None
