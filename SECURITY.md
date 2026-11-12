# Security

## Supported versions

Only the latest release receives security patches.

## Reporting

Email the maintainer or open a private advisory. Do not disclose vulnerabilities in public issues.

## Security model

- API keys are encrypted at rest; original provider keys are never exposed to clients.
- Local-first by default; the server binds to 127.0.0.1 unless you change `AETHER_HOST`.
- File operations prevent path traversal; agents/skills require explicit user approval for dangerous actions.
- Set `AETHER_SECRET_KEY` and `AETHER_ENCRYPTION_KEY` before first production launch.

## Default credentials

The first launch creates a local admin account (`admin` / `admin`). Change the password immediately after first login.
