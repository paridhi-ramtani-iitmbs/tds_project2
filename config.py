import os

# API Keys (Added .strip() to fix copy-paste errors)
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Logic: Use Proxy if token exists, else default OpenAI
if AIPROXY_TOKEN:
    OPENAI_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"
    API_KEY = AIPROXY_TOKEN
else:
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    API_KEY = OPENAI_API_KEY

# Server Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))
USER_SECRET = os.getenv("USER_SECRET", "default_secret").strip()
