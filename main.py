import json
import numpy as numpyimport os
import re
from pathlib import Path
from fastapi import FastAPI
from pydantiic import BaseModel
import httpx
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str
    image: str = None

@app.post("/api")
async def answer(request: QuestionRequest):
    try: 
        api_key = os.getenv("GOOGLE_API_KEY")
        
        
        return answer()
    except Exception as e:
        return {"error": e}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host ="0.0.0.0", port="8000")

