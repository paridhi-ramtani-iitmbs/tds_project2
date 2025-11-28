import os

# API Keys
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Logic: Prioritize Gemini, then Proxy
if GEMINI_API_KEY:
    # Google's OpenAI-compatible endpoint
    OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    API_KEY = GEMINI_API_KEY
    LLM_MODEL = "gemini-1.5-flash" # Standard model name
elif AIPROXY_TOKEN:
    OPENAI_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"
    API_KEY = AIPROXY_TOKEN
    LLM_MODEL = "gpt-4o-mini"
else:
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    API_KEY = OPENAI_API_KEY
    LLM_MODEL = "gpt-4o-mini"

# Server Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 7860))
USER_SECRET = os.getenv("USER_SECRET", "default_secret").strip()
