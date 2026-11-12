import { useEffect, useState } from "react";
import { Plus, RefreshCw, ShieldCheck, Eye, EyeOff, PlusCircle, Trash2, ToggleRight, ToggleLeft, AlertCircle } from "lucide-react";
import { api } from "../lib/api";

export function APIKeys() {
  const [data, setData] = useState({ providers: [] as any[], api_keys: [] as any[] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [addProviderName, setAddProviderName] = useState("");
  const [addProviderDisplay, setAddProviderDisplay] = useState("");

  const [keyProvider, setKeyProvider] = useState("");
  const [keyName, setKeyName] = useState("");
  const [keyValue, setKeyValue] = useState("");
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const r = await api.get("/providers");
      setData(r.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load providers");
    }
  }

  async function addProvider() {
    if (!addProviderName.trim()) return;
    setLoading(true);
    try {
      await api.post("/providers", {
        name: addProviderName,
        display_name: addProviderDisplay || addProviderName,
        capabilities: '["chat"]',
      });
      setAddProviderName("");
      setAddProviderDisplay("");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Add provider failed");
    } finally {
      setLoading(false);
    }
  }

  async function addKey() {
    if (!keyProvider || !keyName || !keyValue) return;
    setLoading(true);
    try {
      await api.post("/providers/keys", {
        provider_id: Number(keyProvider),
        name: keyName,
        key: keyValue,
      });
      setKeyProvider("");
      setKeyName("");
      setKeyValue("");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Add key failed");
    } finally {
      setLoading(false);
    }
  }

  async function testKey(id: number) {
    try {
      const r = await api.post(`/providers/keys/${id}/test`);
      await load();
      return r.data.ok;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Test failed");
      await load();
      return false;
    }
  }

  async function toggleKey(id: number, enabled: boolean) {
    try {
      await api.patch(`/providers/keys/${id}`, { is_enabled: enabled });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Toggle failed");
    }
  }

  async function deleteKey(id: number) {
    if (!confirm("Delete this API key?")) return;
    try {
      await api.delete(`/providers/keys/${id}`);
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  }

  const providersById = Object.fromEntries(data.providers.map((p: any) => [p.id, p]));

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <ShieldCheck className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">API Key Manager</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Add and manage provider API keys. Keys are encrypted at rest.</p>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <div className="panel p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-slate-900 dark:text-white">Connected Providers</h4>
                <button onClick={load} className="btn-outline text-xs px-2">
                  <RefreshCw size={14} className="mr-1" /> Refresh
                </button>
              </div>
              <div className="space-y-2">
                {data.providers.map((p) => (
                  <div key={p.id} className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg flex items-center justify-center bg-aether-100 dark:bg-aether-900/20">
                        <Plus size={16} className="text-aether-600 dark:text-aether-400" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-slate-900 dark:text-white">{p.display_name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{p.name}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        p.is_configured ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400" : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                      }`}>
                        {p.is_configured ? "Configured" : "Pending key"}
                      </span>
                    </div>
                    <button className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                      <AlertCircle size={16} />
                    </button>
                  </div>
                ))}
                {data.providers.length === 0 && (
                  <div className="text-center py-6 text-slate-400 text-sm">No providers yet. Add one below.</div>
                )}
              </div>

              <div className="mt-6 panel p-4">
                <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Add a new provider</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input
                    className="input"
                    value={addProviderName}
                    onChange={(e) => setAddProviderName(e.target.value)}
                    placeholder="Provider name (e.g. openai)"
                  />
                  <input
                    className="input"
                    value={addProviderDisplay}
                    onChange={(e) => setAddProviderDisplay(e.target.value)}
                    placeholder="Display name (optional)"
                  />
                  <button
                    onClick={addProvider}
                    className="btn col-span-1 sm:col-span-2 disabled:opacity-50"
                    disabled={loading || !addProviderName.trim()}
                  >
                    {loading ? "Adding…" : <><PlusCircle size={16} className="mr-2" /> Add provider</>}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="panel p-4 sticky top-5">
              <h4 className="font-semibold text-slate-900 dark:text-white mb-4">Add API Key</h4>
              <label className="label">Provider</label>
              <select
                className="input mb-3"
                value={keyProvider}
                onChange={(e) => setKeyProvider(e.target.value)}
              >
                <option value="">Select provider</option>
                {data.providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
              <label className="label">Key name</label>
              <input
                className="input mb-3"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g. Production key"
              />
              <label className="label flex items-center gap-2">
                API key value
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="ml-2 text-slate-400 hover:text-slate-600"
                  title="Toggle visibility"
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </label>
              <input
                className="input mb-3 font-mono text-xs"
                type={showKey ? "text" : "password"}
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                placeholder="sk-…"
              />
              <button
                onClick={addKey}
                className="btn w-full disabled:opacity-50"
                disabled={loading || !keyProvider || !keyName || !keyValue}
              >
                {loading ? "Adding…" : <><PlusCircle size={16} className="mr-2" /> Add key</>}
              </button>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
            <h4 className="font-semibold text-slate-900 dark:text-white">Installed Keys</h4>
            <span className="text-xs text-slate-400">{data.api_keys.length} keys</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Name</th>
                  <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Provider</th>
                  <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Prefix</th>
                  <th className="py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Status</th>
                  <th className="py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.api_keys.map((k) => {
                  const prov = providersById[k.provider_id];
                  return (
                    <tr key={k.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-3 text-sm font-medium text-slate-900 dark:text-slate-100">{k.name}</td>
                      <td className="py-3 text-sm text-slate-600 dark:text-slate-400">{prov?.display_name ?? "—"}</td>
                      <td className="py-3 text-sm text-slate-600 dark:text-slate-400 font-mono text-xs">{k.key_prefix}</td>
                      <td className="py-3 text-sm">
                        {k.test_ok ? (
                          <span className="flex items-center gap-1.5 text-green-700 dark:text-green-400">
                            <ShieldCheck size={14} /> Verified
                          </span>
                        ) : (
                          <span className="text-amber-700 dark:text-amber-400">Unverified</span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => testKey(k.id).then((ok) => ok && alert("Key verified"))}
                            className="btn-outline text-xs px-2 py-1.5"
                            title="Test key"
                          >
                            <ShieldCheck size={14} />
                          </button>
                          <button
                            onClick={() => toggleKey(k.id, !k.is_enabled)}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                            title={k.is_enabled ? "Disable" : "Enable"}
                          >
                            {k.is_enabled ? <ToggleRight size={16} className="text-green-600 dark:text-green-400" /> : <ToggleLeft size={16} className="text-slate-400" />}
                          </button>
                          <button
                            onClick={() => deleteKey(k.id)}
                            className="text-xs px-2 py-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {data.api_keys.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-400 text-sm">No keys added yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
