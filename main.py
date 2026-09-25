import os
import sys
import asyncio
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine.manager import BypassManager

app = FastAPI(
    title="Direct Link Bypasser API",
    description="High-speed direct link bypasser for shorteners, multi-redirect chains, and ad networks.",
    version="1.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(rel_path: str) -> str | None:
    candidates = [
        os.path.join(BASE_DIR, rel_path),
        os.path.join(os.path.dirname(BASE_DIR), rel_path),
        os.path.join(os.getcwd(), rel_path),
        rel_path
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def read_file_content(rel_path: str) -> str:
    path = find_file(rel_path)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Mount static if available
static_path = find_file("static")
if static_path:
    app.mount("/static", StaticFiles(directory=static_path), name="static")

class BypassRequest(BaseModel):
    url: str

class BatchBypassRequest(BaseModel):
    urls: List[str]

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def index_page():
    content = read_file_content("templates/index.html")
    if not content:
        content = "<h1>BypassDirect Web Application</h1>"
    return HTMLResponse(content=content)

# Fallback static routes for Vercel Serverless
@app.get("/static/css/style.css")
async def static_css():
    content = read_file_content("static/css/style.css")
    return Response(content=content, media_type="text/css")

@app.get("/static/js/app.js")
async def static_js():
    content = read_file_content("static/js/app.js")
    return Response(content=content, media_type="application/javascript")

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
