FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py binance_client.py mistral_agent.py discord_bot.py config.py models.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Run the bot
CMD ["python", "-u", "main.py"]
```

---

## **3. `.dockerignore`**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Logs
*.log
bot.log

# Tests
test_*.py
mock_*.py
*_test.py

# Git
.git/
.gitignore

# Env files
.env

# Documentation
*.md
README.md

# Old files
*_old.py
*_backup.py
*.bak

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db