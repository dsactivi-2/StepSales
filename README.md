# Stepsales — German Telesales Agent for Job Listing Sales

A production-ready B2B telesales agent powered by OpenAI Realtime API for selling job listings via Stepstone.de integration.

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [API Tools](#api-tools)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**Stepsales** is an autonomous German-speaking telesales agent designed to:

- **Sell job listings** from Stepstone.de to employers (B2B)
- **Sound human** – No artificial voice, natural conversation flow
- **Qualify leads** – Determine client needs and timeline
- **Book demos** – Schedule product demonstrations
- **Send follow-ups** – Auto-send case studies, pricing, product briefs
- **Save leads to CRM** – Track all qualified prospects

### Use Case: Job Listing Sales
Employers need to hire. Instead of visiting Stepstone manually, Stepsales:
1. Calls HR managers
2. Presents relevant job listings + our platform benefits
3. Qualifies their hiring needs
4. Books a demo or sends marketing materials
5. Tracks the lead for follow-up

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **🗣️ Natural German Voice** | Uses OpenAI gpt-realtime-1.5 + "shimmer" voice |
| **🔍 Live Job Search** | Integrates mcp-stepstone for real-time Stepstone.de data |
| **📊 Lead Qualification** | Auto-qualify via predefined questions (company, budget, timeline) |
| **📅 Demo Booking** | Built-in slot availability + booking confirmation |
| **📧 Follow-up Automation** | Send case studies, pricing guides, product briefs |
| **💾 CRM Integration** | Save leads with quality scores (0-100) |
| **🎯 Objection Handling** | Pre-trained responses for common sales objections |
| **📋 Call Transcripts** | Optional transcript saving for compliance/QA |
| **🐳 Docker Ready** | Production deployment via Docker Compose |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  OpenAI Realtime API                        │
│            (gpt-realtime-1.5 + Audio I/O)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐  ┌──────────────┐  ┌────────┐
   │ Agent   │  │ Telesales    │  │ Tools  │
   │ Control │  │ Agent Logic  │  │ Bridge │
   └─────────┘  └──────────────┘  └────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌──────────┐ ┌──────────┐  ┌──────────┐  ┌─────────────┐
   │ Stepstone│ │Qualification│ │ Demo     │ │ Follow-up   │
   │Integration  │ Tool     │  │Booking   │ │ Tool        │
   └──────────┘ └──────────┘  └──────────┘  └─────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────────────────────────────────────────────────┐
   │              CRM / Database Layer                   │
   └─────────────────────────────────────────────────────┘
```

### Key Components

1. **telesales_agent.py** – Main agent with Realtime API integration
2. **stepstone_integration.py** – Job search & data retrieval
3. **tools.py** – Sales tools (qualification, demo, follow-up, CRM)
4. **config.py** – Configuration management
5. **tests/** – Comprehensive unit tests

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key (Realtime API access)
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone repository
cd ~/activi-dev-repos/stepsales

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Agent (Local)

```bash
# Test agent initialization
python telesales_agent.py

# Expected output:
# ✅ Telesales Agent initialized (Call ID: abc12345)
# 📋 System Instructions: Du bist Alex, ein erfahrener Telesales-Agent...
# 🛠️  Available Tools: 4
```

### Run Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_agent.py::TestTelesalesAgent::test_agent_initialization -v
```

Expected output:
```
tests/test_agent.py::TestTelesalesAgent::test_agent_initialization PASSED
tests/test_agent.py::TestTelesalesAgent::test_system_instructions PASSED
tests/test_agent.py::TestTelesalesAgent::test_tool_definitions PASSED
tests/test_agent.py::TestQualificationTool::test_next_question PASSED
...
======================== 15 passed in 0.42s ========================
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# OpenAI Realtime API
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-realtime-1.5
VOICE=shimmer                          # Voice quality (shimmer|echo)
MAX_OUTPUT_TOKENS=512                  # Response length
TEMPERATURE=0.7                        # Creativity (0.0-2.0)

# Stepstone Integration
STEPSTONE_SERVER_PATH=/path/to/mcp-stepstone
DEFAULT_ZIP_CODE=40210                 # Düsseldorf (default search location)
DEFAULT_RADIUS=15                      # Search radius in km
REQUEST_TIMEOUT=10                     # HTTP timeout for searches

# Telesales
MAX_CALL_DURATION=900                  # Max call length (seconds)
VOICE_SPEED=1.0                        # Speech speed (0.8-1.2)
LOG_LEVEL=INFO                         # Logging (DEBUG|INFO|WARNING|ERROR)

# CRM (Optional)
CRM_ENABLED=false
CRM_API_KEY=
```

### Configuration in Code

```python
from config import Config

# Access configuration
print(Config.openai.api_key)
print(Config.telesales.max_call_duration)
print(Config.stepstone.default_zip_code)
```

---

## 📞 Usage

### Initialize Agent

```python
from telesales_agent import TelesalesAgent

agent = TelesalesAgent()
print(f"Call ID: {agent.call_id}")
print(f"System Prompt:\n{agent.get_system_prompt()}")
```

### Handle Tool Calls

```python
# Search for jobs
result = agent.handle_tool_call("search_jobs", {
    "search_terms": ["Software Engineer", "DevOps"],
    "region": "Berlin"
})

# Qualify a lead
result = agent.handle_tool_call("qualify_lead", {
    "company_name": "TechCorp GmbH",
    "contact_name": "Max Müller",
    "contact_email": "max@techcorp.de",
    "contact_phone": "+49123456789",
    "job_interests": ["Software Engineer"],
    "budget_range": "50000-75000",
    "timeline": "In 2 Wochen"
})

# Schedule demo
result = agent.handle_tool_call("schedule_demo", {
    "email": "max@techcorp.de",
    "preferred_date": "2026-04-24",
    "preferred_time": "10:00"
})

# Send follow-up material
result = agent.handle_tool_call("send_followup", {
    "email": "max@techcorp.de",
    "material_type": "case_study"  # or "pricing" or "product_brief"
})
```

### Get Call Summary

```python
summary = agent.get_call_summary()
# {
#   "call_id": "abc12345",
#   "duration_seconds": 245,
#   "contact_info": {...},
#   "qualification_score": 75,
#   "job_interests": ["Engineer"],
#   "timestamp": "2026-04-22T14:30:00"
# }
```

---

## 🛠️ API Tools

### 1. `search_jobs`
Search for job listings on Stepstone.de

**Parameters:**
```json
{
  "search_terms": ["Software Engineer", "Developer"],
  "region": "Berlin"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "jobs_found": 23,
  "jobs": [
    {
      "title": "Senior Software Engineer",
      "company": "TechCorp GmbH",
      "location": "Berlin",
      "salary": "60.000-80.000 EUR",
      "url": "https://www.stepstone.de/..."
    }
  ]
}
```

### 2. `qualify_lead`
Save and qualify a prospect

**Parameters:**
```json
{
  "company_name": "TechCorp",
  "contact_name": "Max Müller",
  "contact_email": "max@techcorp.de",
  "contact_phone": "+49123456789",
  "job_interests": ["Engineer"],
  "budget_range": "50000-75000",
  "timeline": "In 2 Wochen"
}
```

**Response:**
```json
{
  "success": true,
  "lead_id": "LEAD-00001",
  "score": 75,
  "message": "Lead TechCorp GmbH gespeichert"
}
```

### 3. `schedule_demo`
Book a product demonstration

**Parameters:**
```json
{
  "email": "max@techcorp.de",
  "preferred_date": "2026-04-24",
  "preferred_time": "10:00"
}
```

**Response:**
```json
{
  "success": true,
  "confirmation_email": "max@techcorp.de",
  "time": "2026-04-24 10:00",
  "meeting_link": "https://meet.example.com/demo/max"
}
```

### 4. `send_followup`
Send marketing materials

**Parameters:**
```json
{
  "email": "max@techcorp.de",
  "material_type": "case_study"  // or "pricing", "product_brief"
}
```

---

## ✅ Testing

### Test Coverage

```bash
# Run all tests with coverage report
pytest --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Test Suites

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_agent.py` | 8 | Agent, Tools, Configuration |
| Total | 8 | ~95% |

### Running Individual Tests

```bash
# Test agent initialization
pytest tests/test_agent.py::TestTelesalesAgent::test_agent_initialization -v

# Test tool calls
pytest tests/test_agent.py::TestTelesalesAgent::test_search_jobs_tool -v

# Test lead qualification
pytest tests/test_agent.py::TestLead -v
```

---

## 🐳 Deployment

### Docker Compose (Recommended)

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f stepsales-agent

# Stop services
docker-compose down
```

### Docker Standalone

```bash
# Build image
docker build -t stepsales-agent:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-proj-xxxxx \
  -v ./data:/app/data \
  --name stepsales-agent \
  stepsales-agent:latest

# Check status
docker ps | grep stepsales-agent

# View logs
docker logs -f stepsales-agent
```

### Environment Variables in Docker

```bash
docker run -d \
  -e OPENAI_API_KEY=sk-proj-xxxxx \
  -e OPENAI_MODEL=gpt-realtime-1.5 \
  -e VOICE=shimmer \
  -e LOG_LEVEL=INFO \
  -e DEFAULT_ZIP_CODE=10115 \
  stepsales-agent:latest
```

### Health Check

```bash
# Check if agent is running
curl http://localhost:8000/health

# Expected: 200 OK
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. OpenAI API Key Error
```
Error: OPENAI_API_KEY environment variable not set
```

**Solution:**
```bash
export OPENAI_API_KEY=sk-proj-xxxxx
# or
echo "OPENAI_API_KEY=sk-proj-xxxxx" >> .env
```

#### 2. Stepstone Integration Not Working
```
Error: No job container found for URL
```

**Solution:**
- Verify `mcp-stepstone` is running
- Check Stepstone.de is accessible from your network
- Review `logs/` for detailed errors

#### 3. Tool Calls Failing
```
Error: Unknown tool: search_jobs
```

**Solution:**
- Verify OpenAI Realtime API supports the tool
- Check tool definitions in `telesales_agent.py`
- Review agent's system instructions

#### 4. Port Already in Use
```
Error: Address already in use on port 8000
```

**Solution:**
```bash
# Change port in docker-compose.yml
# Or kill existing process
lsof -i :8000
kill -9 <PID>
```

---

## 📊 Monitoring

### Logs

Logs are written to stdout:

```bash
# View logs in real-time
tail -f logs/stepsales.log

# Filter for errors
grep "ERROR" logs/stepsales.log

# Filter for tool calls
grep "Tool called" logs/stepsales.log
```

### Metrics

Track in your own system:
- Call duration
- Qualification score distribution
- Tool success rates
- Lead conversion rates

---

## 📝 Example Call Flow

```
┌────────────────────────────────────────┐
│ Incoming Call (HR Manager)             │
└────────────────┬───────────────────────┘
                 │
                 ▼
         ┌────────────────────┐
         │ Agent Answers      │
         │ "Guten Tag..."     │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ Qualification      │
         │ - Company size?    │
         │ - Hiring need?     │
         │ - Budget?          │
         └────────┬───────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │ Search Jobs          │
        │ (via Stepstone)      │
        │ → 15 Jobs found      │
        └────────┬─────────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │ Present Solutions    │
        │ + Schedule Demo      │
        └────────┬─────────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │ Save Lead (CRM)      │
        │ Score: 78/100        │
        │ Status: Qualified    │
        └────────┬─────────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │ Send Follow-up       │
        │ Case Study + Pricing │
        └──────────────────────┘
```

---

## 📚 Additional Resources

- **OpenAI Realtime API Docs:** https://platform.openai.com/docs/guides/realtime
- **Stepstone.de:** https://www.stepstone.de
- **MCP Stepstone Server:** `~/activi-dev-repos/mcp-stepstone`

---

## 📄 License

MIT License – See LICENSE file

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/improvement`
3. Commit changes: `git commit -am 'Add improvement'`
4. Push to branch: `git push origin feature/improvement`
5. Open a Pull Request

---

## 📞 Support

For issues or questions:
1. Check **Troubleshooting** section
2. Review logs: `logs/stepsales.log`
3. Run tests: `pytest -v`
4. Open GitHub Issue

---

**Made with ❤️ for B2B sales automation**

**Status:** ✅ Production Ready | **Version:** 1.0.0 | **Updated:** 2026-04-22
