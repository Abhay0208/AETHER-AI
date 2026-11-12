import { useEffect, useState } from "react";
import { Plus, Play, Trash2, RefreshCw, CheckCircle, XCircle, Copy, Terminal } from "lucide-react";
import { api } from "../lib/api";

type Skill = {
  id: number;
  name: string;
  display_name: string;
  version: string;
  description: string;
  category: string;
  is_installed: number;
  is_enabled: number;
  is_builtin: number;
};

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [executing, setExecuting] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<any>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const r = await api.get("/skills");
      setSkills(r.data.skills ?? []);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }

  async function toggle(skill: Skill, enable: boolean) {
    try {
      await api.post(enable ? "/skills/enable" : "/skills/disable", { id: skill.id });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Toggle failed");
    }
  }

  async function uninstall(skill: Skill) {
    if (!confirm(`Uninstall "${skill.display_name}"?`)) return;
    try {
      await api.delete("/skills", { data: { id: skill.id } });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Uninstall failed");
    }
  }

  async function execute(skill: Skill, fn: string) {
    setExecuting(skill.name);
    setExecResult(null);
    try {
      const r = await api.post("/skills/execute", {
        skill: skill.name,
        function: fn,
        params: {},
      });
      setExecResult(r.data.result);
    } catch (err: any) {
      setExecResult({ ok: false, error: err.response?.data?.detail || "Execution failed" });
    } finally {
      setExecuting(null);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <Play className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Skills Marketplace</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Install, enable, and run AI skills. Skills run in a permission-gated sandbox.
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-slate-900 dark:text-white">Installed Skills</h4>
          <button onClick={load} className="btn-outline text-xs px-2">
            <RefreshCw size={14} className="mr-1" /> Refresh
          </button>
        </div>

        <div className="space-y-3">
          {skills.map((s) => (
            <div key={s.id} className="panel p-3 flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`font-medium text-slate-900 dark:text-white ${s.is_builtin ? "text-aether-600 dark:text-aether-400" : "text-slate-600 dark:text-slate-400"}`}>
                    {s.display_name}
                  </span>
                  {s.is_builtin && (
                    <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded">builtin</span>
                  )}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {s.description} • v{s.version} • {s.category}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded-full ${
                  s.is_enabled
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                }`}>
                  {s.is_enabled ? "Enabled" : "Disabled"}
                </span>
                <button
                  onClick={() => toggle(s, !s.is_enabled)}
                  disabled={Boolean(s.is_builtin) || executing === s.name}
                  className="btn-outline text-xs px-3 py-1.5 disabled:opacity-50"
                >
                  {executing === s.name ? "Running…" : s.is_enabled ? "Disable" : "Enable"}
                </button>
                {!s.is_builtin && (
                  <button
                    onClick={() => uninstall(s)}
                    className="text-xs px-3 py-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
                {s.name === "file_reader" && (
                  <button
                    onClick={() => execute(s, "read_file")}
                    disabled={executing === s.name}
                    className="btn-outline text-xs px-3 py-1.5 disabled:opacity-50"
                    title="Read skill_test.txt"
                  >
                    <Terminal size={14} className="mr-1" /> Run
                  </button>
                )}
              </div>
            </div>
          ))}
          {skills.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">No skills installed.</div>
          )}
        </div>

        {execResult && (
          <div className="panel p-4">
            <h4 className="font-semibold text-slate-900 dark:text-white mb-2">Execution Result</h4>
            <pre className="text-sm text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 p-3 rounded overflow-x-auto">
              {JSON.stringify(execResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
