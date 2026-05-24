"""
Tests for jarvis/commands/media.py — CameraManager and web media commands.
"""
import pytest
from unittest.mock import MagicMock, patch, call


class TestSearchSpotifyWeb:
    """Tests for the search_spotify_web command."""

    def test_opens_browser_with_song(self, mocker):
        """search_spotify_web should open a Spotify URL containing the song name."""
        mock_browser = mocker.patch("jarvis.commands.media.webbrowser.open")
        from jarvis.commands.media import search_spotify_web
        search_spotify_web("Blinding Lights")
        mock_browser.assert_called_once()
        url = mock_browser.call_args[0][0]
        assert "spotify.com" in url
        assert "Blinding Lights" in url

    def test_opens_correct_base_url(self, mocker):
        """The URL should point to open.spotify.com/search."""
        mock_browser = mocker.patch("jarvis.commands.media.webbrowser.open")
        from jarvis.commands.media import search_spotify_web
        search_spotify_web("test song")
        url = mock_browser.call_args[0][0]
        assert url.startswith("https://open.spotify.com/search/")


class TestPlayRandomMusic:
    """Tests for play_random_music command."""

    def test_opens_browser(self, mocker):
        """play_random_music should open a browser tab."""
        mock_browser = mocker.patch("jarvis.commands.media.webbrowser.open")
        from jarvis.commands.media import play_random_music
        play_random_music()
        mock_browser.assert_called_once()

    def test_opens_youtube_url(self, mocker):
        """The opened URL should be a YouTube video URL."""
        mock_browser = mocker.patch("jarvis.commands.media.webbrowser.open")
        from jarvis.commands.media import play_random_music
        play_random_music()
        url = mock_browser.call_args[0][0]
        assert "youtube.com" in url


class TestCameraManager:
    """Tests for the CameraManager class."""

    def test_initial_state(self):
        """CameraManager should start with camera=None and is_open=False."""
        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        assert cam.camera is None
        assert cam.is_open is False

    def test_close_when_camera_is_none(self):
        """close() should not raise when camera is None."""
        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        # Should not raise even though camera is None
        cam.close()

    def test_close_releases_camera(self, mocker):
        """close() should release the camera and destroy windows."""
        mock_cv2 = mocker.patch("jarvis.commands.media.cv2")
        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        cam.camera = MagicMock()
        cam.is_open = True
        cam.close()
        cam.camera.release.assert_called_once()
        mock_cv2.destroyAllWindows.assert_called_once()
        assert cam.is_open is False

    def test_take_photo_returns_path(self, mocker):
        """take_photo should return the file path of the saved image."""
        mock_cv2 = mocker.patch("jarvis.commands.media.cv2")
        mocker.patch("jarvis.commands.media.time.sleep")

        mock_cap = MagicMock()
        fake_frame = MagicMock()
        mock_cap.read.return_value = (True, fake_frame)
        mock_cv2.VideoCapture.return_value = mock_cap

        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        result = cam.take_photo()
        assert result == "photo.jpg"

    def test_take_photo_calls_imwrite_on_success(self, mocker):
        """take_photo should call cv2.imwrite when capture succeeds."""
        mock_cv2 = mocker.patch("jarvis.commands.media.cv2")
        mocker.patch("jarvis.commands.media.time.sleep")

        mock_cap = MagicMock()
        fake_frame = MagicMock()
        mock_cap.read.return_value = (True, fake_frame)
        mock_cv2.VideoCapture.return_value = mock_cap

        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        cam.take_photo()
        mock_cv2.imwrite.assert_called_once_with("photo.jpg", fake_frame)

    def test_take_photo_does_not_write_on_failure(self, mocker):
        """take_photo should not call imwrite when capture fails."""
        mock_cv2 = mocker.patch("jarvis.commands.media.cv2")
        mocker.patch("jarvis.commands.media.time.sleep")

        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_cv2.VideoCapture.return_value = mock_cap

        from jarvis.commands.media import CameraManager
        cam = CameraManager()
        cam.take_photo()
        mock_cv2.imwrite.assert_not_called()
