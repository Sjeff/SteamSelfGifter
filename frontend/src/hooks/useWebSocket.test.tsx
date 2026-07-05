import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { useWebSocketQueryInvalidation } from "./useWebSocket";
import { websocketService } from "@/services/websocket";
import { analyticsKeys } from "./useAnalytics";
import type { WebSocketEvent } from "@/types";

// Mock the WebSocket service so we can trigger events directly without a
// real socket connection.
vi.mock("@/services/websocket", () => ({
  websocketService: {
    on: vi.fn(),
  },
}));

const mockOn = vi.mocked(websocketService.on);

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

/** Grab the handler registered for a given event type via websocketService.on. */
function getHandler(eventType: string) {
  const call = mockOn.mock.calls.find(([type]) => type === eventType);
  if (!call) throw new Error(`No handler registered for "${eventType}"`);
  return call[1];
}

function fireEvent(eventType: string, data: unknown = {}) {
  getHandler(eventType)({
    type: eventType,
    data,
    timestamp: "",
  } as WebSocketEvent);
}

describe("useWebSocketQueryInvalidation", () => {
  beforeEach(() => {
    mockOn.mockReset();
    mockOn.mockReturnValue(() => {});
  });

  it("invalidates the real dashboard query key on stats_update", () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    renderHook(() => useWebSocketQueryInvalidation(), {
      wrapper: createWrapper(queryClient),
    });

    fireEvent("stats_update");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: analyticsKeys.dashboard,
    });
  });

  it("invalidates the real dashboard query key on scan_complete", () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    renderHook(() => useWebSocketQueryInvalidation(), {
      wrapper: createWrapper(queryClient),
    });

    fireEvent("scan_complete");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: analyticsKeys.dashboard,
    });
  });

  it("invalidates the real dashboard query key on entry_success", () => {
    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    renderHook(() => useWebSocketQueryInvalidation(), {
      wrapper: createWrapper(queryClient),
    });

    fireEvent("entry_success");

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: analyticsKeys.dashboard,
    });
  });
});
