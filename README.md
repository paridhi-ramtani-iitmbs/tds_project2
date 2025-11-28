---
title: TDS Quiz Solver
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# TDS Project 2 - Automatic Quiz Solver

This project is an automated agent designed to solve data analysis quizzes. It uses an LLM to generate Python code, executes it in a secure environment, and submits the answers via API.

## 🚀 Features

*   **FastAPI Backend**: Handles incoming tasks via a REST API.
*   **Agentic Workflow**:
    *   Scrapes quiz pages using **Playwright**.
    *   Parses tasks using **Google Gemini** (via OpenAI compatible client).
    *   Writes and executes Python code dynamically.
    *   Supports **OCR** (Tesseract) and **PDF Parsing**.
*   **Dockerized**: Fully isolated environment for safe code execution.
*   **Resilient**: Includes retry logic and self-correction if the answer is wrong.

## 🛠️ Configuration

To run this project, you need to set the following Environment Variables (locally or in Hugging Face Secrets):

| Variable | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Your Google Gemini API Key. |
| `USER_SECRET` | A custom secret password to authenticate requests. |
| `AIPROXY_TOKEN` | (Optional) Alternative if using the course proxy. |

## 📦 How to Run Locally

### Using Docker (Recommended)
```bash
# 1. Build the image
docker build -t quiz-solver .

# 2. Run container (replace YOUR_KEY and YOUR_SECRET)
docker run -p 8000:7860 \
  -e GEMINI_API_KEY="AIzaSy..." \
  -e USER_SECRET="mysecret" \
  quiz-solver
