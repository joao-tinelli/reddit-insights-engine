import React, { useState } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api';

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setPosts([]);

    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      
      if (data.status === 'success') {
        if (data.data && data.data.length > 0) {
          setPosts(data.data);
        } else {
          setError('No posts found or rate limit reached. See local logs for details.');
        }
      } else {
        throw new Error(data.message || 'Error occurred during processing.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!webhookUrl.trim() || posts.length === 0) return;
    
    setExporting(true);
    setExportStatus(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ webhook_url: webhookUrl, data: posts }),
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || 'Failed to export to webhook');
      }
      
      setExportStatus({ type: 'success', message: 'Data exported successfully!' });
      setTimeout(() => setExportStatus(null), 4000);
      
    } catch (err) {
      setExportStatus({ type: 'error', message: err.message });
      setTimeout(() => setExportStatus(null), 5000);
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (utcTimestamp) => {
    const date = new Date(utcTimestamp * 1000);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Reddit Insights Engine</h1>
        <p>Extract top 5 posts from any topic using smart engagement scoring.</p>
      </header>

      <form className="search-section" onSubmit={handleSearch}>
        <input 
          type="text" 
          className="search-input" 
          placeholder="Enter a topic (e.g., Artificial Intelligence)..." 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button type="submit" className="btn" disabled={loading || !query.trim()}>
          {loading ? 'Scraping...' : 'Analyze'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="main-content">
        <div className="results-container">
          <div className="results-header">
            <h2>Top Posts Ranked by Engagement</h2>
            
            {posts.length > 0 && (
              <div className="export-section">
                <input
                  type="url"
                  className="export-input"
                  placeholder="Paste Webhook URL (Make, Zapier)..."
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
                <button 
                  className="btn" 
                  style={{ padding: '0 1rem', fontSize: '0.9rem' }}
                  onClick={handleExport}
                  disabled={exporting || !webhookUrl}
                >
                  {exporting ? 'Exporting...' : 'Export'}
                </button>
              </div>
            )}
          </div>

          {exportStatus && (
            <div className={`export-status ${exportStatus.type}`}>
              {exportStatus.message}
            </div>
          )}
          
          {posts.length === 0 && !loading && !error && (
            <div className="status-message">
              Ready to execute. Enter a topic above to begin.
            </div>
          )}

          {loading && posts.length === 0 && (
            <div className="status-message">
              Connecting to Reddit API, applying heuristic scoring...
              <div className="pulse loading" style={{ display: 'inline-block', marginLeft: '10px' }}></div>
            </div>
          )}

          {posts.map((post, index) => (
            <div className="post-card" key={index}>
              <div className="post-header">
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <a href={post.url} target="_blank" rel="noopener noreferrer" className="post-title" style={{ marginBottom: 0 }}>
                      {post.title}
                    </a>
                    {post.sentiment && (
                      <span className={`sentiment-badge ${post.sentiment.label.toLowerCase()}`}>
                        {post.sentiment.label}
                      </span>
                    )}
                  </div>
                  <div className="post-meta">
                    Posted by <span className="post-author">u/{post.author}</span> • {formatDate(post.created_utc)}
                  </div>
                </div>
              </div>
              
              {post.ai_summary && (
                <div className="ai-insight">
                  <div className="ai-label">AI INSIGHT</div>
                  <p>{post.ai_summary}</p>
                </div>
              )}

              <div className="post-stats">
                <div className="stat-item score">
                  Score: <span className="highlight">{post.score}</span>
                </div>
                <div className="stat-item">
                  ↑ <span className="highlight">{post.upvotes}</span>
                </div>
                <div className="stat-item">
                  💬 <span className="highlight">{post.comments}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
