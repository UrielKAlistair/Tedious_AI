from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.post("/api")
async def api(query):
    print(query)
    return "Here is a dummy response to see if my endpoint works"

@app.get("/")
async def resp():
    return "Here is a text message to let you know that the server is up and running!"
