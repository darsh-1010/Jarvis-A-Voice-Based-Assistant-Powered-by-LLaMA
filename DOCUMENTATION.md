# 🧠 Jarvis AI Documentation (v3.0 - Zenith HUD)

Welcome to the documentation for **Jarvis v3**. This version introduces a high-end web interface, multi-model cloud intelligence, and a distributed API-first architecture.

---

## 🚀 The v3 Architecture

Jarvis now operates as a **Distributed System**:

1.  **🧠 Multi-Model Brain**:
    - **Ollama (Local)**: Private and offline reasoning.
    - **Gemini 2.0 Flash (Cloud)**: High-speed, high-reasoning, and vision-ready.
    - **OpenRouter (Cloud)**: Access to various open-source models.
    - Jarvis automatically switches or allows you to pick the brain that suits your needs.

2.  **🌐 API-First Design**:
    - The backend is powered by **FastAPI**, enabling real-time communication between the voice engine and the dashboard.
    - The frontend is a modern **Next.js** application providing a visual HUD.

---

## 🛠️ Setup Instructions

### Backend (FastAPI)
1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `uvicorn app.main:app --reload --port 8000`

### Frontend (Next.js)
1. Navigate to `frontend/`.
2. Install: `npm install`
3. Run: `npm run dev`
4. Access the dashboard at `http://localhost:3000`

---

## 📜 Engineering Standards
Jarvis follows the **Zenith Design Principles**:
- **Invisible Computing**: UI should be ambient and non-obtrusive.
- **Privacy First**: Local LLMs are prioritized for sensitive tasks.
- **Extensibility**: All features are implemented as isolated command plugins.
