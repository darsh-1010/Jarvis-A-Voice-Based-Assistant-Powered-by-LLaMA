import asyncio
import logging
from jarvis.audio import AudioManager

# Configure logging to see the output
logging.basicConfig(level=logging.INFO)

async def test_audio():
    print("--- Jarvis Audio Stack Test ---")
    audio = AudioManager()
    
    # Test TTS
    test_text = "Hello! I am your Jarvis assistant, now powered by Kokoro and Faster-Whisper. How do I sound?"
    print(f"\n[TTS Test] Speaking: '{test_text}'")
    await audio.speak(test_text)
    
    # Test STT
    print("\n[STT Test] Please say something in 3 seconds...")
    await asyncio.sleep(1)
    print("3...")
    await asyncio.sleep(1)
    print("2...")
    await asyncio.sleep(1)
    print("1...")
    
    command = await audio.listen("Testing your hearing...")
    if command:
        print(f"\n[STT Result] I heard: '{command}'")
        await audio.speak(f"I heard you say: {command}")
    else:
        print("\n[STT Result] I didn't hear anything.")

if __name__ == "__main__":
    asyncio.run(test_audio())
