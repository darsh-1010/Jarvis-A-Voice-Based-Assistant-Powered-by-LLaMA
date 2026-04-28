# 🧠 Jarvis AI Documentation (Professional Version)

Welcome to the documentation for **Jarvis**, your modular, voice-powered AI assistant. Jarvis has been refactored into a professional Python package for better performance, stability, and maintainability.

---

## 🚀 How Jarvis Works (The Hear-Think-Act Loop)

Jarvis follows a streamlined process to interact with you:

1.  **👂 Ear (Audio Manager)**:
    - Jarvis stays in a low-power "waiting" state, monitoring the microphone for the wake word (**"Jarvis"**).
    - It uses **Google Speech Recognition** to convert your spoken words into high-quality text.

2.  **🧠 Brain (Brain Manager)**:
    - Once a command is captured, Jarvis uses its AI brain—powered by **LangChain** and **Ollama (Gemma 2)**.
    - It understands context, maintains conversation history, and decides the best way to respond or act.

3.  **🔊 Voice & Action (Controller)**:
    - **Actions**: If you give a specific command (like "open notepad" or "search Google"), Jarvis uses specialized modules to interact with your OS or the web.
    - **Voice**: Jarvis responds using a Text-to-Speech engine (**pyttsx3**), giving you verbal feedback on everything it does.

---

## 🛠️ The Technology Stack

- **Python 3.11+**: The core language.
- **SpeechRecognition**: Handles audio capture and STT.
- **pyttsx3**: Provides the offline TTS voice.
- **Ollama & LangChain**: Manages the LLM (Gemma 2) for intelligent reasoning.
- **OpenCV (cv2)**: Controls the camera for video feed and snapshots.
- **PyAutoGUI & pynput**: Handles system-level automation (screenshots, volume).
- **Requests & BeautifulSoup**: Fetches live data like news.
- **python-dotenv**: Manages configuration and API keys securely via `.env`.

---

## 📂 Features Breakdown

### 🎙️ Interaction
- **Wake Word**: Jarvis wakes up when he hears his name.
- **Conversational Memory**: Remembers what you said earlier to provide more natural responses.

### 🖥️ System Control
- **Apps**: "Open Notepad", "Open Calculator", "Open Command Prompt".
- **Shortcuts**: "Open source file" (opens your project folder).
- **Volume**: "Volume up", "Volume down".
- **Screenshot**: "Take screenshot" (3s delay).
- **Power**: "Shutdown the system".

### 📸 Multimedia
- **Camera**: "Open camera" (press Q to close), "Click photo" (5s delay).
- **Music**: "Play [song name]" (Spotify), "I am tired" (Random favorite YouTube music).

### 🌐 Web Utilities
- **Search**: "Search for [topic] on Google/YouTube".
- **News**: "Fetch the latest news" (Top 5 headlines).
- **Technician**: "Test internet speed".

---

## ⚙️ Quick Setup
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set up your `.env` with a NewsAPI key.
3.  Ensure Ollama is running `gemma2:2b`.
4.  Run `python main.py`.
