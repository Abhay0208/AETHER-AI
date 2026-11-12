import { useEffect, useState } from "react";
import { Plus, Edit, Trash2, Folder, FileText, Upload, Search, MoreHorizontal, ChevronRight } from "lucide-react";
import { api } from "../lib/api";

export function Files() {
  const [path, setPath] = useState(".");
  const [entries, setEntries] = useState<any[]>([]);
  const [current, setCurrent] = useState<{ path: string; content: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newContent, setNewContent] = useState("");
  const [isDir, setIsDir] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    load();
  }, [path, search]);

  async function load() {
    try {
      const r = await api.get("/files", { params: { path, q: search || undefined } });
      setEntries(r.data.entries ?? []);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load files");
    }
  }

  async function openFile(p: string, isDirectory: boolean) {
    if (isDirectory) {
      setPath(p === "." ? p + "" : p);
      setCurrent(null);
      return;
    }
    try {
      const r = await api.get("/files/text", { params: { path: p } });
      setCurrent(r.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Cannot open file");
    }
  }

  async function createItem() {
    if (!newName.trim()) return;
    setCreating(false);
    try {
      await api.post("/files", { path: newName, content: newContent, is_dir: isDir });
      setNewName("");
      setNewContent("");
      setIsDir(false);
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Create failed");
    }
  }

  async function saveFile() {
    if (!current) return;
    try {
      await api.put("/files/content", { path: current.path, content: current.content });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Save failed");
    }
  }

  async function removeItem(p: string, isDirectory: boolean) {
    if (!confirm(`Delete ${p}?`)) return;
    try {
      await api.delete("/files", { data: { path: p } });
      await load();
      if (current?.path === p) setCurrent(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  }

  async function renameItem(oldP: string) {
    const np = prompt("New name:", oldP);
    if (!np || np === oldP) return;
    try {
      await api.post("/files/rename", { path: oldP, new_path: np });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Rename failed");
    }
  }

  async function uploadFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("path", file.name);
    form.append("file", file);
    try {
      await api.post("/files/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      e.target.value = "";
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed");
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
            <Folder className="text-aether-600 dark:text-aether-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">File Workspace</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">{path}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-4 w-4" />
            <input
              className="input pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search files…"
            />
          </div>
          <button onClick={() => document.getElementById("file-input")?.click()} className="btn-outline text-sm">
            <Upload size={16} className="mr-2" /> Upload
          </button>
          <input id="file-input" type="file" className="hidden" onChange={uploadFile} />
        </div>
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {creating ? (
          <div className="panel p-4 max-w-sm">
            <label className="label">Name</label>
            <input className="input mb-2" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="file.txt or folder/" />
            <label className="label mb-2">Content</label>
            <textarea className="input mb-3" value={newContent} onChange={(e) => setNewContent(e.target.value)} rows={3} />
            <div className="flex items-center gap-2 mb-3">
              <input type="checkbox" checked={isDir} onChange={(e) => setIsDir(e.target.checked)} />
              <span className="text-sm text-slate-600 dark:text-slate-400">Create folder</span>
            </div>
            <div className="flex gap-2">
              <button onClick={createItem} className="btn flex-1">Create</button>
              <button onClick={() => setCreating(false)} className="btn-outline flex-1">Cancel</button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-3">
              <button onClick={() => setCreating(true)} className="btn-outline">
                <Plus size={16} className="mr-2" /> New
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {entries.map((e) => (
              <div key={e.path} className="panel p-3 cursor-pointer hover:border-aether-200 dark:hover:border-aether-800 transition group" onClick={() => openFile(e.path, e.is_dir)}>
                <div className="flex items-center gap-2 mb-2">
                  {e.is_dir ? (
                    <Folder className="text-aether-600 dark:text-aether-400" size={18} />
                  ) : (
                    <FileText className="text-slate-400" size={18} />
                  )}
                  <span className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">{e.name}</span>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-500">
                  {e.is_dir ? "Folder" : e.mime_type} • {e.size_bytes} B
                </div>
              </div>
            ))}
            {entries.length === 0 && <div className="col-span-full text-center py-10 text-slate-400">No files found.</div>}
          </div>
            </>
          )}
      </div>

      {current && (
        <div className="border-t border-slate-200 dark:border-slate-800 flex-1 min-h-0 flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate max-w-[60%]">{current.path}</span>
            </div>
            <div className="flex gap-1">
              <button onClick={renameItem.bind(null, current.path)} className="btn-outline text-xs px-2" title="Rename">
                <span className="sr-only">Rename</span>
              </button>
              <button onClick={() => removeItem(current.path, false)} className="btn-outline text-xs px-2 text-red-600 dark:text-red-400" title="Delete">
                <Trash2 size={14} />
              </button>
              <button onClick={saveFile} className="btn text-xs px-3" disabled={!current.content}>
                Save
              </button>
            </div>
          </div>
          <textarea
            className="flex-1 m-4 border-0 bg-transparent focus:ring-0 text-sm font-mono text-slate-700 dark:text-slate-300"
            value={current.content}
            onChange={(e) => setCurrent({ ...current, content: e.target.value })}
            rows={20}
            spellCheck={false}
          />
        </div>
      )}
    </div>
  );
}
