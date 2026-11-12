# Changelog

## 0.8.0 — Phase 8: Security audit, tests, stable release (released)

- Security hardening: PBKDF2 password hashing, HMAC-signed access tokens with expiry, encrypted API key storage (per-encryption salt), path traversal prevention, input validation, rate limiting
- Rate limiting middleware: per-client-IP request throttling with configurable limits
- Response caching: TTL-based in-memory cache for model listings and provider data with cache invalidation on writes
- Comprehensive test suite: security unit tests (12 tests) + backend smoke tests (17 tests) = 29 tests passing
- Stable release: v1.0.0

## 0.7.0 — Phase 7: Connector ecosystem (released)

- 28+ modular data source connectors across 6 categories:
  Space and Science, News and Information, Media and Entertainment,
  Development, Knowledge, Other
- Built-in providers: OpenAI-compatible, Anthropic, Google Gemini, Ollama,
  Wikipedia, NASA, TMDB, MusicBrainz, OpenLibrary, Weather, Currency,
  GitHub, GitLab, npm, PyPI, Docker Hub, Stack Exchange, TVMaze, and more
- Connector CRUD: list, get by ID/name, add, test connection, delete
- Connection management with encrypted auth config storage
- Operation execution with full audit logging
- Per-connector capabilities and operation definitions
- Frontend Connector page

## 0.6.0 — Phase 6: Automatic video editor (released)

- Multi-track timeline editor (video, audio, subtitle tracks)
- Clip management: add, update, delete, reorder, trim (in/out points)
- Subtitle/caption support with styling
- Multi-track audio mixing with volume and fade in/out
- Automatic editing modes: beat sync, smart cut, highlight reel
- FFmpeg-based rendering with export presets (YouTube, TikTok, Instagram, Twitter)
- Background rendering jobs with progress tracking
- Project CRUD: list, get, update, delete
- Frontend Video Editor page

## 0.5.0 — Phase 5: Video generation (released)

- Scene-based AI video generation engine per build.txt section 7
- Pipeline: script generation (via model chat) → scene splitting → per-scene clip generation → FFmpeg assembly → export
- Long durations handled by combining multiple clips (not pretending single-provider 60-minute renders)
- Mock video adapter (FFmpeg test patterns) for end-to-end testing without external providers
- Video CRUD: list, get, delete (with local file cleanup)
- Job/stage tracking: script, scenes, assemble, export with progress
- Per-scene clips stored in SQLite (video_clips table)
- Frontend Video page: generate, gallery, delete

## 0.4.0 — Phase 4: Image generation (released)

- Universal image generation engine with provider adapters:
  OpenAI-compatible (DALL·E 3, DALL·E 2) and Stability AI
- Model discovery via provider `/models` endpoints
- Text-to-image generation with size, aspect ratio, negative prompt, style
- Images downloaded and stored locally under `data/storage/images/`
- Resumable generation jobs tracked in SQLite (`images`, `image_jobs`)
- Image CRUD: list, get, delete (with local file cleanup)
- Honest 403 when a provider has no API key configured (no fake images)

## 0.3.0 — Phase 3: Agent framework & skills ecosystem (released)

- Skills runtime with permission-gated execution (file_read, file_write,
  model_chat, skill_call); skills never get unrestricted OS access
- Built-in skills: file_reader, file_writer, code_generator, web_researcher
- Skill install/enable/disable/uninstall/execute with execution logs
- Agent orchestrator: goal planning, task decomposition, step execution
  (model chat / skill call / file op), human-approval gates, task history
- Skills + agents API endpoints under /api/skills, /api/agents, /api/tasks
- Frontend Skills and Agents pages

## 0.2.0 — Phase 2: AI provider integrations & unified gateway (released)

- Provider adapters: OpenAI-compatible (OpenAI, Groq, Together, Fireworks,
  Cerebras, xAI, Mistral, DeepSeek, Cohere, LM Studio, vLLM, OpenRouter,
  Hugging Face), Anthropic, Google Gemini, Ollama — real HTTP calls, no mocks
- Model discovery via provider `/models` endpoints plus DB registry
- Streaming chat completions (Server-Sent Events) end-to-end
- Tool calling and vision capability flags per model
- Unified gateway (`/api/v1/chat/completions`, `/api/v1/models`) with
  API-key rotation, load balancing, automatic fallback on provider errors
- Usage tracking (tokens per provider/model), key test/enable/disable
- Unified `sk-local-` key endpoint reports `/api/v1/chat/completions`

## 0.1.0 — Phase 1 foundation (released)

- Project scaffold per `build.txt`: full directory structure, installers, docs
- Backend: stdlib-only server (asyncio + sqlite3), auth/sessions, encrypted API-key storage
- Frontend: React + Vite + TypeScript + Tailwind UI (chat, files, models, API keys, settings, dashboard)
- File workspace: full CRUD, upload, search, versions, path-traversal protection
- Providers: 14 built-in provider definitions, key add/test/toggle/delete
- Gateway: `/v1/models`, `/v1/chat/completions` foundation, unified `sk-local-` key
- Installers: `install.sh`, `install-termux.sh`, `install.ps1`, `start.sh`, `start.ps1`, `docker-compose.yml`
