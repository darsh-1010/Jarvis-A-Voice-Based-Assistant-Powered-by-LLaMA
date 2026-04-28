"""Media-related commands for Jarvis (Camera, Spotify, YouTube)."""
import time
import random
import webbrowser
import cv2
from jarvis.logger import logger

def open_spotify(song_name: str) -> None:
    """
    Search for a song on Spotify.

    Args:
        song_name: Name of the song to search for.
    """
    logger.info(f"[MEDIA_SPOTIFY] Action: Searching for {song_name}")
    search_url = f"https://open.spotify.com/search/{song_name}"
    webbrowser.open(search_url)

def play_random_music() -> None:
    """Play a random favorite song on YouTube."""
    songs = [
        "https://www.youtube.com/watch?v=v-icNVDbVLk",
        "https://www.youtube.com/watch?v=pxCWiYFkvTg",
        "https://www.youtube.com/watch?v=DCkRJ8BDRQU"
    ]
    song = random.choice(songs)
    logger.info("[MEDIA_YOUTUBE] Action: Playing favorite music")
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
        logger.info("[MEDIA_CAMERA] Action: Opening live feed")
        
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
            logger.info("[MEDIA_CAMERA] Action: Closing live feed")

    def take_photo(self) -> str:
        """
        Take a photo after a 5-second countdown.

        Returns:
            str: Path to the saved photo.
        """
        logger.info("[MEDIA_CAMERA] Action: Taking photo in 5s")
        # In a real assistant, the Speak() would happen before this
        time.sleep(5)
        
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        file_path = "photo.jpg"
        if ret:
            cv2.imwrite(file_path, frame)
            logger.info(f"[MEDIA_CAMERA] Status: Photo saved to {file_path}")
        cap.release()
        return file_path
