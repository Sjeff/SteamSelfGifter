# SteamSelfGifter

[![Tests](https://github.com/Sjeff/SteamSelfGifter/actions/workflows/test.yml/badge.svg)](https://github.com/Sjeff/SteamSelfGifter/actions/workflows/test.yml)
[![Docker](https://github.com/Sjeff/SteamSelfGifter/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Sjeff/SteamSelfGifter/actions/workflows/docker-publish.yml)
[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

SteamSelfGifter is an automated bot for entering Steam game giveaways on SteamGifts.com. It features a modern web interface for managing your giveaway entries, tracking wins, and configuring automation settings — with full multi-account support.

## Features

- **Multi-Account Support**: Manage multiple SteamGifts accounts from a single dashboard, with an account switcher in the sidebar
- **Per-Account Settings**: Every setting (DLC, Safety, Auto-Join Rules, Scheduler, Rate Limiting) is configurable independently per account
- **Web Dashboard**: Modern React-based UI for monitoring and control
- **Wishlist Integration**: Automatically enters giveaways for games on your Steam wishlist
- **DLC Support**: Optional support for DLC giveaways (per account)
- **Smart Auto-join**: Automatically enters giveaways based on customizable criteria:
  - Minimum price threshold
  - Minimum review score
  - Minimum number of reviews
- **Safety Detection**: Detects and avoids trap/scam giveaways with background safety checks (per account)
- **Win Tracking**: Track your wins and win rate statistics
- **Real-time Updates**: WebSocket-based live notifications
- **Analytics Dashboard**: View entry statistics and trends
- **Activity Logs**: View detailed logs of all bot activity

## Quick Start

### Docker (Recommended)

```bash
# Using the pre-built image from GitHub Container Registry
docker run -d \
  --name steamselfgifter \
  -p 8080:80 \
  -v steamselfgifter-data:/config \
  ghcr.io/sjeff/steamselfgifter:latest

# Access the web interface at http://localhost:8080
```

Or with Docker Compose (recommended for external deployments):

```bash
# Download the compose file
curl -O https://raw.githubusercontent.com/Sjeff/SteamSelfGifter/master/docker-compose.yml

# Start
docker-compose up -d

# Access the web interface at http://localhost:8080
```

No clone needed — `docker-compose.yml` pulls the pre-built image from `ghcr.io` directly.

### Development / build from source

```bash
# Clone the repository
git clone https://github.com/Sjeff/SteamSelfGifter.git
cd SteamSelfGifter

# Build and start locally
docker-compose -f docker-compose.dev.yml up -d

# Access the web interface at http://localhost:8080
```

### Manual Installation

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Start the backend
cd src
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev  # Development server at http://localhost:5173
```

## Configuration

Settings are configured **per account** via the Accounts page:

1. Open the web interface
2. Go to **Accounts**
3. Add an account and expand it to enter your SteamGifts credentials (PHPSESSID + User Agent)
4. Open the **Settings** panel within the account to configure:
   - Enable/disable automation and auto-join
   - Enable/disable DLC giveaways
   - Set auto-join criteria (min price, score, reviews)
   - Enable safety check for trap detection
   - Scheduler interval and rate limiting

### How to get your PHPSESSID

1. Sign in to [SteamGifts](https://www.steamgifts.com)
2. Open your browser's developer tools (F12)
3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
4. Find **Cookies** → `www.steamgifts.com`
5. Copy the `PHPSESSID` value
6. Paste it in the account credentials section on the Accounts page

## Architecture

```
SteamSelfGifter/
├── package.json          # Root package — single source of truth for version number
├── backend/              # FastAPI REST API + SQLite
│   ├── src/
│   │   ├── api/          # REST API endpoints
│   │   ├── core/         # Configuration, logging, exceptions
│   │   ├── db/           # Database session management
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── repositories/ # Data access layer
│   │   ├── services/     # Business logic
│   │   ├── utils/        # SteamGifts/Steam API clients
│   │   └── workers/      # Background job scheduler
│   └── tests/            # Test suite (pytest)
├── frontend/             # React + TypeScript + Vite + TailwindCSS
│   └── src/
│       ├── components/   # Reusable UI components
│       ├── hooks/        # React Query hooks
│       ├── pages/        # Page components
│       └── services/     # API client
├── docs/                 # Documentation
├── Dockerfile            # Multi-stage single-container build
├── docker-compose.yml        # External deployment (pulls from ghcr.io)
└── docker-compose.dev.yml    # Local development (builds from source)
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

When running via Docker, the API is available at:
- http://localhost:8080/api/v1/

## Development

### Running Tests

```bash
# Backend tests
cd backend
pip install -e ".[test]"
pytest

# Frontend build/lint
cd frontend
npm run lint
npm run build
```

### Database Migrations

The project uses Alembic for database migrations. Migrations run automatically on startup.

```bash
# Create a new migration after model changes
cd backend/src
alembic revision --autogenerate -m "description"

# Apply migrations manually
alembic upgrade head
```

## Changelog

### v3.0.0

All changes in this release were made in collaboration with [Claude](https://claude.ai) (Anthropic).

#### Multi-account support

- Added full multi-account management: create, rename, delete, and switch between accounts
- Account switcher in the sidebar with automation status indicator
- Accounts page with expandable rows for credentials, settings, and per-account scheduler controls
- Default account promotion when the current default is deleted

#### Per-account settings

- All settings (DLC, Safety Detection, Auto-Join Rules, Scheduler interval, Rate Limiting) are now configurable per account
- Removed the global Settings page from the navigation; all configuration lives on the Accounts page
- New accounts are created with sensible defaults

#### Security

- Session cookies (PHPSESSID) are no longer exposed in list API responses; replaced with a `has_credentials` boolean flag
- `set_default` account operation is now atomic (two SQL `UPDATE` statements) to prevent race conditions

#### Automation

- Scheduler jobs are automatically cleaned up when an account is deleted
- Per-account scheduler endpoints: start, stop, run cycle, scan, process, sync wins

#### Frontend improvements

- Optimistic cache updates: all account mutations update the UI immediately without a full refetch
- Version number (`v3.0.0`) shown at the bottom of the sidebar, sourced from the root `package.json`

#### Version management

- Single version number (`3.0.0`) shared between backend (`pyproject.toml`) and frontend (root `package.json` read via Vite `define`)

#### Docker

- Backend process now runs as a non-root `appuser` inside the container
- Added `stopwaitsecs=30` to supervisord for graceful shutdown of in-flight requests
- Stage 3 copies backend source from the build stage instead of re-sending from the build context

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is for educational purposes only. Please ensure you comply with SteamGifts' terms of service and use this tool responsibly.
