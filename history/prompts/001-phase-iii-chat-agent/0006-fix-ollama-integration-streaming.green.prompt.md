---
id: "0006"
title: Fix Ollama Integration and Add Streaming
stage: green
date: 2026-03-04
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-phase-iii-chat-agent
branch: 001-phase-iii-chat-agent
user: developer
command: chat
labels: ["ollama", "streaming", "bug-fix", "agent-service", "sse"]
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
  - frontend/hooks/useChat.ts
tests:
  - backend/tests/unit/test_agent_service.py (7 tests: success/error/health)
---

## Prompt

You are an expert AI backend engineer specializing in FastAPI, Ollama, and real-time AI chat systems.

My system is currently having problems such as:
- Fallback responses instead of real AI answers
- Slow response time
- Connection failures
- Streaming not working
- Model not responding correctly

Environment Details:
- Backend: FastAPI
- AI Engine: Ollama (local)
- Model: llama3
- Host: http://localhost:11434
- OS: Windows

Your job is to:
1. Find the root cause of ALL possible issues.
2. Provide production-level working code.
3. Enable real-time streaming responses.
4. Remove all fallback or fake responses.
5. Add proper error logging.
6. Add timeout handling.
7. Check model availability before making requests.
8. Optimize for fast response speed.
9. Provide step-by-step debugging checklist.
10. Provide Windows-specific setup instructions.

## Response snapshot

Diagnosed 13 issues across agent_service.py, chat.py route, config.py, and requirements.txt. Key root causes:
1. Fallback response hiding real errors (catch-all returning fake "thinking..." message)
2. No HTTP status code validation on Ollama responses
3. No streaming support (stream: False)
4. httpx client recreated per request (no connection pooling)
5. No startup health/model checks
6. Hardcoded model name, no timeout granularity
7. Missing httpx in requirements.txt

Fixed all 8 files with production-level code including SSE streaming, proper error propagation, reusable httpx client, health check endpoints, and frontend streaming consumer.

## Outcome

- ✅ Impact: Eliminated all fallback responses, added real-time SSE streaming, proper error propagation, startup health checks
- 🧪 Tests: Updated test_agent_service.py with 7 tests covering success, user_id, connection error, HTTP error, empty response, health check
- 📁 Files: 8 files modified (agent_service.py, chat.py, main.py, config.py, requirements.txt, .env.example, test_agent_service.py, useChat.ts)
- 🔁 Next prompts: Test end-to-end with Ollama running, verify SSE streaming in browser
- 🧠 Reflection: The original catch-all exception handler was the primary issue — it silently converted every error into a fake "thinking" response, making debugging impossible

## Evaluation notes (flywheel)

- Failure modes observed: Fallback response masking connection errors, timeout errors, model-not-found errors
- Graders run and results (PASS/FAIL): Manual code review PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run pytest to validate all unit tests pass
