import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@/test/utils";
import { Login } from "./Login";
import { api } from "@/services/api";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApi = vi.mocked(api);

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a setup form when setup is not complete", () => {
    render(<Login setupComplete={false} />);

    expect(screen.getByText("Create admin account")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i }),
    ).toBeInTheDocument();
  });

  it("shows a login form when setup is complete", () => {
    render(<Login setupComplete={true} />);

    expect(
      screen.getByRole("button", { name: /^log in$/i }),
    ).toBeInTheDocument();
  });

  it("submits setup credentials", async () => {
    mockApi.post.mockResolvedValueOnce({
      success: true,
      data: { id: 1, username: "admin" },
    });

    render(<Login setupComplete={false} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith("/api/v1/auth/setup", {
        username: "admin",
        password: "password1234",
      });
    });
  });

  it("shows an error message when login fails", async () => {
    mockApi.post.mockResolvedValueOnce({
      success: false,
      data: null,
      error: "AUTH_002",
    });

    render(<Login setupComplete={true} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^log in$/i }));

    expect(
      await screen.findByText("Invalid username or password"),
    ).toBeInTheDocument();
  });
});
