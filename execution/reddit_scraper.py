import sys
import requests
import json
import logging
import os
from typing import List, Dict, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline

# Configure logging to write to tmp/scraper.log (renamed from .tmp for docker compatibility)
LOG_DIR = "tmp"
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure logger
logger = logging.getLogger("reddit_scraper")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# File handler
file_handler = logging.FileHandler(LOG_FILE, mode='w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console / Docker logs handler (StreamHandler)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

import threading

analyzer = SentimentIntensityAnalyzer()
summarizer = None
summarizer_lock = threading.Lock()

def get_summarizer():
    global summarizer
    # Use a lock so that 5 concurrent threads don't attempt to download
    # the model to the exact same cache directory simultaneously
    with summarizer_lock:
        if summarizer is None:
            logger.info("Initializing ultra-light AI Summarizer (T5-Small)...")
            # Falconsai/text_summarization is a T5-small fine-tune. Exceptionally fast on CPU (~1-2s).
            summarizer = pipeline("summarization", model="Falconsai/text_summarization", device=-1)
    return summarizer

def get_sentiment_label(score: float) -> str:
    """Classify sentiment score into Neutral, Positive, or Negative."""
    if score >= 0.05:
        return "Positive"
    elif score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

def get_post_data_and_summary(post_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Fetch comments for a post and calculate average sentiment and generate an AI summary."""
    url = f"https://old.reddit.com/comments/{post_id}.json?sort=top&limit=15"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 403 or response.status_code == 429:
            # On AWS IP Block
            return {
                "sentiment": {"score": 0, "label": "Neutral", "count": 0},
                "summary": "AI Insight skipped: Reddit CDN blocked AWS Datacenter scraping for comments."
            }
            
        response.raise_for_status()
        data = response.json()
        
        # Reddit comments JSON structure: [post_data, comments_data]
        comments = data[1].get('data', {}).get('children', [])
        
        scores = []
        comment_texts = []
        for comment in comments:
            body = comment.get('data', {}).get('body', '')
            if body and len(body) > 10 and "[deleted]" not in body:
                vs = analyzer.polarity_scores(body)
                scores.append(vs['compound'])
                comment_texts.append(body)
        
        # Sentiment calculation
        if not scores:
            summary = "No discussion available for analysis."
            sentiment = {"score": 0, "label": "Neutral", "count": 0}
        else:
            avg_score = sum(scores) / len(scores)
            sentiment = {
                "score": round(float(avg_score), 3),
                "label": get_sentiment_label(avg_score),
                "count": len(scores)
            }
            
            # AI Summary generation (Optimized for speed)
            # Only use the top 3 comments to drastically reduce inference time
            combined_text = " ".join(comment_texts[:3])
            if len(combined_text) > 50:
                # Truncate strictly to avoid quadratic scaling in Transformer attention
                input_text = combined_text[:400]
                summarizer_func = get_summarizer()
                # Run with minimal max_length to stop generating early
                summary_output = summarizer_func(input_text, max_length=30, min_length=10, do_sample=False)
                summary = summary_output[0]['summary_text'].strip()
            else:
                summary = "Discussion too short for a detailed AI summary."

        return {
            "sentiment": sentiment,
            "summary": summary
        }
    except Exception as e:
        import traceback
        logger.error(f"Error fetching data/summary for post {post_id}: {str(e)}")
        # Suppress traceback mapping in stdout to keep logs clean
        return {
            "sentiment": {"score": 0, "label": "Neutral", "count": 0},
            "summary": f"Insight unavailable: {str(e)}"
        }

def get_top_posts_pullpush(query: str, limit: int = 100, top_k: int = 5) -> List[Dict[str, Any]]:
    """Failover function that uses the pullpush.io community ingestor to bypass AWS Datacenter blocks."""
    logger.info(f"Fallback triggered: Fetching from pullpush.io mirror for query '{query}'")
    url = f"https://api.pullpush.io/reddit/search/submission/?q={query}&size={limit}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        posts = data.get('data', [])
        logger.info(f"Successfully retrieved {len(posts)} posts from PullPush.")
        
        processed_posts = []
        for post in posts:
            upvotes = post.get('score', 0)
            comments_count = post.get('num_comments', 0)
            
            # Engagement Score
            score = upvotes + (comments_count * 2)
            
            processed_posts.append({
                'id': post.get('id'),
                'title': post.get('title', 'No Title'),
                'author': post.get('author', 'Unknown'),
                'url': f"https://www.reddit.com{post.get('permalink', '')}",
                'upvotes': upvotes,
                'comments': comments_count,
                'score': score,
                'created_utc': post.get('created_utc', 0),
                'thumbnail': ''
            })
            
        # Sort by the calculated score descending
        sorted_posts = sorted(processed_posts, key=lambda x: x['score'], reverse=True)[:top_k]
        
        # Attempt to get comments from reddit for these top posts. If 403, we get the graceful degradation built in get_post_data_and_summary
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        logger.info(f"Analyzing sentiment with failover awareness...")
        import concurrent.futures
        def process_post(post):
            insight = get_post_data_and_summary(post['id'], headers)
            post['sentiment'] = insight['sentiment']
            post['ai_summary'] = insight['summary']
            logger.info(f"Post Analysis Complete: {post['title'][:50]}...")
            return post

        with concurrent.futures.ThreadPoolExecutor(max_workers=top_k) as executor:
            top_posts = list(executor.map(process_post, sorted_posts))
            
        return top_posts

    except Exception as e:
        logger.error(f"Fallback pullpush API also failed: {str(e)}")
        return []

def get_top_posts(query: str, limit: int = 100, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search Reddit for the most recent posts matching the query and return the top K based on engagement and sentiment with AI summaries.
    """
    logger.info(f"Starting Reddit search for query: '{query}'")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    url = f"https://old.reddit.com/search.json?q={query}&sort=new&limit={limit}"
    logger.info(f"Fetching posts from: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        # If AWS IP is blocked by Fastly
        if response.status_code == 403 or response.status_code == 429:
            logger.warning(f"Reddit actively blocked AWS IP ({response.status_code}). Initiating failover to PullPush.io...")
            return get_top_posts_pullpush(query, limit, top_k)
            
        response.raise_for_status()
        data = response.json()
        
        posts = data.get('data', {}).get('children', [])
        logger.info(f"Successfully retrieved {len(posts)} posts from Reddit.")
        
        processed_posts = []
        for post in posts:
            post_data = post.get('data', {})
            upvotes = post_data.get('ups', 0)
            comments_count = post_data.get('num_comments', 0)
            
            # Engagement Score: Weight comments slightly more than upvotes
            score = upvotes + (comments_count * 2)
            
            processed_posts.append({
                'id': post_data.get('id'),
                'title': post_data.get('title', 'No Title'),
                'author': post_data.get('author', 'Unknown'),
                'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                'upvotes': upvotes,
                'comments': comments_count,
                'score': score,
                'created_utc': post_data.get('created_utc', 0),
                'thumbnail': post_data.get('thumbnail', '')
            })
            
        # Sort by the calculated score descending
        sorted_posts = sorted(processed_posts, key=lambda x: x['score'], reverse=True)
        top_posts = sorted_posts[:top_k]
        
        logger.info(f"Analyzing sentiment and generating AI summaries for the top {top_k} posts concurrently...")
        import concurrent.futures

        def process_post(post):
            insight = get_post_data_and_summary(post['id'], headers)
            post['sentiment'] = insight['sentiment']
            post['ai_summary'] = insight['summary']
            logger.info(f"Post Analysis Complete: {post['title'][:50]}...")
            return post

        # Execute the 5 summary and sentiment fetches concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=top_k) as executor:
            top_posts = list(executor.map(process_post, top_posts))
            
        return top_posts
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Reddit: {str(e)}")
        return get_top_posts_pullpush(query, limit, top_k)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response from Reddit: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        return []

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "technology"
    results = get_top_posts(query)
    print(json.dumps(results, indent=2))
