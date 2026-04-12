import { useState } from "react";
import axios from "axios";
import { Send, Bot } from "lucide-react";

export function CommandPrompt() {
  const [intent, setIntent] = useState("");
  const [loading, setLoading] = useState(false);
  const [responseMsg, setResponseMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!intent.trim()) return;

    setLoading(true);
    setResponseMsg("");
    try {
      const res = await axios.post("http://127.0.0.1:8000/api/v1/copilot/prompt", { intent });
      setResponseMsg(`Intent recognized. Task pipeline matched: \n${res.data.tasks.join(", ")}`);
      setIntent("");
    } catch (err) {
      console.error(err);
      setResponseMsg("Failed to connect to LangGraph Backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-4 bg-slate-900 border-b border-slate-700 text-slate-100">
      <div className="flex items-center gap-2 mb-2 font-semibold text-teal-400">
        <Bot size={20} />
        NeuroBoard Copilot
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="Design a Raspberry Pi AI HAT..."
          className="flex-1 bg-slate-800 border border-slate-600 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
          disabled={loading}
        />
        <button
          type="submit"
          className="bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-md flex items-center gap-2 transition-colors disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Thinking..." : <Send size={18} />}
        </button>
      </form>
      {responseMsg && <div className="text-sm mt-2 text-slate-300 font-mono whitespace-pre-line">{responseMsg}</div>}
    </div>
  );
}
