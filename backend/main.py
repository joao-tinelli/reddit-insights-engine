import sys
import os
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add execution directory to path to import scraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from execution.reddit_scraper import get_top_posts

app = FastAPI(title="Reddit Scraper API")

# Enable CORS for the frontend Vite server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str

class ExportRequest(BaseModel):
    webhook_url: str
    data: list

@app.post("/api/search")
async def search_reddit(request: SearchRequest):
    try:
        results = get_top_posts(request.query)
        if not results:
            return {"status": "success", "data": [], "message": "No results found or an error occurred."}
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export")
async def export_webhook(request: ExportRequest):
    try:
        response = requests.post(
            request.webhook_url,
            json={"posts": request.data},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return {"status": "success", "message": "Successfully exported to webhook."}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to send to webhook: {str(e)}")

@app.get("/api/logs")
async def get_logs():
    log_file = os.path.join(os.path.dirname(__file__), '..', 'tmp', 'scraper.log')
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return {"status": "success", "data": "".join(lines)}
    return {"status": "success", "data": "No logs found yet.", "message": "Log file does not exist."}


if __name__ == "__main__":
    import uvicorn
    # reload=False is crucial here so the 460MB NLP model is not loaded twice during boot
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
