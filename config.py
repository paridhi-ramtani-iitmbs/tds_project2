import os
import logging

logger = logging.getLogger("uvicorn")

# Collect all API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Server Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))
USER_SECRET = os.getenv("USER_SECRET", "default_secret").strip()

# API Configuration Priority: Gemini > AIProxy > OpenAI
API_CONFIGS = []

if GEMINI_API_KEY:
    # Using the latest Gemini models with OpenAI compatibility
    # Base URL: https://generativelanguage.googleapis.com/v1beta/openai/
    # Valid models: gemini-2.5-flash, gemini-2.0-flash, gemini-3-pro-preview, etc.
    API_CONFIGS.append({
        "name": "Gemini 2.5 Flash",
        "api_key": GEMINI_API_KEY,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash"
    })
    API_CONFIGS.append({
        "name": "Gemini 2.0 Flash",
        "api_key": GEMINI_API_KEY,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash"
    })
    logger.info("✓ Gemini API configured (2.5 Flash + 2.0 Flash)")

if AIPROXY_TOKEN:
    API_CONFIGS.append({
        "name": "AIProxy",
        "api_key": AIPROXY_TOKEN,
        "base_url": "https://aiproxy.sanand.workers.dev/openai/v1",
        "model": "gpt-4o-mini"
    })
    logger.info("✓ AIProxy configured")

if OPENAI_API_KEY:
    API_CONFIGS.append({
        "name": "OpenAI",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    })
    logger.info("✓ OpenAI API configured")

if not API_CONFIGS:
    raise ValueError("No API keys configured. Set at least one: GEMINI_API_KEY, AIPROXY_TOKEN, or OPENAI_API_KEY")

logger.info(f"Total {len(API_CONFIGS)} API endpoint(s) configured with fallback support")
