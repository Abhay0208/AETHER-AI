import { useEffect, useState } from "react";
import { Plus, Play, RefreshCw, Trash2, Download, Video as VideoIcon, Film, Music, Subtitles, Layers, Zap, Scissors } from "lucide-react";
import { api } from "../lib/api";

export function VideoEditor() {
  const [projects, setProjects] = useState<any[]>([]);
  const [activeProject, setActiveProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rendering, setRendering] = useState<string | null>(null);

  const [projTitle, setProjTitle] = useState("");

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const r = await api.get("/edits");
      setProjects(r.data.projects ?? []);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  async function loadProject(id: number) {
    try {
      const r = await api.get(`/edits/${id}`);
      setActiveProject(r.data.project);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load project");
    }
  }

  async function createProject() {
    if (!projTitle.trim()) return;
    try {
      const r = await api.post("/edits", {
        title: projTitle,
        width: 1280,
        height: 720,
        fps: 30,
      });
      setProjTitle("");
      await loadProjects();
      setActiveProject(r.data.project);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create project");
    }
  }

  async function addTrack(trackType: string) {
    if (!activeProject) return;
    const name = prompt(`Track name (${trackType}):`, trackType.charAt(0).toUpperCase() + trackType.slice(1));
    if (!name) return;
    try {
      await api.post("/edits/tracks", {
        edit_id: activeProject.id,
        track_type: trackType,
        name,
      });
      await loadProject(activeProject.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add track");
    }
  }

  async function addClip(trackId: number) {
    if (!activeProject) return;
    const sourcePath = prompt("Media file path (relative to project root):", "data/storage/videos/");
    if (!sourcePath) return;
    const duration = prompt("Duration (seconds):", "5");
    if (!duration) return;
    try {
      await api.post("/edits/clips", {
        track_id: trackId,
        source_type: "video",
        source_path: sourcePath,
        start_time: 0,
        duration: Number(duration),
      });
      await loadProject(activeProject.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add clip");
    }
  }

  async function addSubtitle(trackId: number) {
    if (!activeProject) return;
    const text = prompt("Subtitle text:");
    if (!text) return;
    const start = prompt("Start time (seconds):", "0");
    const end = prompt("End time (seconds):", "5");
    if (!start || !end) return;
    try {
      await api.post("/edits/subtitles", {
        edit_id: activeProject.id,
        track_id: trackId,
        clip_id: null,
        start_time: Number(start),
        end_time: Number(end),
        text,
      });
      await loadProject(activeProject.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add subtitle");
    }
  }

  async function renderProject(preset: string) {
    if (!activeProject) return;
    setRendering(activeProject.id);
    try {
      await api.post("/edits/exports", {
        edit_id: activeProject.id,
        preset,
        format: "mp4",
        codec: "libx264",
        resolution: "1280x720",
        fps: 30,
      });
      await loadProject(activeProject.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to start render");
    } finally {
      setRendering(null);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
              <Film className="text-aether-600 dark:text-aether-400" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">Video Editor</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Multi-track timeline editor with transitions, subtitles, audio mixing,
                and FFmpeg rendering.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="input"
              value={projTitle}
              onChange={(e) => setProjTitle(e.target.value)}
              placeholder="Project name…"
            />
            <button onClick={createProject} className="btn disabled:opacity-50" disabled={!projTitle.trim()}>
              <Plus size={16} className="mr-2" /> New Project
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Projects list */}
        <div className="panel p-4">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Projects</h4>
          <div className="space-y-2">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => loadProject(p.id)}
                className={`flex items-center justify-between p-2 rounded-lg border border-slate-200 dark:border-slate-800 cursor-pointer transition ${
                  activeProject?.id === p.id ? "bg-aether-50 dark:bg-aether-900/30 border-aether-500" : "hover:bg-slate-50 dark:hover:bg-slate-800"
                }`}
              >
                <div className="flex-1">
                  <div className="font-medium text-slate-900 dark:text-white">{p.title}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {p.status} • {p.width}x{p.height} @ {p.fps}fps
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  p.status === "completed"
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                    : p.status === "failed"
                      ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                      : p.status === "rendering"
                        ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                }`}>
                  {p.status}
                </span>
              </div>
            ))}
            {projects.length === 0 && (
              <div className="text-center py-4 text-slate-400 text-sm">No projects yet. Create one above.</div>
            )}
          </div>
        </div>

        {/* Timeline editor */}
        {activeProject && (
          <div className="panel p-4 flex-1 min-h-0 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-slate-900 dark:text-white">
                {activeProject.title}
              </h4>
              <div className="flex items-center gap-2">
                <select
                  className="input text-sm"
                  value="youtube"
                  onChange={(e) => renderProject(e.target.value)}
                  disabled={rendering === activeProject.id}
                >
                  <option value="youtube">YouTube</option>
                  <option value="tiktok">TikTok</option>
                  <option value="instagram">Instagram</option>
                  <option value="twitter">Twitter</option>
                </select>
                <button
                  onClick={() => renderProject("youtube")}
                  disabled={rendering === activeProject.id}
                  className="btn disabled:opacity-50"
                >
                  {rendering === activeProject.id ? "Rendering…" : <><Film size={16} className="mr-2" /> Render</>}
                </button>
              </div>
            </div>

            {/* Tracks */}
            <div className="flex-1 overflow-y-auto space-y-2">
              {activeProject.tracks.map((track: any) => (
                <div key={track.id} className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                  <div className="w-20 text-xs font-medium text-slate-600 dark:text-slate-400 truncate">
                    {track.name} ({track.track_type})
                  </div>
                  <div className="flex-1 h-10 bg-slate-200 dark:bg-slate-800 rounded relative overflow-hidden">
                    {track.clips.map((clip: any) => (
                      <div
                        key={clip.id}
                        className="absolute left-0 top-0 h-full bg-aether-600 dark:bg-aether-400 rounded-sm opacity-80 border border-white/20"
                        style={{
                          width: `${Math.max((clip.duration || 5) * 20, 40)}px`,
                        }}
                        title={`${clip.source_type}: ${(clip.duration || 5).toFixed(1)}s`}
                      />
                    ))}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => addClip(track.id)}
                      className="text-xs px-2 py-1 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                      title="Add clip"
                    >
                      <Plus size={14} />
                    </button>
                    {track.track_type === "subtitle" && (
                      <button
                        onClick={() => addSubtitle(track.id)}
                        className="text-xs px-2 py-1 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                        title="Add subtitle"
                      >
                        <Subtitles size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => {
                        // delete track
                      }}
                      className="text-xs px-2 py-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                      title="Delete track"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
              <div className="flex gap-1">
                {["video", "audio", "subtitle"].map((t) => (
                  <button
                    key={t}
                    onClick={() => addTrack(t)}
                    className="flex-1 btn-outline text-xs px-2 py-1.5"
                  >
                    <Plus size={14} className="mr-1" /> {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
