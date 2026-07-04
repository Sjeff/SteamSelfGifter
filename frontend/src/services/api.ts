import { config } from "@/config/env";
import type { ApiResponse } from "@/types";

/**
 * API Client for backend communication
 *
 * Handles all HTTP requests to the backend API.
 * Uses the Vite proxy in development to avoid CORS issues.
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make an HTTP request to the API
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      // Parse JSON response
      const data = await response.json();

      // Successful responses are { success, data, meta }. But responses
      // produced by the backend's global exception handlers
      // (api/middleware.py) are shaped { error: { message, code, details } }
      // with no success/data keys at all. Normalize both into the same
      // { success, data, error } shape so callers can always rely on
      // `error` being a string, not an object (passing an object into
      // `new Error(...)` stringifies it to "[object Object]").
      if (
        data &&
        typeof data === "object" &&
        !("success" in data) &&
        "error" in data
      ) {
        const backendError = (data as { error?: { message?: string } }).error;
        return {
          success: false,
          data: null as T,
          error: backendError?.message || "An unexpected error occurred",
        };
      }

      return data as ApiResponse<T>;
    } catch (error) {
      // Network error or invalid JSON
      return {
        success: false,
        data: null as T,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }
}

// Export singleton instance
export const api = new ApiClient(config.apiUrl);
