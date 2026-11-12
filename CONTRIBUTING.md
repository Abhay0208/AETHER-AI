# Contributing to AETHER

Thanks for helping build AETHER! Follow the rules in `build.txt` section 16:

1. No static mockups or fake API responses in production functionality.
2. No buttons that do nothing.
3. No hardcoded API keys.
4. No unsupported provider capability claims.
5. Write modular, maintainable code; handle errors; add tests; document subsystems.

## How to contribute

1. Fork the repo and create a feature branch.
2. Run `./install.sh` (or `install-termux.sh` on Android) to set up the dev environment.
3. Make changes, run tests (`pytest backend/tests`), and verify the UI at `http://localhost:5467`.
4. Open a pull request with a clear description.

## Subsystems

- `backend/` — API, database, security
- `frontend/` — React UI
- `providers/`, `gateway/` — model providers and unified API
- `agents/`, `skills/` — agent and skills runtime
- `image_engine/`, `video_engine/`, `video_editor/` — media
- `connectors/` — data sources

Respect each provider's terms of service; never bypass authentication or DRM.
