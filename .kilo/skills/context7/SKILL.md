---
name: context7
description: Use Context7 to fetch up-to-date, version-specific documentation for libraries used in this project (LangGraph, OpenAI, Deepgram, ElevenLabs, Telnyx, Stripe, SQLAlchemy, FastAPI).
---

# Context7 Skill - Up-to-Date Documentation Lookup

When working with any library or framework in this project, use Context7 to fetch current documentation before writing code.

## Libraries Used in This Project

Always use Context7 library IDs for these libraries:

| Library | Context7 ID | Purpose |
|---------|-------------|---------|
| LangGraph | `/langchain-ai/langgraph` | Conversation state machine |
| LangChain | `/langchain-ai/langchain` | LLM orchestration |
| OpenAI Python SDK | `/openai/openai-python` | Chat completions, Realtime API |
| Deepgram Python SDK | `/deepgram/deepgram-python-sdk` | Speech-to-Text |
| Deepgram API | `/llmstxt/developers_deepgram_llms_txt` | STT recipes and examples |
| ElevenLabs | `/websites/elevenlabs-docs` | Text-to-Speech |
| Telnyx Python SDK | `/telnyx/telnyx-python` | Voice API, outbound calls |
| Stripe Python SDK | `/stripe/stripe-python` | Invoicing, webhooks |
| SQLAlchemy | `/sqlalchemy/sqlalchemy` | ORM, async sessions |
| FastAPI | `/websites/fastapi_tiangolo` | Web server, WebSocket |
| Neo4j Python Driver | `/websites/neo4j_com_developer` | Graph database |
| Qdrant Python SDK | `/websites/qdrant_com` | Vector database |

## When to Use Context7

Use Context7 **before** writing code that involves:
- New library features or APIs you haven't used recently
- Configuration options (e.g., LangGraph checkpointers, Deepgram VAD params)
- Authentication patterns (e.g., Telnyx webhooks, Stripe signature verification)
- Async patterns (e.g., SQLAlchemy async sessions, httpx async clients)
- WebSocket streaming (e.g., ElevenLabs streaming, Deepgram realtime)

## How to Use

### CLI Mode (No MCP Required)
```bash
# Search for a library
ctx7 library <name> <query>

# Get docs for a specific library
ctx7 docs <libraryId> <query>
```

### MCP Mode (when MCP server is connected)
Use the `resolve-library-id` and `query-docs` tools.

## Rules

1. **Always verify API signatures** - Don't assume method names; look them up
2. **Check version compatibility** - This project uses LangGraph 1.1.9, OpenAI 2.32.0
3. **Prefer async patterns** - All services in this project are async
4. **Use official SDKs** - Don't craft raw HTTP requests when an SDK method exists
