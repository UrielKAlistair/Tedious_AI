from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

@app.post("/api")
async def api(request: Request):
    data = await request.json()
    return JSONResponse(content={"answer": "42", "links":"https://discourse.onlinedegree.iitm.ac.in/t/project1-virtual-ta-discussion-thread-tds-may-2025/176077"})

@app.get("/")
async def root():
    return JSONResponse(content={"message": "Dummy response works!", "answer": "42"})
