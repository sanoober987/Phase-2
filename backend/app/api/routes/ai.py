from fastapi import APIRouter, HTTPException
from openai import OpenAI
import os
import time
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/ai", tags=["AI"])

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
)

# Simple rate limiter
last_request_time = 0


@router.post("/chat")
async def chat(prompt: str):

    global last_request_time

    try:
        # Rate limit protection (1 request per 2 seconds)
        current_time = time.time()

        if current_time - last_request_time < 2:
            raise HTTPException(
                status_code=429,
                detail="Slow down! Please wait before sending another message."
            )

        last_request_time = current_time

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return {
            "response": response.choices[0].message.content
        }

    except Exception as e:
        return {"error": str(e)}