"""
Tests for jarvis/commands/web.py — web commands (search, news, speedtest).
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSearchGoogle:
    """Tests for search_google command."""

    def test_opens_browser_with_query(self, mocker):
        """search_google should open a Google URL containing the query."""
        mock_browser = mocker.patch("jarvis.commands.web.webbrowser.open")
        from jarvis.commands.web import search_google
        search_google("python testing")
        mock_browser.assert_called_once()
        url = mock_browser.call_args[0][0]
        assert "google.com" in url
        assert "python+testing" in url or "python%20testing" in url or "python testing" in url

    def test_search_google_url_format(self, mocker):
        """The URL should start with the Google search base."""
        mock_browser = mocker.patch("jarvis.commands.web.webbrowser.open")
        from jarvis.commands.web import search_google
        search_google("AI news")
        url = mock_browser.call_args[0][0]
        assert url.startswith("https://www.google.com/search")


class TestSearchYoutube:
    """Tests for search_youtube command."""

    def test_opens_browser_with_query(self, mocker):
        """search_youtube should open a YouTube URL containing the query."""
        mock_browser = mocker.patch("jarvis.commands.web.webbrowser.open")
        from jarvis.commands.web import search_youtube
        search_youtube("lofi beats")
        mock_browser.assert_called_once()
        url = mock_browser.call_args[0][0]
        assert "youtube.com" in url

    def test_search_youtube_url_contains_query(self, mocker):
        """YouTube search URL should include the query string."""
        mock_browser = mocker.patch("jarvis.commands.web.webbrowser.open")
        from jarvis.commands.web import search_youtube
        search_youtube("deep focus music")
        url = mock_browser.call_args[0][0]
        assert "search_query" in url or "deep" in url


class TestFetchLatestNews:
    """Tests for fetch_latest_news command."""

    def _mock_news_response(self, mocker, articles=None, status="ok"):
        """Helper to patch requests.get with a fake news response."""
        if articles is None:
            articles = [
                {"title": "Breaking: AI advances"},
                {"title": "Markets surge today"},
            ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": status, "articles": articles}
        mocker.patch("jarvis.commands.web.requests.get", return_value=mock_resp)

    def test_returns_list_of_titles(self, mocker):
        """fetch_latest_news should return a list of headline strings."""
        self._mock_news_response(mocker)
        from jarvis.commands.web import fetch_latest_news
        result = fetch_latest_news()
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    def test_returns_up_to_5_headlines(self, mocker):
        """Should return at most 5 headlines."""
        articles = [{"title": f"Headline {i}"} for i in range(10)]
        self._mock_news_response(mocker, articles=articles)
        from jarvis.commands.web import fetch_latest_news
        result = fetch_latest_news()
        assert len(result) <= 5

    def test_returns_correct_titles(self, mocker):
        """The returned titles should match the article data."""
        self._mock_news_response(mocker, articles=[
            {"title": "AI Is Here"},
            {"title": "Stock Market Rises"},
        ])
        from jarvis.commands.web import fetch_latest_news
        result = fetch_latest_news()
        assert "AI Is Here" in result
        assert "Stock Market Rises" in result

    def test_returns_empty_list_on_api_error(self, mocker):
        """Should return empty list when API status is not 'ok'."""
        self._mock_news_response(mocker, status="error")
        from jarvis.commands.web import fetch_latest_news
        result = fetch_latest_news()
        assert result == []

    def test_returns_empty_list_on_network_error(self, mocker):
        """Should return empty list when a network exception occurs."""
        import requests
        mocker.patch("jarvis.commands.web.requests.get",
                     side_effect=requests.ConnectionError("No internet"))
        from jarvis.commands.web import fetch_latest_news
        result = fetch_latest_news()
        assert result == []

    def test_default_category_is_general(self, mocker):
        """Default category should be 'general'."""
        mock_get = mocker.patch("jarvis.commands.web.requests.get")
        mock_get.return_value.json.return_value = {"status": "ok", "articles": []}
        from jarvis.commands.web import fetch_latest_news
        fetch_latest_news()
        call_kwargs = mock_get.call_args[1]["params"]
        assert call_kwargs["category"] == "general"

    def test_custom_category_is_passed(self, mocker):
        """Custom category should be passed to the API."""
        mock_get = mocker.patch("jarvis.commands.web.requests.get")
        mock_get.return_value.json.return_value = {"status": "ok", "articles": []}
        from jarvis.commands.web import fetch_latest_news
        fetch_latest_news(category="technology")
        call_kwargs = mock_get.call_args[1]["params"]
        assert call_kwargs["category"] == "technology"


class TestTestInternetSpeed:
    """Tests for test_internet_speed command."""

    def test_returns_speed_string(self, mocker):
        """test_internet_speed should return a string with download/upload speeds."""
        mock_st = MagicMock()
        mock_st.download.return_value = 100_000_000  # 100 Mbps in bps
        mock_st.upload.return_value = 50_000_000    # 50 Mbps in bps
        mocker.patch("jarvis.commands.web.speedtest.Speedtest", return_value=mock_st)
        from jarvis.commands.web import test_internet_speed
        result = test_internet_speed()
        assert isinstance(result, str)
        assert "100.00 Mbps" in result
        assert "50.00 Mbps" in result

    def test_speedtest_both_called(self, mocker):
        """Both download() and upload() should be called."""
        mock_st = MagicMock()
        mock_st.download.return_value = 0
        mock_st.upload.return_value = 0
        mocker.patch("jarvis.commands.web.speedtest.Speedtest", return_value=mock_st)
        from jarvis.commands.web import test_internet_speed
        test_internet_speed()
        mock_st.download.assert_called_once()
        mock_st.upload.assert_called_once()
