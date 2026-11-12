import { useEffect, useState } from "react";
import { Activity, Monitor, Database, LockKeyhole, Server } from "lucide-react";
import { api } from "../lib/api";

export function Dashboard({ user, onLogout }: { user: any; onLogout: () => void }) {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/health")
      .then((r) => setHealth(r.data))
      .catch(() => setHealth({ error: "Backend unreachable" }))
      .finally(() => setLoading(false));
  }, []);

  const stat = (label: string, value: string, icon: React.ElementType) => {
    const Comp = icon;
    return (
      <div className="panel p-4">
        <div className="flex items-center gap-2 mb-2">
          <Comp className="h-5 w-5 text-aether-600 dark:text-aether-400" />
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
        </div>
        <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
      </div>
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400">
            AETHER is running locally. Connect providers to start using AI models.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn">Connect Provider</button>
          <button className="btn-outline">Generate API Key</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stat("Server", health?.ok ? "Online" : "Offline", Monitor)}
        {stat("Database", health?.database === "ok" ? "Connected" : "Error", Database)}
        {stat("Port", String(health?.port ?? 5467), Server)}
        {stat("Mode", "Local-first", LockKeyhole)}
        {stat("Activity", "Idle", Activity)}
      </div>

      <div className="panel p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Quick start</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="panel p-4 border-l-4 border-aether-600">
            <h4 className="font-semibold text-slate-900 dark:text-white mb-2">1. Add an API key</h4>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
              Go to API Keys and add a key from OpenAI, Anthropic, Groq, Ollama, or another provider.
            </p>
            <button className="btn-outline text-sm">Open API Keys</button>
          </div>
          <div className="panel p-4 border-l-4 border-slate-400 dark:border-slate-600">
            <h4 className="font-semibold text-slate-900 dark:text-white mb-2">2. Start chatting</h4>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
              Select a model and send your first message in Chat.
            </p>
            <button className="btn-outline text-sm">Open Chat</button>
          </div>
        </div>
      </div>

      <div className="panel p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Status</h3>
        <pre className="text-sm text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-900 p-4 rounded overflow-x-auto">
          {JSON.stringify(health ?? { loading }, null, 2)}
        </pre>
      </div>
    </div>
  );
}
