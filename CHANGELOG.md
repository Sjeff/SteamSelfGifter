# Changelog

All notable changes to this project will be documented in this file.

All changes were made in collaboration with [Claude](https://claude.ai) (Anthropic).

## [Unreleased]

## [3.2.0]

### Added

- New "Prioritize Wishlist" setting (on by default): wishlist giveaways are now entered before the general autojoin pool and bypass the price/review-score/review-count/game-age filters (they still respect active/hidden/entered status and the points budget below).
- DLC-priority autojoin: giveaways are now tagged as DLC when discovered, get their own "DLC" tab (and `GET /api/v1/giveaways/dlc` endpoint) on the Giveaways page, and — like wishlist giveaways — bypass the price/review-score/review-count/game-age filters when "Include DLC" is enabled in Settings. Entries made this way are recorded as `entry_type="dlc"`.
- Chance-to-win and time-remaining browse filters on the Active/Wishlist/DLC giveaway tabs ("Min Chance" and "Ending in" sliders), plus a win-chance badge and entry count on every giveaway card. Giveaways page filters (tab, score, safety, chance, time) now persist across visits via `localStorage`.
- Analytics page now leads with per-day trend charts (entries succeeded/failed, points spent, wins), backed by a new `GET /analytics/entries/trends` endpoint. Chart colors are CVD-validated CSS custom properties matched to the light/dark app surfaces; the data is also available as a collapsible table.
- A Playwright e2e suite (`npm run test:e2e`) covering the dashboard, accounts, giveaways, navigation, and analytics pages against a mocked API — no backend required to run it.
- The published Docker image now has a `nightly` tag (rebuilt daily, and on every `master` push) so it keeps picking up base-image security patches even between releases; `latest` now only ever points at the last tagged release, never an arbitrary `master` build.

- The SteamGifts connection status ("Connected as X" / invalid / not configured) moved from a Dashboard-only banner into a persistent header icon, visible on every page and scoped to the currently selected account. The Dashboard keeps its actionable banners for the not-configured and invalid-session cases (with a link to the Accounts page), since those need a call to action; the "all good" case is now just the header icon.

### Changed

- The Docker build now removes the backend package from its own virtualenv after installing dependencies, so `/app/src` is the single copy of the code running in the container (the installed copy in site-packages was dead weight that could shadow-fight with it).

### Fixed

- The entry count on a giveaway never actually got stored: the scraper parsed it but the sync step silently dropped it, and separately the parser was looking for a `<span class="giveaway__links">` element that SteamGifts had long since changed to a `<div>`, so every giveaway showed 0 entries. Both are fixed, entry counts (and the win-chance% they drive) now reflect the last scan; the parser also now handles thousands separators ("1,234 entries") and the singular "1 entry".
- The wishlist scanner no longer picks up the "Featured" ad giveaways SteamGifts pins at the top of the wishlist page — it was matching the old `pinned-giveaways__inner-wrap` container class, which SteamGifts has since renamed to `pinned-giveaways`.
- History and Analytics no longer blank the page with an unhandled error when the API returns a partial/unexpected payload (missing entries, missing `by_type` or `win_rate`) — both now degrade gracefully instead.
- Auto-join now tracks the points budget across a whole entry cycle instead of only checking the balance once at the start: entering a giveaway that would drop the balance below the configured stop threshold is skipped (a cheaper giveaway later in the queue still gets a chance) rather than potentially overspending.
- Reduced the risk of the scraper tripping SteamGifts' rate limiting during scan/entry cycles: all `SteamGiftsClient` requests now go through a minimum delay between requests and retry with exponential backoff on 429/5xx responses or transient network errors.

## [3.1.1]

### Security

- Added an explicit `permissions: contents: read` block to `.github/workflows/test.yml` (CodeQL: "Workflow does not contain permissions") — without it, the `GITHUB_TOKEN` for both jobs defaults to broader repository permissions than either job (checkout, test, build) actually needs

### Fixed

- The shipped `docker-compose.yml`/`docker-compose.dev.yml` never set `SESSION_COOKIE_SECURE`, so it defaulted to `true`. Over the plain HTTP these compose files serve by default, the browser silently discarded the `Secure`-flagged login cookie — login/setup looked successful, but every following request was unauthenticated and refreshing the page always dropped back to the login screen. Both compose files now default to `SESSION_COOKIE_SECURE=false`.
- `3.1.0`'s login requirement accidentally put `/api/v1/system/health` behind auth and dropped `curl` from the image, breaking any pre-existing custom healthcheck (e.g. for Traefik/Swarm/Kubernetes health-aware routing) that pinged it with `curl`. The container would never report healthy, and a health-aware reverse proxy would silently stop routing to it. `/api/v1/system/health` is unauthenticated again and `curl` is back in the image — no changes needed to existing healthcheck overrides.
- Added a warning log when a `Secure` session cookie is issued over a plain-HTTP request, so a misconfigured `SESSION_COOKIE_SECURE` is visible in the container logs instead of failing silently.
- A failed giveaway entry (e.g. a database lock) left the automation cycle's session in an unusable state without rolling back, silently failing every remaining giveaway in that same cycle.
- The dashboard didn't live-update on scans or entries — a query-key mismatch meant WebSocket-triggered cache invalidation never matched the dashboard's actual query, so it only refreshed via its 30-second poll.

## [3.1.0]

### ⚠ Action Required

- On first launch after upgrading, you'll be asked to create an admin username and password before the dashboard becomes accessible. This is a one-time setup — every request after that requires logging in.
- If you run this app over plain HTTP without a TLS reverse proxy in front of it (e.g. LAN-only), set `SESSION_COOKIE_SECURE=false` in your environment, otherwise the login cookie won't be accepted by the browser and you won't be able to log in.

### Security

- Added a login gate: a single admin account (created via an in-app setup wizard) is now required to use the dashboard or its API. Sessions are server-side (stored in the database, survive a restart), identified by a random token — only its hash is persisted, never the raw value
- Login lockout after 5 failed attempts (15 minutes)
- Every API router and the `/ws/events` WebSocket now require a valid session, not just the frontend
- Updated frontend dependencies (react-router, vite, vitest, postcss, and transitive packages) to resolve all `npm audit` findings — 14 vulnerabilities down to 0
- Bumped all GitHub Actions (checkout, setup-python, setup-node, docker/*) to their latest major versions

### Added

- Setup wizard and login page; "Change password" and "Log out" controls on the Settings page

### Performance

- Docker image shrunk from 419MB to 371MB: added a missing `.dockerignore` (was letting the build accidentally copy `frontend/node_modules` from the host into the image), dropped `curl` in favor of a Python-based healthcheck, and dropped uvicorn's unused `[standard]` extra (uvloop/httptools/watchfiles aren't needed since the container never runs with `--reload`)

### Removed

- Deleted `backend/src/db/migrations/`, an orphaned duplicate of `backend/src/alembic/` left over from before the project moved its migrations there — nothing imported it, and its revision history had already diverged from the real one
- Deleted `backend/src/db/seeds/` (an empty, unreferenced package) and `NotificationService.get_logs_count()` (unused method)
- Deleted unused frontend hooks (`useGames`, `useSystem`, `useEntry`, `useHistory`, `useGiveaway`, `useRefreshGiveawayGame`, `useEntryTrends`, `useWebSocketAnyEvent`) and their now-unused types (`SystemInfo`, `HealthCheck`, `TrendDataPoint`, `GameFilters`) — none were wired into any page
- Removed the unused `date-fns` dependency from `frontend/package.json`

### Fixed

- The Docker healthcheck and container `HEALTHCHECK` pinged `/api/v1/system/health`, which is now behind login — added an unauthenticated `/health` route so the container correctly reports "healthy" again
- `vitest.config.ts` was missing the `__APP_VERSION__` define that `vite.config.ts` already had, crashing any test that rendered the sidebar
- The sidebar was missing a link to the Settings page (the route existed but was only reachable by typing the URL directly)

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
