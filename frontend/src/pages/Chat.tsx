import { useEffect, useRef, useState } from "react";
import { Send, StopCircle, Maximize2, Minimize2, MessageSquare } from "lucide-react";
import { api } from "../lib/api";

export function Chat() {
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get("/models").then((r) => setModels(r.data.models ?? [])).catch(() => setModels([]));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !selectedModel) return;
    setError("");
    const userMsg = input;
    setInput("");
    setSending(true);
    setMessages([...messages, { role: "user", content: userMsg }]);

    try {
      const res = await api.post("/v1/chat/completions", {
        model: selectedModel,
        messages: [{ role: "user", content: userMsg }],
        stream: false,
      });
      setMessages([...messages, { role: "user", content: userMsg }, { role: "assistant", content: res.data.choices?.[0]?.message?.content ?? JSON.stringify(res.data) }]);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || "Request failed";
      setMessages([...messages, { role: "user", content: userMsg }, { role: "assistant", content: `⚠️ ${detail}` }]);
      setError(detail);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-aether-100 dark:bg-aether-900/30">
              <MessageSquare className="text-aether-600 dark:text-aether-400" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">Chat</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Streaming AI conversation</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input"
            >
              <option value="">Select a model</option>
              {models.map((m) => (
                <option key={m.id} value={m.model_id}>
                  {m.display_name || m.model_id} ({m.provider})
                </option>
              ))}
            </select>
            <button
              disabled={sending || !selectedModel}
              onClick={handleSend}
              className="btn disabled:opacity-50"
            >
              {sending ? <StopCircle size={16} className="mr-2" /> : <Send size={16} className="mr-2" />}
              {sending ? "Stopping…" : "Send"}
            </button>
          </div>
        </div>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <div className="text-4xl mb-2">💬</div>
            <p>Select a model and send a message.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={`max-w-[85%] p-3 rounded-xl text-sm ${
              m.role === "user"
                ? "bg-aether-600 text-white rounded-tr-none"
                : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none"
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="border-t border-slate-200 dark:border-slate-800 p-3">
        <form onSubmit={handleSend} className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message…"
            rows={1}
            className="input flex-1 resize-none focus:ring-aether-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || !selectedModel || sending}
            className="btn disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </form>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Phase 1 foundation: real endpoints. Provider adapters (live completions) arrive in Phase 2 — until then the gateway returns an honest configuration hint instead of a fake reply.
        </p>
      </div>
    </div>
  );
}
