# 🧠 Jarvis: Professional Voice AI Assistant

**Jarvis** is a modular, voice-activated personal assistant built with Python. It leverages **LLaMA (Gemma 2)** via Ollama for intelligent conversation and provides hands-free control over your computer and web tasks.

---

## 🛠️ Installation & Setup

### 1. Requirements
- **Python 3.11+**
- **Ollama** installed and running (`ollama run gemma2:2b`)
- A working microphone and speakers

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
1.  Create a `.env` file in the root directory (based on `.env.example`).
2.  Add your **NewsAPI Key**:
    ```env
    NEWS_API_KEY=your_key_here
    ```

---

## 🚀 Usage

To start the assistant, run:
```bash
python main.py
```

1.  Say **"Jarvis"** to wake him up.
2.  Give your command (e.g., "What time is it?", "Open Notepad", "Search for space travel on Google").
3.  To put him back to sleep, say **"Sleep"**.
4.  To exit, say **"Terminate"**.

---

## 📂 Project Structure

- `main.py`: Entry point and command controller.
- `jarvis/`: Core package containing audio, brain, and logging logic.
- `jarvis/commands/`: Specific modules for system, media, and web features.
- `.agents/`: Documentation and internal engineering standards.

---

## 📜 Documentation
For a detailed look at how Jarvis works, check out:
- [DOCUMENTATION.md](./DOCUMENTATION.md) - User-friendly guide.
- [.agents/documentations/workflow.md](./.agents/documentations/workflow.md) - System architecture.
- [.agents/documentations/function.md](./.agents/documentations/function.md) - Module breakdown.
