import { useEffect, useRef, useState } from "react";
import PdfViewer from "./PdfViewer";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(null); // citation currently open in the viewer
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, loading]);

  async function send(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);
    try {
      const r = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const data = await r.json();
      setMessages((m) => [...m, { role: "assistant", content: data.answer, facts: data.facts || [], citations: data.citations || [] }]);
      if (data.citations?.length) setActive(data.citations[0]); // open the viewer only when something is cited
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `Request failed: ${err.message}. Check that the API is running and allows CORS from this address.`, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  const showPdf = Boolean(active);
  const layout = !showPdf ? "single" : chatCollapsed ? "chat-collapsed" : "split";

  return (
    <div className="app">
      <header>
        <h1>Financial Report Assistant</h1>
        <button onClick={() => { setMessages([]); setActive(null); }}>Clear chat</button>
      </header>

      <main className={layout}>
        <section className={"pane" + (chatCollapsed && showPdf ? " collapsed" : "")}>
          <div className="bar">
            <span className="bar-title">Chat</span>
            {showPdf && (
              <button
                onClick={() => setChatCollapsed((c) => !c)}
                aria-expanded={!chatCollapsed}
                aria-label={chatCollapsed ? "Expand chat" : "Collapse chat"}
              >
                {chatCollapsed ? "»" : "«"}
              </button>
            )}
          </div>
          <div className="log" ref={logRef}>
            {messages.length === 0 && <p className="muted center">Ask about a report. Cited answers open their source PDF.</p>}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "q" : "a" + (m.error ? " error" : "")}>
                <p>{m.content}</p>
                {m.citations?.map((c, j) => (
                  <button
                    key={j}
                    className={"cite" + (active === c ? " on" : "")}
                    onClick={() => { setActive(c); setChatCollapsed(false); }}
                  >
                    {c.quote}
                    <small>{c.doc_title}, page {c.page}</small>
                  </button>
                ))}
                {m.facts?.length > 0 && (
                  <details className="facts">
                    <summary>Traversed graph relationships ({m.facts.length})</summary>
                    {m.facts.map((f, k) => <div key={k}>{f}</div>)}
                  </details>
                )}
              </div>
            ))}
            {loading && <p className="muted">Searching documents…</p>}
          </div>
          <form onSubmit={send}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }}
              placeholder="Ask a question"
              aria-label="Question"
            />
            <button className="primary" disabled={loading}>Ask</button>
          </form>
        </section>

        {showPdf && (
          <section className="pane">
            <PdfViewer
              url={active.pdf_url}
              page={active.page}
              quote={active.quote}
              title={active.doc_title}
              onClose={() => setActive(null)}
            />
          </section>
        )}
      </main>
    </div>
  );
}
