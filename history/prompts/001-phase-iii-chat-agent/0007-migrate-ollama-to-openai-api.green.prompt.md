---
id: "0007"
title: Migrate Ollama to OpenAI API
stage: green
date: 2026-03-04
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-phase-iii-chat-agent
branch: 001-phase-iii-chat-agent
user: developer
command: chat
labels: ["openai", "streaming", "migration", "agent-service", "gpt-4o-mini"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/app/services/agent_service.py
  - backend/app/api/routes/chat.py
  - backend/app/main.py
  - backend/app/config.py
  - backend/requirements.txt
  - backend/.env.example
  - backend/tests/unit/test_agent_service.py
tests:
  - backend/tests/unit/test_agent_service.py (9 tests: success, system prompt, auth error, connection error, rate limit, empty response, health success, health no key, health bad key)
  - backend/tests/unit/test_chat_service.py (4 tests: unchanged, all pass)
---

## Prompt

Migrate the AI chat backend from local Ollama (llama3) to OpenAI API (gpt-4o-mini). Replace all Ollama-specific code with the official openai Python SDK. Maintain existing SSE streaming architecture. Add proper error handling for auth errors, rate limits, connection failures, and timeouts. Add health check endpoint for API key validation.

## Response snapshot

Complete migration from Ollama to OpenAI API:
- Replaced httpx-based Ollama integration with official `openai` AsyncOpenAI client
- Maintained identical SSE streaming contract (token/done/error events)
- Added granular error handling for 5 OpenAI-specific error types (AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError, APIStatusError)
- Added health check that validates API key by calling models.retrieve()
- Updated config, requirements, .env.example, and all tests
- 13/13 unit tests pass, 0 regressions

## Outcome

- ✅ Impact: Migrated from local Ollama to OpenAI API with gpt-4o-mini for production-quality responses
- 🧪 Tests: 9 agent tests + 4 chat service tests = 13/13 passing
- 📁 Files: 7 files modified
- 🔁 Next prompts: Set OPENAI_API_KEY in .env and test end-to-end
- 🧠 Reflection: The SSE streaming architecture from the previous Ollama work transferred cleanly — only the agent_service internals needed to change

## Evaluation notes (flywheel)

- Failure modes observed: None — clean migration
- Graders run and results (PASS/FAIL): pytest 13/13 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Verify streaming latency with real OpenAI API key
