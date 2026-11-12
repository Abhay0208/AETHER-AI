import { useEffect, useState } from "react";
import { Plus, RefreshCw, Play, Database } from "lucide-react";
import { api } from "../lib/api";

export function Models() {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [regProvider, setRegProvider] = useState("");
  const [regModel, setRegModel] = useState("");
  const [regDisplay, setRegDisplay] = useState("");
  const [regCaps, setRegCaps] = useState('["chat"]');
  const [regCtx, setRegCtx] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const r = await api.get("/models");
      setModels(r.data.models ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load models");
    }
  }

  async function register() {
    setLoading(true);
    setError("");
    try {
      await api.post("/models/register", {
        provider_id: Number(regProvider),
        model_id: regModel,
        display_name: regDisplay || undefined,
        capabilities: regCaps,
        context_window: regCtx ? Number(regCtx) : undefined,
        supports_tools: false,
        supports_vision: false,
        supports_streaming: true,
      });
      setRegModel("");
      setRegDisplay("");
      setRegCtx("");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Register failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <Database className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Model Registry</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Register and manage models available to AETHER.</p>
          </div>
        </div>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="panel p-4">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Total models</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{models.length}</div>
          </div>
          <div className="panel p-4">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">With tools</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {models.filter((m) => m.supports_tools).length}
            </div>
          </div>
          <div className="panel p-4">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">With vision</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {models.filter((m) => m.supports_vision).length}
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-4 mb-4">
          <button
            onClick={load}
            className="btn-outline flex-1 md:flex-none"
            disabled={loading}
          >
            <RefreshCw size={16} className="mr-2" /> Refresh
          </button>
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400 mb-4">
            {error}
          </div>
        )}

        <div className="panel p-4 mb-6">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Register a custom model</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="col-span-1 sm:col-span-2 lg:col-span-2">
              <label className="label">Provider ID</label>
              <input className="input" value={regProvider} onChange={(e) => setRegProvider(e.target.value)} placeholder="e.g. ollama" />
            </div>
            <div>
              <label className="label">Model ID</label>
              <input className="input" value={regModel} onChange={(e) => setRegModel(e.target.value)} placeholder="e.g. llama3.1" />
            </div>
            <div>
              <label className="label">Display name</label>
              <input className="input" value={regDisplay} onChange={(e) => setRegDisplay(e.target.value)} placeholder="optional" />
            </div>
            <div className="sm:col-span-2 lg:col-span-2">
              <label className="label">Capabilities (JSON)</label>
              <input className="input" value={regCaps} onChange={(e) => setRegCaps(e.target.value)} placeholder='["chat","tools"]' />
            </div>
            <div>
              <label className="label">Context window</label>
              <input className="input" type="number" value={regCtx} onChange={(e) => setRegCtx(e.target.value)} placeholder="optional" />
            </div>
            <div className="col-span-full">
              <button onClick={register} className="btn" disabled={loading || !regProvider || !regModel}>
                {loading ? "Registering…" : <><Play size={16} className="mr-2" /> Register model</>}
              </button>
            </div>
          </div>
        </div>

        <div className="panel">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Model</th>
                <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Provider</th>
                <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Capabilities</th>
                <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Context</th>
                <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30">
                  <td className="py-3 text-sm font-medium text-slate-900 dark:text-slate-100">{m.display_name || m.model_id}</td>
                  <td className="py-3 text-sm text-slate-600 dark:text-slate-400">{m.provider}</td>
                  <td className="py-3 text-xs text-slate-500 dark:text-slate-500">
                    <span className="inline-flex items-center gap-1">
                      {JSON.parse(m.capabilities || "[]").map((c: string, i: number) => (
                        <span key={i} className="rounded bg-slate-200 dark:bg-slate-700 px-2 py-0.5 text-[10px] font-medium text-slate-700 dark:text-slate-300">
                          {c}
                        </span>
                      ))}
                    </span>
                  </td>
                  <td className="py-3 text-sm text-slate-600 dark:text-slate-400">{m.context_window ?? "—"}</td>
                  <td className="py-3 text-sm">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      m.is_enabled ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400" : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                    }`}>
                      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50" />
                      {m.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                </tr>
              ))}
              {models.length === 0 && (
                <tr><td colSpan={5} className="py-8 text-center text-slate-400">No models registered yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
