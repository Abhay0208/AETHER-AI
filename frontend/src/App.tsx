import { useEffect, useState } from "react";
import { LogIn, LogOut, LayoutDashboard, MessageSquare, File, Settings as SettingsIcon, Key, Play, Layout, Video as VideoIcon, Image as ImageIcon, Zap, Layers } from "lucide-react";
import { login, logout, me } from "./lib/auth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Chat } from "./pages/Chat";
import { Files } from "./pages/Files";
import { Models } from "./pages/Models";
import { APIKeys } from "./pages/APIKeys";
import { Settings } from "./pages/Settings";
import { Skills } from "./pages/Skills";
import { Agents } from "./pages/Agents";
import { Images } from "./pages/Images";
import { Video } from "./pages/Video";
import { VideoEditor } from "./pages/VideoEditor";
import { NotImplemented } from "./pages/NotImplemented";

type View = "dashboard" | "chat" | "files" | "models" | "apikeys" | "settings" | "skills" | "agents" | "images" | "video" | "video-editor" | "login";

const ROUTES: Record<View, { label: string; icon: React.ElementType }> = {
  dashboard: { label: "Dashboard", icon: LayoutDashboard },
  chat: { label: "Chat", icon: MessageSquare },
  files: { label: "Files", icon: File },
  models: { label: "Models", icon: Layout },
  apikeys: { label: "API Keys", icon: Key },
  settings: { label: "Settings", icon: SettingsIcon },
  skills: { label: "Skills", icon: Play },
  agents: { label: "Agents", icon: Zap },
  images: { label: "Images", icon: ImageIcon },
  video: { label: "Video", icon: VideoIcon },
  "video-editor": { label: "Video Editor", icon: Layers },
  login: { label: "Login", icon: LogIn },
};

export default function App() {
  const [view, setView] = useState<View>("login");
  const [user, setUser] = useState<{ id: number; username: string; is_admin: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const u = await me();
        setUser(u);
        setView("dashboard");
      } catch {
        setView("login");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const navItems: View[] = ["dashboard", "chat", "files", "models", "apikeys", "skills", "agents", "images", "video", "video-editor", "settings"];

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-aether-50 dark:bg-slate-950">
        <div className="flex flex-col items-center gap-2">
          <div className="h-12 w-12 rounded-xl bg-aether-600 flex items-center justify-center">
            <Zap className="text-white" size={24} />
          </div>
          <div className="text-lg font-semibold text-slate-900 dark:text-white">AETHER</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">Loading…</div>
        </div>
      </div>
    );
  }

  const isAuthView = view === "login";
  if (isAuthView && user) {
    return <Dashboard user={user} onLogout={logout} />;
  }

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
      {!isAuthView && (
        <aside className="hidden md:flex flex-col w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-3 p-5">
            <div className="h-8 w-8 rounded-lg bg-aether-600 flex items-center justify-center">
              <Zap className="text-white" size={18} />
            </div>
            <div>
              <div className="font-bold text-slate-900 dark:text-white tracking-tight">AETHER</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Local AI Platform</div>
            </div>
          </div>
          <nav className="flex-1 px-3 space-y-1">
            {navItems.map((v) => {
              const Comp = ROUTES[v].icon;
              const active = view === v;
              return (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                    active
                      ? "bg-aether-50 dark:bg-aether-900/20 text-aether-600 dark:text-aether-400"
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                  }`}
                >
                  <Comp size={18} />
                  {ROUTES[v].label}
                </button>
              );
            })}
          </nav>
          <div className="p-4 border-t border-slate-200 dark:border-slate-800">
            <button
              onClick={() => { logout(); setView("login"); setUser(null); }}
              className="flex w-full items-center gap-3 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg px-3 py-2 transition"
            >
              <LogOut size={16} />
              Sign out
            </button>
          </div>
        </aside>
      )}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur sticky top-0 z-10">
          <div className="flex items-center gap-3">
            {!isAuthView && (
              <button
                onClick={() => document.documentElement.classList.toggle("dark")}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                title="Toggle theme"
              >
                {document.documentElement.classList.contains("dark") ? (
                  <span className="text-yellow-500">☀</span>
                ) : (
                  <span className="text-slate-500">☾</span>
                )}
              </button>
            )}
            <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
              {isAuthView ? "Sign in" : ROUTES[view]?.label ?? "AETHER"}
            </h1>
          </div>
          {!isAuthView && user && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500 dark:text-slate-400 hidden md:inline">
                {user.username} ({user.is_admin ? "admin" : "user"})
              </span>
              <button
                onClick={() => { logout(); setView("login"); setUser(null); }}
                className="btn-outline"
              >
                <LogOut size={16} className="mr-2" /> Sign out
              </button>
            </div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {isAuthView ? (
            <Login onLogin={(u) => { setUser(u); setView("dashboard"); }} />
          ) : view === "dashboard" ? (
            <Dashboard user={user} onLogout={logout} />
          ) : view === "chat" ? (
            <Chat />
          ) : view === "files" ? (
            <Files />
          ) : view === "models" ? (
            <Models />
          ) : view === "apikeys" ? (
            <APIKeys />
          ) : view === "settings" ? (
            <Settings />
          ) : view === "skills" ? (
            <Skills />
          ) : view === "agents" ? (
            <Agents />
          ) : view === "images" ? (
            <Images />
          ) : view === "video" ? (
            <Video />
          ) : view === "video-editor" ? (
            <VideoEditor />
          ) : null}
        </main>
      </div>
    </div>
  );
}
