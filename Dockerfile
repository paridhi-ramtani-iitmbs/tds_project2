FROM python:3.10-slim

WORKDIR /app

# 1. Install basic system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies (As root)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright Browsers & System Deps (As root)
# We set a custom path so we can give the user permission to access it later
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir /ms-playwright && \
    playwright install --with-deps chromium

# 4. Setup non-root user (Required for Hugging Face)
RUN useradd -m -u 1000 user

# 5. Fix permissions: Give user ownership of app AND browser binaries
RUN chown -R user:user /app && \
    chown -R user:user /ms-playwright

# 6. Copy Code
COPY --chown=user . .

# 7. Switch to non-root user
USER user

# 8. Run
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
