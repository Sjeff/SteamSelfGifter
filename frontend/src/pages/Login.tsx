import { useState, type FormEvent } from "react";
import { LogIn, UserPlus } from "lucide-react";
import { Card, Button, Input } from "@/components/common";
import { useSetup, useLogin } from "@/hooks";

interface LoginProps {
  setupComplete: boolean;
}

/**
 * Shown instead of the routed app until a valid session exists.
 * Doubles as the one-time setup wizard when no admin account exists yet.
 */
export function Login({ setupComplete }: LoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const setup = useSetup();
  const login = useLogin();

  const mutation = setupComplete ? login : setup;
  const error = mutation.error instanceof Error ? mutation.error.message : null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate({ username, password });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
          SteamSelfGifter
        </h1>
        <Card title={setupComplete ? "Log in" : "Create admin account"}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              autoComplete={setupComplete ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={setupComplete ? undefined : 8}
              helperText={setupComplete ? undefined : "At least 8 characters"}
              error={error ?? undefined}
            />
            <Button
              type="submit"
              fullWidth
              isLoading={mutation.isPending}
              icon={setupComplete ? LogIn : UserPlus}
            >
              {setupComplete ? "Log in" : "Create account"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
