"""Media-related commands for Jarvis (Spotify, YouTube music, Camera)."""
import logging
import random
import time
import webbrowser

import cv2

from jarvis.commands.registry import registry
from jarvis.logger import log_action


@registry.register(name="open_spotify", description="Search for and play a song or artist on Spotify.")
def open_spotify(song_name: str) -> None:
    """
    Search for a song on Spotify.

    Args:
        song_name: Name of the song to search for.
    """
    log_action(
        "MEDIA_SPOTIFY",
        f"Search: {song_name}",
        f"I'm searching Spotify for '{song_name}'."
    )
    search_url = f"https://open.spotify.com/search/{song_name}"
    webbrowser.open(search_url)


@registry.register(name="play_random_music", description="Play a random favourite song from YouTube.")
def play_random_music() -> None:
    """Play a random favorite song on YouTube."""
    songs = [
        "https://www.youtube.com/watch?v=v-icNVDbVLk",
        "https://www.youtube.com/watch?v=pxCWiYFkvTg",
        "https://www.youtube.com/watch?v=DCkRJ8BDRQU"
    ]
    song = random.choice(songs)
    log_action(
        "MEDIA_YOUTUBE",
        "Random selection from favorites",
        "I'm playing a random favourite song for you."
    )
    webbrowser.open(song)


class CameraManager:
    """Manages camera operations."""

    def __init__(self):
        """Initialize camera state."""
        self.camera = None
        self.is_open = False

    def open(self) -> None:
        """Open the camera live feed."""
        self.camera = cv2.VideoCapture(0)
        self.is_open = True
        log_action(
            "MEDIA_CAMERA",
            "CV2 VideoCapture(0) active",
            "I'm opening your camera live feed."
        )

        while self.is_open:
            ret, frame = self.camera.read()
            if not ret:
                break
            cv2.imshow("Jarvis Camera", frame)

            # Press 'q' or 'Esc' to close
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                self.close()
                break

    def close(self) -> None:
        """Close the camera."""
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            self.is_open = False
            log_action(
                "MEDIA_CAMERA",
                "CV2 release and cleanup",
                "I've closed the camera live feed."
            )

    def take_photo(self) -> str:
        """
        Take a photo after a 5-second countdown.

        Returns:
            str: Path to the saved photo.
        """
        log_action(
            "MEDIA_CAMERA",
            "CV2 Capture (5s delay)",
            "I'm taking a photo for you in 5 seconds."
        )
        # Delay allows the user to compose the shot
        time.sleep(5)

        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        file_path = "photo.jpg"
        if ret:
            cv2.imwrite(file_path, frame)
            log_action(
                "MEDIA_CAMERA",
                f"Saved: {file_path}",
                "I've saved the photo to your project folder.",
                level=logging.INFO
            )
        cap.release()
        return file_path
