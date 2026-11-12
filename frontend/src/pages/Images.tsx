import { useEffect, useState } from "react";
import { Plus, Image as ImageIcon, RefreshCw, Trash2, Play } from "lucide-react";
import { api } from "../lib/api";

export function Images() {
  const [images, setImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [providerId, setProviderId] = useState("");
  const [size, setSize] = useState("1024x1024");
  const [providers, setProviders] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  useEffect(() => {
    loadProviders();
    loadImages();
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
      const r = await api.get("/api/images/models", { params: { provider_id: pid } });
      setModels(r.data.models ?? []);
      if (r.data.models?.[0]) setModel(r.data.models[0].id);
    } catch (err: any) {
      setModels([]);
    }
  }

  async function loadImages() {
    try {
      const r = await api.get("/images");
      setImages(r.data.images ?? []);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load images");
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    if (!prompt.trim() || !providerId || !model) return;
    setGenerating(true);
    try {
      await api.post("/images/generate", {
        provider_id: Number(providerId),
        model,
        prompt,
        size,
      });
      setPrompt("");
      await loadImages();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function removeImage(id: number) {
    if (!confirm("Delete this image?")) return;
    try {
      await api.delete("/images", { data: { id } });
      await loadImages();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <ImageIcon className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Image Generation</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Generate images with connected providers and save them locally.
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
          <h4 className="font-semibold text-slate-900 dark:text-white mb-3">Generate Image</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="lg:col-span-2">
              <label className="label">Prompt</label>
              <input
                className="input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="A cyberpunk cat in neon lights…"
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
              <label className="label">Size</label>
              <select className="input" value={size} onChange={(e) => setSize(e.target.value)}>
                <option value="1024x1024">1024×1024</option>
                <option value="1024x1792">1024×1792</option>
                <option value="1792x1024">1792×1024</option>
              </select>
            </div>
            <div className="lg:col-span-4 flex items-end">
              <button
                onClick={generate}
                disabled={generating || !prompt.trim() || !providerId || !model}
                className="btn w-full disabled:opacity-50"
              >
                {generating ? <><Play size={16} className="mr-2" /> Generating…</> : <><ImageIcon size={16} className="mr-2" /> Generate</>}
              </button>
            </div>
          </div>
        </div>

        {/* Gallery */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-slate-900 dark:text-white">Generated Images</h4>
            <button onClick={loadImages} className="btn-outline text-xs px-2">
              <RefreshCw size={14} className="mr-1" /> Refresh
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {images.map((img) => (
              <div key={img.id} className="panel p-2 flex flex-col">
                <div className="aspect-square overflow-hidden rounded-lg bg-slate-200 dark:bg-slate-800 relative">
                  {img.file_path ? (
                    <img
                      src={`/static/${img.file_path}`}
                      alt={img.prompt}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-slate-400 text-xs">
                      No preview
                    </div>
                  )}
                  <button
                    onClick={() => removeImage(img.id)}
                    className="absolute top-1 right-1 bg-black/50 backdrop-blur text-white rounded p-1 hover:bg-black/70"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="mt-2">
                  <div className="text-sm font-medium text-slate-900 dark:text-white truncate">
                    {img.prompt}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {img.model} • {img.provider} • {img.status}
                  </div>
                </div>
              </div>
            ))}
            {images.length === 0 && (
              <div className="col-span-full text-center py-10 text-slate-400 text-sm">
                No images yet. Generate your first image above.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
