import sys
import os
import requests
import json
import redis

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add execution directory to path to import scraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from execution.reddit_scraper import get_top_posts

app = FastAPI(title="Reddit Scraper API")

# Initialize Redis Client. Defaults to localhost for local dev, uses 'redis_cache' for Docker.
REDIS_HOST = os.getenv("REDIS_HOST", "redis_cache")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

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
        query_clean = request.query.lower().strip()
        cache_key = f"search:{query_clean}"
        
        # 1. Check Redis Cache First
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                print(f"Cache Hit for query: '{query_clean}'")
                return {"status": "success", "data": json.loads(cached_data), "cached": True}
        except redis.RedisError as e:
            print(f"Redis connection error during read: {e}")
            
        # 2. Cache Miss: Execute the full expensive scraping logic
        print(f"Cache Miss for query: '{query_clean}', executing scraper...")
        results = get_top_posts(request.query)
        
        if not results:
            return {"status": "success", "data": [], "message": "No results found or an error occurred."}
            
        # 3. Save to Cache for 1 hour (3600 seconds)
        try:
            redis_client.setex(cache_key, 3600, json.dumps(results))
        except redis.RedisError as e:
            print(f"Redis connection error during write: {e}")
            
        return {"status": "success", "data": results, "cached": False}
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
