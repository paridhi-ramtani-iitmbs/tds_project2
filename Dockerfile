FROM python:3.10-slim

WORKDIR /app

# 1. Install system dependencies
# - chromium for Playwright
# - tesseract-ocr for image-to-text (vision tasks)
# - git/wget/gnupg for general utilities
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Playwright Browsers (Chromium only)
RUN playwright install --with-deps chromium

# 4. Copy Code
COPY . .

# 5. Expose Port
EXPOSE 8000

# 6. Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
