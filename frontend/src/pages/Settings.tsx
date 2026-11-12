import { useEffect, useState } from "react";
import { PanelLeft, Monitor, LockKeyhole, Info, Bell, RefreshCw } from "lucide-react";
import { api } from "../lib/api";

export function Settings() {
  const [theme, setTheme] = useState<string>("system");
  const [appName, setAppName] = useState("AETHER");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("aether_theme");
    if (stored) setTheme(stored);
    applyTheme(stored || "system");
  }, []);

  function applyTheme(t: string) {
    if (t === "dark") document.documentElement.classList.add("dark");
    else if (t === "light") document.documentElement.classList.remove("dark");
    else {
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (dark) document.documentElement.classList.add("dark");
      else document.documentElement.classList.remove("dark");
    }
  }

  function save() {
    localStorage.setItem("aether_theme", theme);
    applyTheme(theme);
    setSaving(true);
    setTimeout(() => setSaving(false), 600);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <PanelLeft className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Settings</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Configure AETHER preferences.</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-semibold text-slate-900 dark:text-white">Appearance</h4>
              <p className="text-sm text-slate-500 dark:text-slate-400">Choose the UI theme.</p>
            </div>
            <Info size={18} className="text-slate-400" aria-label="Theme preference is stored locally." />
          </div>
          <div className="space-y-3">
            {[
              { value: "system", label: "System", desc: "Follows your operating system" },
              { value: "light", label: "Light", desc: "Light mode" },
              { value: "dark", label: "Dark", desc: "Dark mode" },
            ].map((t) => (
              <button
                key={t.value}
                onClick={() => setTheme(t.value)}
                className={`flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
                  theme === t.value
                    ? "bg-aether-50 dark:bg-aether-900/20 border border-aether-200 dark:border-aether-800 text-aether-600 dark:text-aether-400"
                    : "bg-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <div className="flex items-center justify-center w-5 h-5 rounded-full border border-slate-300 dark:border-slate-600">
                  {theme === t.value && (
                    <div className="w-2.5 h-2.5 rounded-full bg-aether-600 dark:bg-aether-400" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-slate-900 dark:text-slate-100">{t.label}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{t.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="panel p-5">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-4">Application</h4>
          <div className="space-y-3">
            <div>
              <label className="label">App name</label>
              <input
                className="input"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                placeholder="AETHER"
              />
            </div>
            <button onClick={save} className="btn" disabled={saving}>
              {saving ? "Saving…" : <><RefreshCw size={16} className="mr-2" /> Save settings</>}
            </button>
          </div>
        </div>

        <div className="panel p-5">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-4">About</h4>
          <div className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
            <div className="flex justify-between">
              <span>Name</span>
              <span className="font-medium text-slate-900 dark:text-white">AETHER</span>
            </div>
            <div className="flex justify-between">
              <span>Tagline</span>
              <span className="font-medium text-slate-900 dark:text-white">One Platform. Limitless Intelligence.</span>
            </div>
            <div className="flex justify-between">
              <span>Version</span>
              <span className="font-mono">0.1.0-phase1</span>
            </div>
            <div className="flex justify-between">
              <span>License</span>
              <span>MIT (open source)</span>
            </div>
            <div className="flex justify-between">
              <span>Server</span>
              <span className="font-mono">http://localhost:5467</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
