FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/transcripts static

# Expose port for web server
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD sh -c 'python -c "import os,requests; port=os.getenv(\"PORT\",\"8000\"); requests.get(f\"http://localhost:{port}/health\", timeout=5)"' || exit 1

# Run web server (for live voice calls)
# Override with: docker run -e MODE=agent [image] python telesales_agent.py
CMD ["python", "web_server.py"]
