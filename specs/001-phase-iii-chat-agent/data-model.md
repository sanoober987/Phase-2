# Data Model: Phase III Chat Agent

**Feature**: 001-phase-iii-chat-agent
**Date**: 2026-02-25

---

## Entities

### Task (existing — no schema changes)

Located at: `backend/app/models/task.py`

| Field       | Type                | Constraints                   |
|-------------|---------------------|-------------------------------|
| id          | UUID (PK)           | default uuid4                 |
| user_id     | str                 | indexed, NOT NULL             |
| title       | str                 | max 255, NOT NULL             |
| description | str (optional)      | max 2000                      |
| completed   | bool                | default False                 |
| created_at  | datetime (tz-aware) | auto, DateTime(timezone=True) |
| updated_at  | datetime (tz-aware) | auto, DateTime(timezone=True) |

State transitions: `completed=False` → `completed=True` (toggle via PATCH /tasks/{id}/toggle)

---

### Conversation (new)

New file: `backend/app/models/conversation.py`

| Field      | Type                | Constraints                   |
|------------|---------------------|-------------------------------|
| id         | UUID (PK)           | default uuid4                 |
| user_id    | str                 | indexed, NOT NULL             |
| created_at | datetime (tz-aware) | auto, DateTime(timezone=True) |
| updated_at | datetime (tz-aware) | auto, DateTime(timezone=True) |

Index: `(user_id)` — for listing a user's conversations

---

### Message (new)

New file: `backend/app/models/message.py`

| Field           | Type                | Constraints                           |
|-----------------|---------------------|---------------------------------------|
| id              | UUID (PK)           | default uuid4                         |
| conversation_id | UUID (FK)           | → conversations.id, indexed, NOT NULL |
| role            | str                 | "user" \| "assistant" \| "tool"       |
| content         | Text                | NOT NULL                              |
| tool_calls      | JSON (optional)     | nullable                              |
| created_at      | datetime (tz-aware) | auto, DateTime(timezone=True)         |

Index: `(conversation_id, created_at)` — for loading history in order

---

## Relationships

```
User (user_id: str)
  ├── Task*          (user_id FK)
  └── Conversation*  (user_id FK)
         └── Message* (conversation_id FK)
```

`user_id` on `Conversation` and `Task` is a string FK referencing the Better Auth
user record. Tasks and Conversations reference it by string ID.

---

## SQLModel Sketches

### Conversation

```python
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlmodel import SQLModel, Field

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True, nullable=False)
    created_at: datetime = Field(default_factory=_utcnow,
                                  sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow,
                                  sa_type=DateTime(timezone=True))
```

### Message

```python
from typing import Optional
from sqlalchemy import Column, Text, JSON

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(foreign_key="conversations.id",
                                   index=True, nullable=False)
    role: str = Field(nullable=False)  # user | assistant | tool
    content: str = Field(sa_column=Column(Text, nullable=False))
    tool_calls: Optional[dict] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    created_at: datetime = Field(default_factory=_utcnow,
                                  sa_type=DateTime(timezone=True))
```

---

## init_db Registration

In `backend/app/database.py` → `init_db()`, add imports so `create_all` registers
new tables:

```python
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message            # noqa: F401
```
