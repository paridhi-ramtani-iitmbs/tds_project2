FROM python:3.10-slim

# Set working directory
WORKDIR /app

# 1. Install system dependencies
# chromium: for Playwright
# tesseract-ocr: for vision tasks
# git/wget: utilities
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup a non-root user (Required for Hugging Face)
RUN useradd -m -u 1000 user
# Give the user ownership of the app directory
RUN chown -R user:user /app

# 3. Switch to non-root user
USER user

# 4. Set Environment variables for Path
ENV PATH="/home/user/.local/bin:$PATH"

# 5. Copy requirements and install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Install Playwright Browsers (Chromium only)
RUN playwright install --with-deps chromium

# 7. Copy Code (with correct ownership)
COPY --chown=user . .

# 8. Expose Hugging Face default port
EXPOSE 7860

# 9. Run application on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
