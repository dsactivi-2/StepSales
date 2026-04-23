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
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD sh -c 'python -c "from services.orchestrator_langgraph import build_conversation_graph; from config.settings import AppConfig; g = build_conversation_graph(AppConfig); print(\"LangGraph OK\")"' || exit 1

# Run LangGraph orchestrator (full voice pipeline)
CMD ["python", "main.py"]
