import type { Page, Route } from "@playwright/test";

function mockTrends(days: number) {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(NOW - (days - 1 - i) * 86_400_000)
      .toISOString()
      .slice(0, 10);
    return {
      date,
      entries: 5 + i,
      successful: 4 + i,
      failed: 1,
      points_spent: (4 + i) * 25,
      wins: i === days - 1 ? 1 : 0,
    };
  });
}

/** Envelope every backend response uses. */
function ok(data: unknown) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ success: true, data }),
  };
}

/**
 * Match a scheduler action path in either its flat form
 * (/api/v1/scheduler/<action>) or its per-account form
 * (/api/v1/accounts/<id>/scheduler/<action>). AccountSwitcher auto-selects
 * the default account on load, which switches every scheduler call in the
 * app from the flat path to the per-account one.
 */
function schedulerPath(action: string): RegExp {
  return new RegExp(`^/api/v1/(scheduler|accounts/\\d+/scheduler)/${action}$`);
}

const NOW = Date.now();
const inHours = (h: number) => new Date(NOW + h * 3_600_000).toISOString();

export const mockAuthStatus = { setup_complete: true };
export const mockAuthUser = { id: 1, username: "e2e-user" };

export const mockAccountListItem = {
  id: 1,
  name: "Main",
  is_active: true,
  is_default: true,
  automation_enabled: true,
  autojoin_enabled: true,
  has_credentials: true,
};

export const mockAccount = {
  id: 1,
  name: "Main",
  is_active: true,
  is_default: true,
  phpsessid: "e2e-session-cookie",
  user_agent: "SteamSelfGifter/3.0",
  xsrf_token: null,
  dlc_enabled: false,
  safety_check_enabled: true,
  auto_hide_unsafe: true,
  autojoin_enabled: true,
  autojoin_start_at: 300,
  autojoin_stop_at: 50,
  autojoin_min_price: 10,
  autojoin_min_score: 7,
  autojoin_min_reviews: 1000,
  autojoin_max_game_age: null,
  wishlist_priority: true,
  scan_interval_minutes: 30,
  max_entries_per_cycle: 10,
  automation_enabled: true,
  max_scan_pages: 3,
  entry_delay_min: 5,
  entry_delay_max: 15,
  last_synced_at: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

export const mockSettings = {
  id: 1,
  phpsessid: "e2e-session-cookie",
  user_agent: "SteamSelfGifter/3.0",
  xsrf_token: null,
  dlc_enabled: false,
  safety_check_enabled: true,
  auto_hide_unsafe: true,
  autojoin_enabled: true,
  autojoin_start_at: 300,
  autojoin_stop_at: 50,
  autojoin_min_price: 10,
  autojoin_min_score: 7,
  autojoin_min_reviews: 1000,
  autojoin_max_game_age: null,
  wishlist_priority: true,
  scan_interval_minutes: 30,
  max_entries_per_cycle: 10,
  automation_enabled: true,
  max_scan_pages: 3,
  entry_delay_min: 5,
  entry_delay_max: 15,
  last_synced_at: null,
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

export const mockDashboard = {
  session: {
    configured: true,
    valid: true,
    username: "e2e-user",
    error: null,
  },
  points: { current: 342 },
  entries: {
    total: 120,
    today: 4,
    entered_30d: 60,
    wins_30d: 3,
    win_rate: 5.0,
  },
  giveaways: { active: 57, entered: 12, wins: 9 },
  safety: { checked: 40, safe: 38, unsafe: 2, unchecked: 17 },
  scheduler: {
    running: true,
    paused: false,
    last_scan: inHours(-1),
    next_scan: inHours(1),
  },
};

export const mockSchedulerStatus = {
  running: true,
  paused: false,
  job_count: 1,
  jobs: [
    {
      id: "automation_cycle",
      name: "scan_giveaways",
      next_run: inHours(1),
      pending: false,
    },
  ],
};

function giveaway(id: number, over: Record<string, unknown> = {}) {
  return {
    id,
    code: `Code${id}`,
    url: `https://www.steamgifts.com/giveaway/Code${id}/`,
    game_name: `Test Game ${id}`,
    game_id: 400 + id,
    price: 25 + id,
    copies: 1,
    entries: 100,
    win_chance: 1.0,
    end_time: inHours(24 + id),
    discovered_at: inHours(-2),
    entered_at: null,
    is_hidden: false,
    is_entered: false,
    is_wishlist: false,
    is_dlc: false,
    is_won: false,
    won_at: null,
    is_safe: true,
    safety_score: 95,
    created_at: inHours(-2),
    updated_at: inHours(-2),
    game_thumbnail: null,
    game_review_score: 9,
    game_total_reviews: 12000,
    game_review_summary: "Very Positive",
    ...over,
  };
}

export const mockGiveaways = [
  giveaway(1, { game_name: "Portal Reloaded" }),
  giveaway(2, { game_name: "Half-Life 3", is_wishlist: true }),
  giveaway(3, {
    game_name: "Stardew Galaxy",
    is_entered: true,
    entered_at: inHours(-1),
  }),
];

export interface ApiCall {
  method: string;
  url: string;
  postData: string | null;
}

/**
 * Install route mocks for every /api/v1 endpoint the app touches (including
 * the login-gate auth checks) and swallow the WebSocket connection. Returns
 * a log of API calls for assertions.
 */
export async function mockApi(page: Page): Promise<ApiCall[]> {
  const calls: ApiCall[] = [];

  // The app connects to /ws/events on load; accept and stay silent.
  await page.routeWebSocket("**/ws/events", () => {
    /* no server messages */
  });

  await page.route("**/api/v1/**", async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();
    calls.push({ method, url: path + url.search, postData: req.postData() });

    // --- Auth (login gate) ---
    if (path === "/api/v1/auth/status") {
      return route.fulfill(ok(mockAuthStatus));
    }
    if (path === "/api/v1/auth/me") {
      return route.fulfill(ok(mockAuthUser));
    }

    // --- Accounts ---
    if (path === "/api/v1/accounts" && method === "GET") {
      return route.fulfill(ok([mockAccountListItem]));
    }
    if (/^\/api\/v1\/accounts\/\d+$/.test(path) && method === "GET") {
      return route.fulfill(ok(mockAccount));
    }
    if (/^\/api\/v1\/accounts\/\d+\/credentials$/.test(path)) {
      return route.fulfill(
        ok({
          ...mockAccount,
          phpsessid: "new-session-cookie",
          has_credentials: true,
        }),
      );
    }
    if (/^\/api\/v1\/accounts\/\d+\/test-session$/.test(path)) {
      return route.fulfill(
        ok({ valid: true, username: "e2e-user", points: 342, error: null }),
      );
    }

    // --- Settings (global defaults) ---
    if (path === "/api/v1/settings" && method === "GET") {
      return route.fulfill(ok(mockSettings));
    }
    if (path === "/api/v1/settings" && method === "PUT") {
      const body = JSON.parse(req.postData() ?? "{}");
      return route.fulfill(
        ok({
          ...mockSettings,
          ...body,
          updated_at: new Date(NOW).toISOString(),
        }),
      );
    }
    if (path === "/api/v1/settings/test-session") {
      return route.fulfill(
        ok({ valid: true, username: "e2e-user", points: 342, error: null }),
      );
    }

    // --- Analytics / dashboard ---
    if (path === "/api/v1/analytics/dashboard") {
      return route.fulfill(ok(mockDashboard));
    }

    // --- Scheduler (flat or per-account path, see schedulerPath()) ---
    if (schedulerPath("status").test(path)) {
      return route.fulfill(ok(mockSchedulerStatus));
    }
    if (schedulerPath("stop").test(path)) {
      return route.fulfill(
        ok({ ...mockSchedulerStatus, running: false, jobs: [] }),
      );
    }
    if (schedulerPath("start").test(path)) {
      return route.fulfill(ok(mockSchedulerStatus));
    }
    if (schedulerPath("pause").test(path)) {
      return route.fulfill(ok({ ...mockSchedulerStatus, paused: true }));
    }
    if (schedulerPath("resume").test(path)) {
      return route.fulfill(ok(mockSchedulerStatus));
    }
    if (
      schedulerPath("scan").test(path) ||
      schedulerPath("process").test(path) ||
      schedulerPath("sync-wins").test(path) ||
      schedulerPath("run").test(path)
    ) {
      return route.fulfill(ok({ triggered: true }));
    }

    // --- Giveaways ---
    if (/^\/api\/v1\/giveaways\/[^/]+\/enter$/.test(path)) {
      return route.fulfill(
        ok({ success: true, points_spent: 26, error: null }),
      );
    }
    if (path.startsWith("/api/v1/giveaways")) {
      const search = url.searchParams.get("search")?.toLowerCase();
      const filtered = search
        ? mockGiveaways.filter((g) =>
            g.game_name.toLowerCase().includes(search),
          )
        : mockGiveaways;
      return route.fulfill(ok({ giveaways: filtered, count: filtered.length }));
    }

    // --- Entries (History page) ---
    if (path.startsWith("/api/v1/entries")) {
      return route.fulfill(ok({ entries: [], count: 0 }));
    }

    // --- Analytics summaries (Analytics page) ---
    if (path === "/api/v1/analytics/entries/summary") {
      return route.fulfill(
        ok({
          total_entries: 120,
          successful_entries: 117,
          failed_entries: 3,
          total_points_spent: 2900,
          average_points_per_entry: 24.8,
          success_rate: 97.5,
          by_type: { auto: 100, manual: 15, wishlist: 5 },
        }),
      );
    }
    if (path === "/api/v1/analytics/giveaways/summary") {
      return route.fulfill(
        ok({
          total_giveaways: 300,
          active_giveaways: 57,
          entered_giveaways: 12,
          hidden_giveaways: 4,
          expiring_24h: 6,
          wins: 9,
          win_rate: 5.0,
        }),
      );
    }
    if (path === "/api/v1/analytics/games/summary") {
      return route.fulfill(
        ok({
          total_games: 200,
          games: 180,
          dlc: 15,
          bundles: 5,
          stale_games: 3,
        }),
      );
    }
    if (path.startsWith("/api/v1/analytics/entries/trends")) {
      const period = url.searchParams.get("period") ?? "month";
      const days = { week: 7, month: 30, year: 365 }[period] ?? 30;
      return route.fulfill(ok({ period, trends: mockTrends(days) }));
    }

    // --- System logs (Logs page) ---
    if (path.startsWith("/api/v1/system/logs")) {
      return route.fulfill(ok({ logs: [], count: 0 }));
    }

    // --- Fallback: empty success so unmodelled endpoints don't hang ---
    return route.fulfill(ok({}));
  });

  return calls;
}
