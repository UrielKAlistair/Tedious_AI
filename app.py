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
    print(data)
    return JSONResponse({"message": "Dummy response works!", "answer":"42"})

@app.get("/")
async def root():
    return JSONResponse({"message": "Server is up", "answer":"42"})
