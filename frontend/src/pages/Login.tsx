import { useState } from "react";
import { Mail, Lock, AlertTriangle, ArrowRight } from "lucide-react";
import { login } from "../lib/auth";

export function Login({ onLogin }: { onLogin: (user: any) => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const data = await login(username, password);
      onLogin(data.user);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed. Try admin / admin.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center pt-20 sm:pt-0">
      <div className="max-w-md w-full space-y-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-14 w-14 rounded-2xl bg-aether-600 flex items-center justify-center shadow-lg shadow-aether-500/30">
            <ArrowRight className="text-white" size={30} />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome to AETHER</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Sign in to your local AETHER platform.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
              <Mail className="h-4 w-4" />
              Username
            </div>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
              <Lock className="h-4 w-4" />
              Password
            </div>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="btn w-full"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
          Default local account: <code className="font-mono text-slate-600 dark:text-slate-400">admin</code> / <code className="font-mono text-slate-600 dark:text-slate-400">admin</code>
        </p>
      </div>
    </div>
  );
}
