# 🔮 Reddit Insights Engine

![Reddit Insights Engine Preview](https://via.placeholder.com/800x400.png?text=Reddit+Insights+Engine)

A modern, AI-powered web application that extracts the top 5 most engaging posts from any Reddit topic, analyzes investor sentiment, and uses Generative AI (Local NLP Models) to summarize community discussions in seconds. Built with a sleek Glassmorphism UI and fully Dockerized for production.

## ✨ Features

- **Smart Engagement Scoring:** Fetches latest posts and ranks them based on a custom algorithm `(Upvotes + Comments * 2)`.
- **Local AI Summaries (Generative AI):** Uses HuggingFace Transformers (T5-Small model) to read the top comments of a post and generate a single-sentence insight summarizing the community's thoughts. Fast, private, and runs entirely on the CPU (~2-5s latency).
- **Sentiment Analysis (NLP):** Uses `vaderSentiment` to analyze the tone of the top comments and classify the general sentiment (Positive, Neutral, Negative) with color-coded UI badges.
- **Multithreaded Processing:** Employs concurrent Python threads for simultaneous scraping and AI inference, reducing response times drastically.
- **Webhook Integration:** Built-in "Export to Webhook" feature to instantly push JSON payloads (Post Data + Sentiment + AI Summary) into automation workflows like Zapier, Make, or n8n.
- **Modern UI/UX:** Built with Vite + React featuring a stunning dark mode, glassmorphism design, and micro-animations.
- **Production Ready:** Fully containerized using Docker and Docker Compose with NGINX reverse proxies and persistent volume caching for ML models.

## 🛠️ Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- HuggingFace Transformers (`Falconsai/text_summarization`)
- PyTorch
- VADER Sentiment

**Frontend:**
- React (Vite)
- Vanilla CSS (Modern CSS Modules)

**Infrastructure:**
- Docker & Docker Compose
- NGINX

## 🚀 Getting Started

### Prerequisites

Ensure you have [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.

### Running with Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/reddit-insights-engine.git
   cd reddit-insights-engine
   ```

2. Build and start the containers:
   ```bash
   sudo docker-compose up --build -d
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5173
   ```

*Note: The first time you run a search, the backend will download the AI summarization model (T5-Small) to the persistent `./tmp/cache` volume. This may take 10-20 seconds. Subsequent searches will take ~5 seconds.*

### Running Locally (Without Docker)

**1. Backend Pipeline:**
```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server (Runs on port 8002)
python backend/main.py
```

**2. Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start the Vite dev server
npm run dev
```

## 🔄 Webhook Export Format

When you export a generated insight to your webhook, the engine sends a POST request with the following JSON schema:

```json
{
  "posts": [
    {
      "id": "1rp8zxg",
      "title": "Example Reddit Post Title",
      "author": "Username",
      "url": "https://reddit.com/r/...",
      "upvotes": 552,
      "comments": 96,
      "score": 744,
      "created_utc": 1104537600.0,
      "sentiment": {
        "score": 0.45,
        "label": "Positive",
        "count": 10
      },
      "ai_summary": "The community overwhelmingly agrees that this new technology will reshape the industry."
    }
  ]
}
```

## 📝 License

This project is open-source and available under the terms of the MIT License.
