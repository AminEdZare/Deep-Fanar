# deep_research/app.py (MODIFIED FOR STREAMING)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import asyncio
import os
import json # Import json to serialize messages
from openai import OpenAI

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

class TTSRequest(BaseModel):
    text: str

# Initialize OpenAI client for TTS
FANAR_API_KEY = os.getenv("FANAR_API_KEY")
tts_client = OpenAI(
    base_url="https://api.fanar.qa/v1",
    api_key=FANAR_API_KEY
)

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Research Assistant API. Use /research for deep research."}

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    API endpoint to convert text to speech using Fanar TTS.
    """
    try:
        # Limit text length to prevent very long processing times
        max_text_length = 2000  # Reduced from 4000 to prevent timeouts
        text = request.text[:max_text_length]
        
        if len(request.text) > max_text_length:
            text += "... (truncated for speech synthesis - full report available in text)"
        
        # Add timeout to the TTS request
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def create_tts():
            return tts_client.audio.speech.create(
                model="Fanar-Aura-TTS-1",
                input=text,
                voice="default",
            )
        
        # Run TTS in a thread pool with timeout
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            response = await asyncio.wait_for(
                loop.run_in_executor(executor, create_tts),
                timeout=60.0  # 60 second timeout
            )
        
        # Read the audio data
        audio_data = response.read()
        
        # Return the audio file as a response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="TTS request timed out. Please try again with shorter text.")
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(status_code=408, detail="TTS service is taking too long. Please try again with shorter text.")
        elif "upstream" in error_msg.lower():
            raise HTTPException(status_code=503, detail="TTS service is temporarily unavailable. Please try again later.")
        else:
            raise HTTPException(status_code=500, detail=f"TTS failed: {error_msg}")

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