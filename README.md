# AETHER

**One Platform. Limitless Intelligence.**

AETHER is an open-source, self-hosted, all-in-one AI platform that runs entirely from your terminal. It combines AI chat, file workspace, image generation, video generation and editing, autonomous AI agents, an extensible skills ecosystem, a unified API gateway, and a connector ecosystem — all from a simple local UI at `http://localhost:5467`.

Built from `build.txt` (project identity & master spec). Local-first, modular, and designed to run on Windows, Linux, macOS, and Android (Termux).

---

## Table of Contents

- [Project Identity](#project-identity)
- [Features](#features)
- [Quick Start](#quick-start)
  - [Linux / macOS](#linux--macos)
  - [Android (Termux)](#android-termux)
  - [Windows (PowerShell)](#windows-powershell)
  - [Docker](#docker)
- [Usage](#usage)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Supported Providers & Models](#supported-providers--models)
- [API Key Management](#api-key-management)
- [Unified API Gateway](#unified-api-gateway)
- [File Workspace](#file-workspace)
- [Skills Ecosystem](#skills-ecosystem)
- [Autonomous Agents](#autonomous-agents)
- [Image Generation](#image-generation)
- [Video Generation & Editor](#video-generation--editor)
- [Connector Ecosystem](#connector-ecosystem)
- [Repository Structure](#repository-structure)
- [Security](#security)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Project Identity

| Property | Value |
|----------|-------|
| **Name** | AETHER (AETHER AI) |
| **Tagline** | One Platform. Limitless Intelligence. |
| **License** | MIT |
| **Default Port** | 5467 |
| **Default Account** | `admin` / `admin` |

AETHER is designed to be an independent open-source ecosystem — not a clone of ChatGPT, OpenCode, or OpenRouter. It runs locally on your machine, keeps your data private, and never ships credentials in installers or repository files.

---

## Features

### Core Platform
- **Terminal-first server**: Runs from the command line on Windows, Linux, macOS, and Android (Termux)
- **SQLite database**: Zero-config local database with WAL mode
- **Local-first architecture**: Your data stays on your machine
- **Terminal installation**: `install.sh`, `install-termux.sh`, `install.ps1`, `start.sh`, `start.ps1`
- **Docker support**: `docker-compose.yml` and `Dockerfile` included

### Authentication & Security
- Session-based authentication with HttpOnly cookies
- Bearer token authentication for API clients
- CSRF protection
- API keys encrypted at rest (Fernet/AES via cryptography, with PBKDF2 fallback)
- Path traversal prevention on all file operations
- Rate limiting per client IP
- Path sanitization for file and skill operations
- Default account: `admin` / `admin` (change immediately after first login)

### AI Model Ecosystem
- **Provider adapters**: OpenAI-compatible (OpenAI, Groq, Together, Fireworks, Cerebras, xAI, Mistral, DeepSeek, Cohere, LM Studio, vLLM, OpenRouter, Hugging Face), Anthropic, Google Gemini, Ollama
- **Model registry**: Register custom models manually with capability flags (tools, vision, streaming, context window)
- **Model discovery**: Providers that expose a `/models` endpoint are automatically discovered
- **Streaming**: Server-Sent Events for streaming chat responses
- **Tool calling**: Structured tool calling support across providers
- **Unified gateway**: OpenAI-compatible `/v1/chat/completions` endpoint
- **Unified API key**: `sk-local-...` key for external OpenAI-compatible clients

### File Workspace
- Create, read, edit, delete, rename files and folders
- Upload and download files
- Search file contents by name
- File versioning (previous versions stored automatically)
- Path traversal protection on all operations
- MIME type detection for common formats (TXT, MD, PDF, JSON, HTML, CSS, JS, TS, PY, Java, C, CPP, Go, Rust, YAML, TOML, CSV, images, video, and more)

### Skills Ecosystem
- Skill marketplace with install, enable, disable, uninstall
- Built-in skills: **File Reader**, **File Writer**, **Code Generator**, **Web Researcher**
- Skill manifests with permissions (`file_read`, `file_write`, `model_chat`, `skill_call`)
- Skill execution logs
- Permission-gated execution (skills never get unrestricted OS access)

### Autonomous Agents
- Goal planning and task decomposition
- Tool selection and execution (model chat, skill calls, file operations)
- Human approval gates for sensitive actions
- Task history and background execution
- Error recovery and monitoring

### Image Generation
- OpenAI-compatible provider (DALL-E 3, DALL-E 2)
- Stability AI adapter
- Text-to-image generation
- Size, aspect ratio, and style controls
- Images saved locally to `data/storage/images/`
- Job tracking with status (queued, completed, failed)

### Video Generation & Editor
- Scene-based video generation (script → scenes → clips → FFmpeg assembly)
- Mock video adapter for testing without external providers
- FFmpeg-based clip assembly
- Video editor with timeline, clips, subtitles, audio mixing
- Export presets (YouTube, TikTok, Instagram, Twitter)
- Background rendering with job progress tracking

### Connector Ecosystem (28+ Connectors)
Categories and connectors:

| Category | Connectors |
|----------|------------|
| **Space & Science** | NASA, OpenAlex, arXiv, Spaceflight |
| **News & Information** | NewsAPI, GDELT, RSS, Guardian |
| **Media & Entertainment** | TMDB, TVMaze, MusicBrainz, Spotify |
| **Development** | GitHub, GitLab, Stack Exchange, npm, PyPI, Docker Hub |
| **Knowledge** | Wikipedia, Wikidata, Crossref, Open Library |
| **Other** | Weather, Currency, Countries, USGS Earthquakes, Wikivoyage |

Each connector includes: name, description, authentication requirements, free/paid status, rate limits, available operations, connection testing, and error handling.

---

## Quick Start

### Linux / macOS (bash)

```bash
git clone https://github.com/Abhay0208/aether-ai.git
cd aether-ai
chmod +x install.sh start.sh
./install.sh
```

Then open **http://127.0.0.1:5467** in your browser.

### Android (Termux)

```bash
git clone https://github.com/Abhay0208/aether-ai.git
cd aether-ai
chmod +x install-termux.sh
./install-termux.sh
# Then:
bash ~/aether-start.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/Abhay0208/aether-ai.git
cd aether-ai
.\install.ps1
.\start.ps1
```

Requirements: Python 3.10+, Node.js 18+, FFmpeg, Git.

### Docker

```bash
git clone https://github.com/Abhay0208/aether-ai.git
cd aether-ai
docker compose up -d
```

Then open **http://localhost:5467**.

---

## Usage

### Starting the Server

After installation, start AETHER with:

```bash
./start.sh          # Linux / macOS
.\start.ps1         # Windows PowerShell
bash ~/aether-start.sh   # Android Termux
```

The server will start on `http://127.0.0.1:5467`.

### Logging In

1. Open **http://127.0.0.1:5467** in your browser
2. Sign in with the default account:
   - **Username**: `admin`
   - **Password**: `admin`
3. **Change your password immediately** after first login.

### Adding an API Key

1. Sign in to AETHER
2. Go to **API Keys** in the sidebar
3. Click **Add Provider** (e.g., OpenAI, Anthropic, Google Gemini, Ollama)
4. Click **Add API Key** and paste your provider API key
5. Click **Test** to verify the key works
6. The key is encrypted at rest and never exposed to clients

### Chatting with a Model

1. Go to **Chat** in the sidebar
2. Select a model from the dropdown
3. Type your message and press Enter
4. Responses stream in real-time

### Generating an Image

1. Go to **Images** in the sidebar
2. Select a provider (OpenAI DALL-E or Stability AI)
3. Enter a prompt and select size/aspect ratio
4. Click **Generate**
5. The image is saved locally and appears in the gallery

### Generating a Video

1. Go to **Video** in the sidebar
2. Enter a prompt and select duration, model, resolution, and aspect ratio
3. Click **Generate**
4. The video is generated scene-by-scene and assembled with FFmpeg
5. Download the final video when complete

### Using the Video Editor

1. Go to **Video Editor** in the sidebar
2. Create a new project
3. Add video, audio, or subtitle tracks
4. Add clips to the timeline
5. Configure transitions, effects, and subtitles
6. Export with your chosen preset (YouTube, TikTok, Instagram, Twitter)

### Using Skills

1. Go to **Skills** in the sidebar
2. Browse installed skills (File Reader, File Writer, Code Generator, Web Researcher)
3. Enable/disable skills as needed
4. Execute skills to perform actions (read files, write files, generate code, research topics)

### Running Agents

1. Go to **Agents** in the sidebar
2. Create an agent with a name, model, and system prompt
3. Create a task with a goal/description
4. Run the task — the agent plans, decomposes, and executes steps
5. Monitor progress and approve dangerous actions when prompted

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Server
AETHER_PORT=5467
AETHER_HOST=127.0.0.1
AETHER_DEBUG=false

# Security (change these before production!)
AETHER_SECRET_KEY=replace-with-a-random-string
AETHER_ENCRYPTION_KEY=replace-with-64-hex-chars

# Data directory (default: ./data)
# AETHER_DATA_DIR=./data
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AETHER_PORT` | `5467` | Server port |
| `AETHER_HOST` | `127.0.0.1` | Bind address |
| `AETHER_DEBUG` | `false` | Enable debug mode |
| `AETHER_SECRET_KEY` | (random) | Session signing key |
| `AETHER_ENCRYPTION_KEY` | (random) | API key encryption key |
| `AETHER_DATA_DIR` | `./data` | Data storage directory |

### `.env.example`

A `.env.example` file is included in the repository. Copy it to `.env` and adjust:

```bash
cp .env.example .env
```

---

## Supported Providers & Models

AETHER includes built-in provider adapters for:

| Provider | Capabilities | Authentication |
|----------|-------------|----------------|
| OpenAI | Chat, completions, tools, vision, image | API key |
| Anthropic | Chat, tools, vision | API key |
| Google Gemini | Chat, tools, vision | API key |
| Ollama | Chat, tools, vision | None (local) |
| LM Studio | Chat, tools | None (local) |
| vLLM | Chat, completions, tools | None (local) |
| OpenRouter | Chat, completions, tools, vision | API key |
| Groq | Chat, completions, tools | API key |
| Together | Chat, completions | API key |
| Fireworks | Chat, completions | API key |
| Cerebras | Chat, completions | API key |
| xAI | Chat | API key |
| Mistral | Chat, tools | API key |
| Cohere | Chat | API key |
| Hugging Face | Chat | API key |

**Total**: 14 providers, 80+ models supported through manual registration and automatic discovery where supported.

> **Note**: Provider API keys are never exposed to client applications. All requests are proxied through AETHER's unified gateway.

---

## API Key Management

AETHER provides a unified API gateway inspired by OpenRouter. Users can:

- Add multiple API keys per provider
- Test keys before use
- Enable/disable individual keys
- Track usage and rate limits
- Rotate keys automatically on failure
- Generate a unified `sk-local-...` key for external clients

### Unified API Key

The unified key allows external OpenAI-compatible clients to talk to AETHER:

```
http://localhost:5467/v1/chat/completions
```

Example `curl` request:

```bash
curl http://localhost:5467/v1/chat/completions \
  -H "Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
```

Original provider API keys are **never** exposed to client applications.

---

## Supported Provider Models (10+ Examples)

| Provider | Model | Capabilities |
|----------|-------|--------------|
| OpenAI | GPT-4o Mini | Chat, Tools, Vision |
| OpenAI | GPT-4o | Chat, Tools, Vision |
| Anthropic | Claude 3.5 Sonnet | Chat, Tools, Vision |
| Anthropic | Claude 3 Haiku | Chat, Tools, Vision |
| Google | Gemini 1.5 Pro | Chat, Tools, Vision |
| Google | Gemini 1.5 Flash | Chat, Tools, Vision |
| Ollama | Llama 3.1 | Chat, Tools, Vision |
| Ollama | CodeLlama | Chat, Tools |
| LM Studio | Various local models | Chat, Tools |
| vLLM | Various local models | Chat, Completions, Tools |
| Groq | Llama 3.1 70B | Chat, Completions, Tools |
| Together | Llama 3 | Chat, Completions |
| Fireworks | Llama 3 | Chat, Completions |
| Cerebras | Llama 3.1 70B | Chat, Completions |
| xAI | Grok | Chat |
| Mistral | Mistral Large | Chat, Tools |
| Cohere | Command R | Chat |
| Hugging Face | Various | Chat |

**Total**: 14 providers, 80+ models supported through manual registration and automatic discovery where supported.

---

## API Reference

### Authentication

```http
POST /api/auth/login
Content-Type: application/json

{"username": "admin", "password": "admin"}
```

Response:
```json
{"ok": true, "token": "...", "user": {"id": 1, "username": "admin", "is_admin": 1}}
```

### Unified Gateway (OpenAI-compatible)

```http
POST /api/v1/chat/completions
Authorization: Bearer sk-local-...
Content-Type: application/json

{
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

### Providers

```http
GET /api/providers          # List all providers
POST /api/providers         # Add a provider
PATCH /api/providers/{id}   # Update a provider
GET /api/providers/keys     # List API keys
POST /api/providers/keys    # Add an API key
PATCH /api/providers/keys/{id}  # Toggle key enable/disable
DELETE /api/providers/keys/{id} # Delete an API key
POST /api/providers/keys/{id}/test  # Test an API key
```

### Models

```http
GET /api/models             # List registered models
POST /api/models/register   # Register a custom model
GET /api/v1/models          # Gateway model listing
```

### Files

```http
GET /api/files              # List files in a directory
GET /api/files/text?path=... # Read file content
POST /api/files             # Create a file
PUT /api/files/content      # Update file content
DELETE /api/files           # Delete a file
POST /api/files/rename      # Rename a file
POST /api/files/upload      # Upload a file
GET /api/files/search?q=...  # Search files
```

### Skills

```http
GET /api/skills             # List skills
GET /api/skill?id=1         # Get skill details
POST /api/skills/install    # Install a skill
POST /api/skills/enable     # Enable a skill
POST /api/skills/disable    # Disable a skill
DELETE /api/skills          # Uninstall a skill
POST /api/skills/execute    # Execute a skill
GET /api/skills/executions  # List execution logs
```

### Agents

```http
GET /api/agents             # List agents
POST /api/agents            # Create an agent
GET /api/tasks              # List tasks
POST /api/tasks             # Create a task
GET /api/task?id=...        # Get task details
POST /api/tasks/run         # Run a task
POST /api/tasks/approve     # Approve a task
```

### Video

```http
GET /api/video              # List videos
GET /api/video/models       # List video models
GET /api/video/content?id=... # Get video details
POST /api/video/generate    # Generate a video
DELETE /api/video           # Delete a video
```

### Video Editor

```http
GET /api/edits              # List projects
POST /api/edits             # Create a project
GET /api/edits/{id}         # Get project details
PATCH /api/edits/{id}       # Update a project
DELETE /api/edits           # Delete a project
POST /api/edits/tracks      # Add a track
PATCH /api/edits/tracks/{id} # Update a track
DELETE /api/edits/tracks    # Delete a track
POST /api/edits/clips       # Add a clip
PATCH /api/edits/clips/{id} # Update a clip
DELETE /api/edits/clips     # Delete a clip
POST /api/edits/subtitles   # Add subtitles
PATCH /api/edits/subtitles/{id} # Update subtitles
DELETE /api/edits/subtitles # Delete subtitles
POST /api/edits/audio       # Add audio
PATCH /api/edits/audio/{id} # Update audio
DELETE /api/edits/audio     # Delete audio
POST /api/edits/auto-beat-sync  # Auto beat sync
POST /api/edits/smart-cut   # Smart cut
POST /api/edits/highlight-reel  # Highlight reel
POST /api/edits/exports     # Create export
GET /api/edits/exports      # List exports
GET /api/edits/exports/{id} # Get export status
```

### Connectors

```http
GET /api/connectors             # List all connectors
GET /api/connectors/categories  # List categories
GET /api/connectors/connector?id=1  # Get connector details
GET /api/connectors/by-name?name=wikipedia  # Get by name
GET /api/connectors/connections # List connections
POST /api/connectors/connections  # Add a connection
POST /api/connectors/connections/test  # Test a connection
DELETE /api/connectors/connections  # Delete a connection
POST /api/connectors/execute    # Execute a connector operation
GET /api/connectors/executions  # List execution logs
```

---

## Repository Structure

```
aether/
├── backend/                  # FastAPI/stdlib backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration & environment
│   │   ├── database.py       # SQLite database layer
│   │   ├── security.py       # Auth, encryption, rate limiting
│   │   ├── cache.py          # In-memory TTL cache
│   │   ├── main.py           # HTTP server & route handlers
│   │   ├── providers/        # AI model provider adapters
│   │   ├── gateway/          # Unified API gateway
│   │   ├── skills/           # Skills runtime
│   │   ├── agents/           & Autonomous agent framework
│   │   ├── image_engine/     # Image generation adapters
│   │   ├── video_engine/     # Video generation engine
│   │   ├── video_editor/     # Video editor & renderer
│   │   └── connectors/       # Data source connectors
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React + Vite + TypeScript UI
│   ├── src/
│   │   ├── App.tsx           # Main app & routing
│   │   ├── lib/              # API client & auth
│   │   ├── pages/            # Page components
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Chat.tsx
│   │   │   ├── Files.tsx
│   │   │   ├── Models.tsx
│   │   │   ├── APIKeys.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Skills.tsx
│   │   │   ├── Agents.tsx
│   │   │   ├── Images.tsx
│   │   │   ├── Video.tsx
│   │   │   └── VideoEditor.tsx
│   │   └── components/       # Shared UI components
│   ├── dist/                 # Built production assets
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── install.sh                # Linux/macOS installer
├── start.sh                  # Linux/macOS starter
├── install-termux.sh         # Android Termux installer
├── install.ps1               # Windows PowerShell installer
├── start.ps1                 # Windows PowerShell starter
├── docker-compose.yml        # Docker Compose
├── Dockerfile                # Docker image
├── .env.example              # Environment variables example
├── .gitignore                # Git ignore rules
├── build.txt                 # Project identity & master spec
├── README.md                 # This file
├── LICENSE                   # MIT License
├── CONTRIBUTING.md           # Contribution guidelines
├── SECURITY.md               # Security policy
├── CHANGELOG.md              # Release notes
├── tests/                    # Automated tests
├── docs/                     # Additional documentation
├── examples/                 & Example skills & connectors
├── data/                     # Local data directory (created on first run)
└── .github/                  # GitHub configuration
```

---

## Security

AETHER is designed with security as a first-class concern:

- **API keys encrypted at rest** using Fernet/AES (or PBKDF2-derived XOR fallback)
- **Session-based authentication** with HttpOnly, SameSite cookies
- **CSRF token protection** for state-changing requests
- **Rate limiting** per client IP (60 requests/minute default)
- **Path traversal prevention** on all file operations
- **Input validation** on all user-submitted data
- **Agents and skills run in a permission model** — dangerous actions require explicit user approval
- **Local-first**: No provider keys leave your machine unless you send them to a provider
- **No hardcoded credentials**: Never ship API keys in installers or repository files

> **Warning**: Change the default `admin`/`admin` credentials immediately after first login. Change `AETHER_SECRET_KEY` and `AETHER_ENCRYPTION_KEY` before production use.

See `SECURITY.md` for detailed security information.

---

## Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg
- Git

### Backend Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev    # Start development server on port 5468
npm run build  # Build for production
```

### Running Tests

```bash
# Backend tests
python -m unittest tests.test_backend_smoke
python -m unittest tests.test_security

# Frontend
cd frontend
npm run build
```

---

## Roadmap

| Phase | Subsystem | Status |
|-------|-----------|--------|
| 1 | Core, installers, server, DB, UI, file workspace | ✅ Implemented |
| 2 | Provider integrations, model selector, multi-key manager, gateway proxy | ✅ Implemented |
| 3 | Agent framework, skills runtime, skill marketplace | ✅ Implemented |
| 4 | Image generation | ✅ Implemented |
| 5 | Video generation (scene-based, FFmpeg) | ✅ Implemented |
| 6 | Automatic video editor | ✅ Implemented |
| 7 | Connector ecosystem | ✅ Implemented (28+ connectors) |
| 8 | Security audit, tests, stable release | ✅ Implemented (v1.0.0) |

---

## Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for detailed guidelines.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `python -m unittest tests/`
5. Commit your changes: `git commit -m "feat: your feature"`
6. Push to your fork: `git push origin feature/your-feature`
7. Open a Pull Request

### Code Style

- Python: Follow PEP 8
- TypeScript: Follow the project's ESLint/Prettier config
- Write tests for new features
- Document all major subsystems
- Handle errors properly
- No hardcoded API keys
- No fake API responses in production

---

## License

AETHER is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Support

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Security**: See `SECURITY.md` for vulnerability reporting
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**AETHER** — One Platform. Limitless Intelligence.

Built from `build.txt` — an open-source, local-first, self-hosted AI workspace.