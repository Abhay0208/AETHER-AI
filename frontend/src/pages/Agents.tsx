import { useEffect, useState } from "react";
import { Plus, Play, RefreshCw, Terminal, MessageSquare, FileText, Clock, Zap, CheckCircle } from "lucide-react";
import { api } from "../lib/api";

type Agent = { id: number; name: string; model: string; description: string };
type Task = {
  id: string;
  agent_id: number;
  title: string;
  status: string;
  progress: number;
  result: string | null;
  error: string | null;
  steps: any[];
  created_at: string;
};

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const [a, t] = await Promise.all([
        api.get("/agents").then((r) => r.data.agents ?? []),
        api.get("/tasks").then((r) => r.data.tasks ?? []),
      ]);
      setAgents(a);
      setTasks(t);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function createAgent() {
    const name = prompt("Agent name:");
    if (!name) return;
    const model = prompt("Model (e.g. mock-model):");
    if (!model) return;
    try {
      await api.post("/agents", { name, model, system_prompt: "You are a helpful AETHER agent." });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Create agent failed");
    }
  }

  async function createTask(agentId: number) {
    const title = prompt("Task title / goal:");
    if (!title) return;
    try {
      const r = await api.post("/tasks", { agent_id: agentId, title });
      await load();
      return r.data.task.id;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Create task failed");
    }
  }

  async function runTask(taskId: string) {
    setRunning(taskId);
    try {
      await api.post("/tasks/run", { task_id: taskId });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Run failed");
    } finally {
      setRunning(null);
    }
  }

  async function approveTask(taskId: string) {
    if (!confirm("Approve this task to continue?")) return;
    try {
      await api.post("/tasks/approve", { task_id: taskId });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Approve failed");
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
              <Zap className="text-aether-600 dark:text-aether-400" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">Agents</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Autonomous agents that plan and execute tasks using models and skills.
              </p>
            </div>
          </div>
          <button onClick={createAgent} className="btn-outline">
            <Plus size={16} className="mr-2" /> New Agent
          </button>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="panel p-4">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Agents</h4>
          <div className="space-y-2">
            {agents.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                <div className="flex-1">
                  <div className="font-medium text-slate-900 dark:text-white">{a.name}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {a.model} • {a.description || "No description"}
                  </div>
                </div>
                <button
                  onClick={() => createTask(a.id)}
                  className="btn-outline text-xs px-3 py-1.5"
                  title="Create task"
                >
                  <Plus size={14} className="mr-1" /> Task
                </button>
              </div>
            ))}
            {agents.length === 0 && (
              <div className="text-center py-4 text-slate-400 text-sm">No agents yet. Create one above.</div>
            )}
          </div>
        </div>

        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-slate-900 dark:text-white">Tasks</h4>
            <button onClick={load} className="btn-outline text-xs px-2">
              <RefreshCw size={14} className="mr-1" /> Refresh
            </button>
          </div>
          <div className="space-y-2">
            {tasks.map((t) => (
              <div key={t.id} className="panel p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-medium text-slate-900 dark:text-white">{t.title}</div>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    t.status === "completed"
                      ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                      : t.status === "failed"
                        ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                        : t.status === "awaiting_approval"
                          ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                  }`}>
                    {t.status}
                  </span>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                  Progress: {t.progress}%
                </div>
                <div className="flex gap-2">
                  {t.status === "queued" || t.status === "failed" ? (
                    <button
                      onClick={() => runTask(t.id)}
                      disabled={running === t.id}
                      className="btn-outline text-xs px-3 py-1.5 disabled:opacity-50"
                    >
                      {running === t.id ? "Running…" : <><Play size={14} className="mr-1" /> Run</>}
                    </button>
                  ) : null}
                  {t.status === "awaiting_approval" ? (
                    <button
                      onClick={() => approveTask(t.id)}
                      className="btn-outline text-xs px-3 py-1.5"
                    >
                      <CheckCircle size={14} className="mr-1" /> Approve
                    </button>
                  ) : null}
                  <button
                    onClick={() => {
                      const s = t.steps.find((st: any) => st.output);
                      if (s) alert(JSON.stringify(s.output, null, 2));
                    }}
                    className="text-xs px-3 py-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                  >
                    <FileText size={14} className="mr-1" /> Output
                  </button>
                </div>
                {t.error && (
                  <div className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                    Error: {t.error}
                  </div>
                )}
              </div>
            ))}
            {tasks.length === 0 && (
              <div className="text-center py-6 text-slate-400 text-sm">No tasks yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
