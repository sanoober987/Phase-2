---
id: "0008"
title: Production Hardening Retry Ratelimit Trimming
stage: green
date: 2026-03-05
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-phase-iii-chat-agent
branch: 001-phase-iii-chat-agent
user: developer
command: chat
labels: ["production", "retry", "rate-limit", "token-trimming", "backoff", "openai"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/app/services/agent_service.py
  - backend/app/api/routes/chat.py
  - backend/app/config.py
  - backend/app/main.py
  - backend/.env.example
  - backend/tests/unit/test_agent_service.py
tests:
  - backend/tests/unit/test_agent_service.py (16 tests)
  - backend/tests/unit/test_chat_service.py (4 tests)
---

## Prompt

Production hardening of the AI chat system: add exponential-backoff retry for OpenAI 429/5xx errors, per-user in-memory rate limiting, token-aware history trimming, single config source, proper HTTP status code mapping, stream persistence safety, and comprehensive test coverage.

## Response snapshot

Diagnosed 11 issues across agent_service.py, chat.py, config.py, main.py. Key root causes:
1. No retry with backoff for rate limits (SDK max_retries only handles transport errors)
2. No per-user request throttling
3. No token budget management — unbounded input costs
4. Dual config source (os.getenv at import time vs Settings class)
5. Stream persistence inside generator (lost on disconnect)
6. No Retry-After header forwarding
7. All errors mapped to generic 502

Added: _retry_with_backoff(), _check_user_rate_limit(), trim_messages(), _translate_openai_error(), proper HTTP status code mapping (429/503/502), user message persisted before stream starts.

## Outcome

- ✅ Impact: Production-grade resilience — retry, rate limiting, cost control, stream safety
- 🧪 Tests: 20/20 unit tests pass (16 agent + 4 chat service), 38/55 full suite (16 pre-existing failures unchanged)
- 📁 Files: 6 files modified
- 🔁 Next prompts: Load test with concurrent users, verify retry timing under real 429s
- 🧠 Reflection: The SDK's max_retries parameter is misleading — it only retries transport errors, not HTTP 429. Application-level retry with backoff is essential.

## Evaluation notes (flywheel)

- Failure modes observed: SDK max_retries=2 did not retry on 429, dual config sources could diverge
- Graders run and results (PASS/FAIL): pytest 20/20 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add tiktoken for exact token counting instead of char/4 estimate
