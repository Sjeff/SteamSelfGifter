# Changelog

All notable changes to this project will be documented in this file.

All changes were made in collaboration with [Claude](https://claude.ai) (Anthropic).

## [3.0.5]

### Fixed

- `PendingRollbackError` in the safety checker when the SQLite database is locked — added `session.rollback()` in the except block before re-using the session, preventing the fallback commit from also failing
- `TypeError: can't compare offset-naive and offset-aware datetimes` when entering a giveaway — `update_win_check_for_new_entry` now compares both datetimes as timezone-aware, consistent with the `TZDateTime` fix introduced in v3.0.4

## [3.0.4]

### Fixed

- Automation cycle crash when the Steam API returns no review data for a game — review fields (`review_score`, `total_positive`, `total_negative`, `total_reviews`) now fall back to `0` instead of `None` to satisfy the database `NOT NULL` constraint

### Changed

- Replaced all uses of the deprecated `datetime.utcnow()` (52 call sites across 21 files + 19 test files) with `datetime.now(timezone.utc)` — required for Python 3.12+ compatibility
- Added `TZDateTime` SQLAlchemy TypeDecorator to re-attach `timezone.utc` when reading datetimes from SQLite, preventing naive/aware comparison errors
- Fixed CI workflow running 4 jobs per PR instead of 2 — push trigger now limited to `master`

## [3.0.3]

### Fixed

- "Failed to load wins" error on accounts with an expired SteamGifts session — read-only endpoints (Wins, Giveaways) now work regardless of session state; only live SteamGifts operations (entering, scanning) require a valid session
- Corrected misleading label "Min Game Price ($)" → "Min Giveaway Cost (points)" on the Accounts page to reflect that the value is in SteamGifts points, not dollars

### Changed

- Added Dependabot configuration for weekly automated dependency updates across npm (frontend), pip (backend), Docker base images, and GitHub Actions

## [3.0.1]

### Fixed

- Fixed play button on the Accounts page not reflecting automation status correctly on the Dashboard
- Dashboard scheduler status now shows the global scheduler state instead of the selected account's state, so starting automation from the Accounts page is immediately visible on the Dashboard
- Fixed 6 failing unit tests in `test_api_routers_system` after refactoring the logs endpoint to use a direct `NotificationService` instance instead of dependency injection

### Changed

- Logs page now shows entries from all accounts in a single combined view — no longer filtered by the selected account; each log entry displays an account badge
- Accounts no longer scan simultaneously: each additional account receives a 5-minute start offset (account 1 at T+0, account 2 at T+5 min, account 3 at T+10 min, etc.)
- The same staggering is applied automatically on startup for accounts that had automation enabled
- Added a 1-second delay between page requests within a single scan to avoid burst traffic

## [3.0.0]

### Added

- Full multi-account management: create, rename, delete, and switch between accounts
- Account switcher in the sidebar with automation status indicator
- Accounts page with expandable rows for credentials, settings, and per-account scheduler controls
- All settings (DLC, Safety Detection, Auto-Join Rules, Scheduler interval, Rate Limiting) configurable per account
- Per-account scheduler endpoints: start, stop, run cycle, scan, process, sync wins
- Version number (`v3.0.0`) shown at the bottom of the sidebar, sourced from the root `package.json`
- GitHub Actions workflow for automated Docker image publishing to `ghcr.io`

### Changed

- Removed the global Settings page from the navigation; all configuration lives on the Accounts page
- New accounts are created with sensible defaults
- Session cookies (PHPSESSID) are no longer exposed in list API responses; replaced with a `has_credentials` boolean flag
- `set_default` account operation is now atomic to prevent race conditions
- Scheduler jobs are automatically cleaned up when an account is deleted
- Optimistic cache updates: all account mutations update the UI immediately without a full refetch
- Single version number shared between backend (`pyproject.toml`) and frontend (root `package.json` read via Vite `define`)
- Backend process now runs as a non-root `appuser` inside the container
- Added `stopwaitsecs=30` to supervisord for graceful shutdown of in-flight requests
- `docker-compose.yml` is now for external deployments (pulls from `ghcr.io/sjeff/steamselfgifter:latest`)
- `docker-compose.dev.yml` is for local development (builds from source)
- Docker images tagged with `latest` on push to `master`, and semver tags on git tags

### Fixed

- "Session Not Configured" banner now links to the Accounts page instead of the removed Settings page
- Default account credentials section auto-expands when navigating from the setup banner
