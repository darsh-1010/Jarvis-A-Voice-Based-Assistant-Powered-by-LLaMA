"""Web-related commands for Jarvis (Search, News, Speedtest)."""
import webbrowser
import json
import requests
import speedtest
from jarvis.config import NEWS_API_KEY
from jarvis.logger import logger

def search_google(query: str) -> None:
    """Search Google for a query."""
    logger.info(f"[WEB_SEARCH] Site: Google | Query: {query}")
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)

def search_youtube(query: str) -> None:
    """Search YouTube for a query."""
    logger.info(f"[WEB_SEARCH] Site: YouTube | Query: {query}")
    url = f"https://www.youtube.com/results?search_query={query}"
    webbrowser.open(url)

def test_internet_speed() -> str:
    """
    Test internet speed.

    Returns:
        str: Summary of download and upload speeds.
    """
    logger.info("[WEB_SPEEDTEST] Action: Starting test")
    st = speedtest.Speedtest()
    download_speed = st.download() / (10**6)  # Convert to Mbps
    upload_speed = st.upload() / (10**6)      # Convert to Mbps
    result = (f"Download: {download_speed:.2f} Mbps | "
              f"Upload: {upload_speed:.2f} Mbps")
    logger.info(f"[WEB_SPEEDTEST] Result: {result}")
    return result

def fetch_latest_news(category: str = "general") -> list:
    """
    Fetch latest news headlines.

    Args:
        category: News category (business, health, technology, etc.)

    Returns:
        list: List of news titles.
    """
    logger.info(f"[WEB_NEWS] Action: Fetching {category} news")
    
    base_url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": category,
        "apiKey": NEWS_API_KEY,
        "language": "en"
    }
    
    # Custom handling for the specific tech query in original code
    if category == "technology":
        params["q"] = "tesla"
        # The original code used /everything for tech with a specific date
        # For robustness, we'll stick to top-headlines but keep the category
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") != "ok":
            logger.error(f"[WEB_NEWS_ERROR] Status: {data.get('status')} | Message: {data.get('message')}")
            return []
            
        articles = data.get("articles", [])
        titles = [art["title"] for art in articles[:5]] # Limit to top 5
        return titles
    except Exception as exc:
        logger.error(f"[WEB_NEWS_FATAL] Message: {exc}")
        return []
