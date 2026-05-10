"""Web-related commands for Jarvis (Search, News, Speedtest)."""
import logging
import webbrowser
import requests
import speedtest
from jarvis.config import NEWS_API_KEY
from jarvis.logger import log_action

def search_google(query: str) -> None:
    """Search Google for a query."""
    log_action("WEB_SEARCH", f"Google | Query: {query}", f"I'm opening Google to search for '{query}'.")
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)

def search_youtube(query: str) -> None:
    """Search YouTube for a query."""
    log_action("WEB_SEARCH", f"YouTube | Query: {query}", f"I'm searching YouTube for '{query}'.")
    url = f"https://www.youtube.com/results?search_query={query}"
    webbrowser.open(url)

def test_internet_speed() -> str:
    """
    Test internet speed.

    Returns:
        str: Summary of download and upload speeds.
    """
    log_action("WEB_SPEEDTEST", "Initializing speedtest-cli", "I'm measuring your current internet speeds.")
    st = speedtest.Speedtest()
    download_speed = st.download() / (10**6)  # Convert to Mbps
    upload_speed = st.upload() / (10**6)      # Convert to Mbps
    result = (f"Download: {download_speed:.2f} Mbps | "
              f"Upload: {upload_speed:.2f} Mbps")
    log_action("WEB_SPEEDTEST_RES", f"Speeds: {result}", "I've finished measuring your internet speed.")
    return result

def fetch_latest_news(category: str = "general") -> list:
    """
    Fetch latest news headlines.

    Args:
        category: News category (business, health, technology, etc.)

    Returns:
        list: List of news titles.
    """
    log_action("WEB_NEWS", f"Category: {category}", f"I'm looking up the latest {category} news.")

    base_url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": category,
        "apiKey": NEWS_API_KEY,
        "language": "en"
    }

    if category == "technology":
        params["q"] = "tesla"

    try:
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            log_action(
                "WEB_NEWS_FAIL",
                f"NewsAPI Error: {data.get('message')}",
                "I couldn't fetch the latest news.",
                level=logging.ERROR
            )
            return []

        articles = data.get("articles", [])
        return [art["title"] for art in articles[:5]]
    except Exception as exc:
        log_action(
            "WEB_NEWS_FATAL",
            f"Exception: {exc}",
            "A critical error occurred while fetching news.",
            level=logging.ERROR
        )
        return []
