import React, { useState, useRef, useEffect } from "react";
import axiosClient from "../../api/axiosClient";

export default function ChatPanel({ scanId, initialAdvice, initialSources }) {
  const [messages, setMessages] = useState(() => {
    if (initialAdvice) {
      return [{ role: "assistant", text: initialAdvice, sources: initialSources || [] }];
    }
    return [];
  });
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || streaming) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setStreaming(true);

    let partialText = "";
    let sources = [];
    setMessages((prev) => [...prev, { role: "assistant", text: "", streaming: true }]);

    try {
      const res = await fetch("/api/rag/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ scan_id: scanId, follow_up_question: question }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));
        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              partialText += data.token;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", text: partialText, streaming: true };
                return updated;
              });
            }
            if (data.done) {
              sources = data.sources || [];
            }
          } catch {}
        }
      }
    } catch (err) {
      partialText = "Error getting response. Please try again.";
    }

    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = { role: "assistant", text: partialText, sources, streaming: false };
      return updated;
    });
    setStreaming(false);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 p-4 bg-gray-50 rounded-xl min-h-48 max-h-96">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-6">
            Ask a follow-up question about the detected waste...
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-xs sm:max-w-sm rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-green-600 text-white"
                  : "bg-white border border-gray-200 text-gray-800 shadow-sm"
              }`}
            >
              {m.text}
              {m.streaming && <span className="animate-pulse ml-1">▌</span>}
              {m.sources?.length > 0 && (
                <details className="mt-2 text-xs text-gray-400">
                  <summary className="cursor-pointer">View sources ({m.sources.length})</summary>
                  <div className="mt-1 space-y-1">
                    {m.sources.map((s, j) => (
                      <div key={j} className="bg-gray-50 rounded p-1 border text-xs">{s}</div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex space-x-2 mt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
          placeholder="Ask about disposal, recycling rules..."
          disabled={streaming}
          className="flex-1 border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={streaming || !input.trim()}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-xl disabled:opacity-50 text-sm font-medium"
        >
          {streaming ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
