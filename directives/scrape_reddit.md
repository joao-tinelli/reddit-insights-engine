# Scrape Reddit Directive

## Goal
Search Reddit for a specific topic, retrieve the 100 most recent posts, calculate an engagement score based on upvotes and comments, and return the top 5 most relevant and engaged posts.

## Inputs
- `query` (string): The topic to search for.

## Tools/Scripts
Use `execution/reddit_scraper.py` to perform the action.

## Outputs
- Returns a JSON array of the top 5 post objects containing:
  - `title`
  - `author`
  - `url`
  - `upvotes`
  - `comments`
  - `score`
  - `created_utc`
- Logs progress to `.tmp/scraper.log`.

## Edge Cases
- Reddit API may return 429 Too Many Requests if rate limited. The script should use a custom User-Agent to avoid immediate blocks.
- If no results are found, it should return an empty list gracefully.
