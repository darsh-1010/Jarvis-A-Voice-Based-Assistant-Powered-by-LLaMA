# 🧠 JARVIS: The Ultimate Voice AI Agent (V3.0 Evolution)

[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)](#)
[![Tech Stack](https://img.shields.io/badge/Stack-Next.js%20%7C%20FastAPI%20%7C%20Ollama-blue)](#)
[![License](https://img.shields.io/badge/License-BUSL--1.1-blue)](#)

**Jarvis** is a state-of-the-art, modular voice assistant that bridges the gap between local privacy and cloud-scale intelligence. Featuring a stunning **"Zenith" Aesthetic HUD**, Jarvis offers a proactive, memory-enabled interaction loop designed for the modern desktop.

---

## ✨ Key Features

### 🎙️ Proactive Voice Interface
- **Ambient Wake Word**: Always listening for "Jarvis" with minimal CPU overhead.
- **Natural Speech**: High-fidelity Text-to-Speech (TTS) with customizable personas.
- **Multimodal Intelligence**: Powered by **Gemma 2 (via Ollama)** and **Gemini 2.0 Flash** for complex reasoning.

### 🖥️ "Zenith" AI Studio (Next.js Dashboard)
- **Glassmorphic UI**: A premium, minimalist interface built with Tailwind CSS and Framer Motion.
- **Real-time Monitoring**: Track system health, background tasks, and active brain status.
- **Dynamic Settings**: On-the-fly adjustment of tone, personality, and voice parameters.
- **Persistent Memory**: Redis-backed memory for long-term user context (Coming Soon).

### 🛠️ Distributed Architecture
- **FastAPI Backend**: A robust API layer managing voice processing, command execution, and state.
- **Modular Commands**: Easily extensible plugin system for Web, Media, and System controls.
- **Docker Ready**: One-command deployment using Docker Compose.

---

## 🚀 Getting Started

### 📦 Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm/bun**
- **Ollama** installed and running (`ollama serve`)
- [Optional] **Docker** & **Docker Compose**

### 🛠️ Local Installation

#### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/darsh-1010/Jarvis-A-Voice-Based-Assistant-Powered-by-LLaMA.git
cd Jarvis

# Install Python dependencies
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env with your API keys (NEWS_API_KEY, GOOGLE_API_KEY, etc.)
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### 3. Launching Jarvis
You can run the unified entry point:
```bash
# From the root directory
python main.py
```
Alternatively, for the API-first HUD experience:
```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

---

## 🐳 Docker Deployment
The fastest way to get Jarvis up and running with all services:
```bash
docker-compose up --build
```
This will launch the Backend (FastAPI) and Frontend (Next.js) in synchronized containers.

---

## 📂 Project Structure
```text
.
├── app/                # FastAPI Backend Layer
│   ├── main.py         # REST API Endpoints
│   └── models.py       # Pydantic Data Schemas
├── frontend/           # Next.js "Zenith" HUD
│   ├── src/app/        # App Router Pages
│   └── src/components/ # UI Components (VoiceOrb, Sidebar, etc.)
├── jarvis/             # Core Logic Package
│   ├── audio.py        # STT and TTS Engines
│   ├── brain.py        # LLM Integration (Ollama/Gemini)
│   ├── commands/       # Feature Plugins (Web, System, Media)
│   └── settings_manager.py # State Persistence
├── main.py             # Desktop CLI Entry Point
└── docker-compose.yml  # Orchestration Config
```

---

## 🗺️ Roadmap (V3.0 Zenith)
- [x] Next.js Dashboard Implementation
- [x] FastAPI Backend Refactoring
- [x] Docker Containerization
- [ ] Redis-backed Contextual Memory
- [ ] Vision-enabled analysis via Gemini 1.5 Pro
- [ ] Mobile-responsive HUD optimization

For a deep dive into the engineering standards, see [JARVIS_V3_ROADMAP.md](./JARVIS_V3_ROADMAP.md).

---

## 🤝 Contributing
We welcome contributions! Please see our [DOCUMENTATION.md](./DOCUMENTATION.md) for architecture details and coding standards.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git checkout -b feat-enhancement`)
5. Open a Pull Request

---

## 📜 License Overview
This repository is source-available under a **Business Source License (BSL 1.1)**. 

### 🚫 Commercial Usage & AI Training
Commercial usage, commercial AI training, hosted services, and proprietary deployments require a separate commercial agreement. **Unauthorized commercial AI training is strictly prohibited.**

### 💼 Enterprise & Custom Licensing
For commercial usage, closed-source deployments, or AI training rights (LLMs, embeddings, fine-tuning), please contact the owner.

**Contact:** <YOUR_EMAIL>

See [LICENSE](./LICENSE), [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md), and [AI_TRAINING_POLICY.md](./AI_TRAINING_POLICY.md) for full details.

Developed with ❤️ by **Darsh** and the **Antigravity AI** team.

