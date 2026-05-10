"""Vision-related commands for Jarvis."""
import asyncio
import pyautogui
import google.generativeai as genai
from jarvis.config import config
from jarvis.logger import logger
from jarvis.commands.registry import registry

@registry.register(name="analyze_screen", description="Take a screenshot and describe what is currently on the screen.")
async def analyze_screen() -> str:
    """Take a screenshot and analyze it with Gemini."""
    logger.info("[VISION_SCREEN] Action: Capturing screen")
    
    # 1. Capture screen
    screenshot = await asyncio.to_thread(pyautogui.screenshot)
    path = "temp_vision.png"
    await asyncio.to_thread(screenshot.save, path)
    
    # 2. Upload and analyze with Gemini
    if not config.gemini_api_key:
        return "Vision requires a Gemini API Key, sir."

    try:
        genai.configure(api_key=config.gemini_api_key)
        model = genai.GenerativeModel(config.gemini_model)
        
        # Open and convert image for SDK
        from PIL import Image
        img = Image.open(path)
        
        prompt = "Describe what is on this screen in detail. If there is code, explain what it does. If there are UI elements, list them."
        
        response = await asyncio.to_thread(model.generate_content, [prompt, img])
        logger.info("[VISION_SCREEN] Analysis complete.")
        return response.text
    except Exception as e:
        logger.error(f"[VISION_ERROR] {e}")
        return f"I encountered an error while analyzing the screen: {e}"

@registry.register(name="what_do_you_see", description="Alias for analyze_screen.")
async def what_do_you_see() -> str:
    return await analyze_screen()
