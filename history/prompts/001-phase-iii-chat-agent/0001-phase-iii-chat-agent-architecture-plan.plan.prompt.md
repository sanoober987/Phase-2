---
id: "002"
title: Phase III Chat Agent Architecture Plan
stage: plan
date: 2026-02-25
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-phase-iii-chat-agent
branch: 001-phase-iii-chat-agent
user: architext
command: /sp.plan
labels: ["plan","openai-agents","mcp","fastapi","chat","jwt","neon"]
links:
  spec: specs/001-phase-iii-chat-agent/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-phase-iii-chat-agent/plan.md
  - specs/001-phase-iii-chat-agent/research.md
  - specs/001-phase-iii-chat-agent/data-model.md
  - specs/001-phase-iii-chat-agent/contracts/api.yaml
tests:
  - tests/unit/test_chat_service.py (defined, not yet implemented)
  - tests/unit/test_mcp_tools.py (defined, not yet implemented)
  - tests/integration/test_chat_endpoint.py (defined, not yet implemented)
---

## Prompt

/sp.plan Phase III AI Chatbot System Plan

Goal: Build an AI-powered chatbot that allows users to manage tasks using natural
language with MCP tools and AI agents.

Steps: Database Setup (conversations, messages tables), Chat API
(POST /api/{user_id}/chat), MCP Server Tools (add_task, list_tasks, complete_task,
delete_task, update_task), AI Agent Logic, Frontend ChatKit UI, Security (JWT +
user isolation), Testing.

## Response snapshot

Produced full architectural plan for Phase III AI chat agent covering 7 implementation
phases (A–G). Research resolved 6 unknowns: OpenAI Agents SDK MCP integration pattern,
stateless FastMCP server design, JWT verification reuse from existing auth_service.py,
Neon+SQLModel async patterns for Conversation/Message models, custom ChatPanel vs
ChatKit UI decision, and stateless pipeline design.

Artifacts written:
- research.md: 6 research decisions with rationale and alternatives
- data-model.md: Task (existing), Conversation (new), Message (new) with SQLModel sketches
- contracts/api.yaml: OpenAPI 3.0 spec for all 7 endpoints
- plan.md: Full architecture plan — 7 phases, security design, risks, source layout

All 6 constitution principles verified as PASS. Top risks documented with mitigations.

## Outcome

- ✅ Impact: Full architectural plan ready for /sp.tasks to generate implementation tasks
- 🧪 Tests: Test file names and scenarios defined; implementation in Phase G
- 📁 Files: plan.md, research.md, data-model.md, contracts/api.yaml
- 🔁 Next prompts: /sp.tasks --feature 001-phase-iii-chat-agent
- 🧠 Reflection: Existing auth_service.py and task_service.py reuse significantly
  reduces new code surface. MCP stdio subprocess latency is the top risk to monitor.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (plan phase)
- Prompt variant (if applicable): N/A
- Next experiment: benchmark MCP stdio latency vs in-process SSE during Phase C
