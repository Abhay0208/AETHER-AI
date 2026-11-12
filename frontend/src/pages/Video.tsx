import { useEffect, useState } from "react";
import { Plus, Play, RefreshCw, Trash2, Download, Video as VideoIcon } from "lucide-react";
import { api } from "../lib/api";

export function Video() {
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState("30");
  const [resolution, setResolution] = useState("1280x720");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [providers, setProviders] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");

  useEffect(() => {
    loadProviders();
    loadVideos();
  }, []);

  async function loadProviders() {
    try {
      const r = await api.get("/providers");
      setProviders(r.data.providers ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load providers");
    }
  }

  async function loadProviderModels(pid: number) {
    try {
      const r = await api.get("/api/video/models", { params: { provider_id: pid } });
      setModels(r.data.models ?? []);
      if (r.data.models?.[0]) {
        setModel(r.data.models[0].id);
      }
    } catch (err: any) {
      setModels([]);
    }
  }

  async function loadVideos() {
    try {
      const r = await api.get("/video");
      setVideos(r.data.videos ?? []);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load videos");
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    if (!prompt.trim() || !providerId || !model) return;
    setGenerating(true);
    try {
      await api.post("/video/generate", {
        title,
        provider_id: Number(providerId),
        model,
        prompt,
        duration: Number(duration),
        resolution,
        aspect_ratio: aspectRatio,
      });
      setPrompt("");
      await loadVideos();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function removeVideo(id: number) {
    if (!confirm("Delete this video?")) return;
    try {
      await api.delete("/video", { data: { id } });
      await loadVideos();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <VideoIcon className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Video Generation</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Scene-based AI video generation with FFmpeg assembly. Long videos are
              built by combining multiple clips.
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

        {/* Generate panel */}
        <div className="panel p-4">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Generate Video</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="lg:col-span-2">
              <label className="label">Title</label>
              <input
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="My AI Video"
              />
            </div>
            <div className="lg:col-span-2">
              <label className="label">Prompt</label>
              <input
                className="input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="A cyberpunk cat walking through neon city streets…"
              />
            </div>
            <div>
              <label className="label">Provider</label>
              <select
                className="input"
                value={providerId}
                onChange={(e) => {
                  setProviderId(e.target.value);
                  loadProviderModels(Number(e.target.value));
                }}
              >
                <option value="">Select provider</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Model</label>
              <select className="input" value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="">Select model</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name || m.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Duration (seconds)</label>
              <input
                className="input"
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                min="1"
                max="3600"
              />
            </div>
            <div>
              <label className="label">Resolution</label>
              <select className="input" value={resolution} onChange={(e) => setResolution(e.target.value)}>
                <option value="640x360">640×360</option>
                <option value="1280x720">1280×720</option>
                <option value="1920x1080">1920×1080</option>
              </select>
            </div>
            <div>
              <label className="label">Aspect Ratio</label>
              <select className="input" value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)}>
                <option value="16:9">16:9</option>
                <option value="9:16">9:16</option>
                <option value="1:1">1:1</option>
              </select>
            </div>
            <div className="lg:col-span-4 flex items-end">
              <button
                onClick={generate}
                disabled={generating || !prompt.trim() || !providerId || !model}
                className="btn w-full disabled:opacity-50"
              >
                {generating ? <><Play size={16} className="mr-2" /> Generating…</> : <><VideoIcon size={16} className="mr-2" /> Generate Video</>}
              </button>
            </div>
          </div>
        </div>

        {/* Gallery */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-slate-900 dark:text-white">Generated Videos</h4>
            <button onClick={loadVideos} className="btn-outline text-xs px-2">
              <RefreshCw size={14} className="mr-1" /> Refresh
            </button>
          </div>
          <div className="space-y-3">
            {videos.map((v) => (
              <div key={v.id} className="panel p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-medium text-slate-900 dark:text-white truncate">
                      {v.title}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {v.model} • {v.provider} • {v.duration}s • {v.status}
                    </div>
                    {v.file_path && (
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[80%]">
                        {v.file_path}
                      </div>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    v.status === "completed"
                      ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                      : v.status === "failed"
                        ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                  }`}>
                    {v.status}
                  </span>
                </div>
                {v.file_path && (
                  <video
                    controls
                    className="w-full max-w-[320px] rounded-lg bg-black"
                    src={`/static/${v.file_path.replace(/^.*?storage\//, "")}`}
                  />
                )}
                <button
                  onClick={() => removeVideo(v.id)}
                  className="mt-2 text-xs px-3 py-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                >
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            ))}
            {videos.length === 0 && (
              <div className="text-center py-10 text-slate-400 text-sm">
                No videos yet. Generate your first video above.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
