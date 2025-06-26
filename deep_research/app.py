# deep_research/app.py (MODIFIED FOR STREAMING)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import os
import json # Import json to serialize messages

from main import run_research # Your refactored research function

app = FastAPI(
    title="AI Deep Research API",
    description="API for comprehensive AI-driven research based on user queries.",
    version="1.0.0",
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173", # Your React app's development server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Research Assistant API. Use /research for deep research."}

@app.post("/research")
async def stream_research_paper(request: QueryRequest):
    """
    API endpoint to receive a query and stream progress updates, then the final research paper.
    """
    print(f"Received query for streaming: '{request.query}'")

    async def event_generator():
        try:
            async for message in run_research(request.query):
                # Send each message as a JSON string followed by a newline
                # Frontend will parse this.
                yield json.dumps(message) + "\n"
        except Exception as e:
            import traceback
            traceback.print_exc() # Log error on server
            error_message = {"type": "error", "content": f"An error occurred during research: {str(e)}"}
            yield json.dumps(error_message) + "\n"
        finally:
            # Ensure the connection is closed gracefully
            print("Streaming complete or disconnected.")

    # Return StreamingResponse with media type text/plain for simpler line-delimited JSON
    return StreamingResponse(event_generator(), media_type="text/plain")