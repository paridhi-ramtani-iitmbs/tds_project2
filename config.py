import os

# API Keys
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Constants
PROXY_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"

# Application Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))

# Timeout settings
BROWSER_TIMEOUT = 60000  # 60 seconds
SUBMISSION_TIMEOUT = 180  # 3 minutes total
