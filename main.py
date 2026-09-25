import os
import asyncio
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine.manager import BypassManager

app = FastAPI(
    title="Direct Link Bypasser API",
    description="High-speed direct link bypasser for shorteners, multi-redirect chains, and ad networks.",
    version="1.0.0"
)

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INDEX_FILE = os.path.join(TEMPLATES_DIR, "index.html")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class BypassRequest(BaseModel):
    url: str

class BatchBypassRequest(BaseModel):
    urls: List[str]

@app.get("/", response_class=FileResponse)
async def index_page():
    return FileResponse(INDEX_FILE)

@app.get("/api/bypass")
async def bypass_get(url: str = Query(..., description="The shortlink or redirect URL to bypass")):
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter.")
    result = await BypassManager.bypass_url(url)
    return JSONResponse(content=result)

@app.post("/api/bypass")
async def bypass_post(req: BypassRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing 'url' field.")
    result = await BypassManager.bypass_url(req.url)
    return JSONResponse(content=result)

@app.post("/api/batch-bypass")
async def batch_bypass(req: BatchBypassRequest):
    if not req.urls:
        raise HTTPException(status_code=400, detail="Empty 'urls' array.")
    tasks = [BypassManager.bypass_url(u) for u in req.urls if u.strip()]
    results = await asyncio.gather(*tasks)
    return JSONResponse(content={"total": len(results), "results": results})

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Direct Link Bypasser"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
