import { useEffect, useState } from 'react'
import './App.css'

const suggestedQuestions = [
  {
    title: 'Understand the fees',
    question: 'What are the management fees?',
    icon: '↗',
  },
  {
    title: 'Explore the benchmark',
    question: 'What index does VAS track?',
    icon: '⌁',
  },
  {
    title: 'Check distributions',
    question: 'How often are distributions paid?',
    icon: '◷',
  },
]

function App() {
  const [question, setQuestion] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [citations, setCitations] = useState([])
  const [systemStats, setSystemStats] = useState(null)
  const [statsError, setStatsError] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    const loadSystemStats = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/stats/')
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.error || 'Could not load system status.')
        }
        if (!cancelled) {
          setSystemStats(data)
          setStatsError('')
        }
      } catch (err) {
        if (!cancelled) {
          setStatsError(err.message || 'System status is unavailable.')
        }
      }
    }

    loadSystemStats()
    return () => {
      cancelled = true
    }
  }, [])

  const askQuestion = async (event) => {
    event?.preventDefault()

    if (!question.trim()) {
      setError('Type a question to get started.')
      return
    }

    const currentQuestion = question.trim()
    setAskedQuestion(currentQuestion)
    setLoading(true)
    setError('')
    setAnswer('')
    setSources([])
    setCitations([])

    const ragQuestion =
      `For the Vanguard Australian Shares Index ETF (ASX: VAS), ${currentQuestion}`

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: ragQuestion }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'The server returned an error.')
      }

      const cleanAnswer = (data.answer || '')
        .replace(/\[[^\]]+\]/g, '')
        .split('---')[0]
        .trim()

      setAnswer(
        cleanAnswer || 'No answer was returned from the available documents.'
      )
      setSources(Array.isArray(data.sources) ? data.sources : [])
      setCitations(Array.isArray(data.citations) ? data.citations : [])
    } catch (err) {
      console.error('ETF Assistant Error:', err)
      setError(
        err.message ||
          'Unable to connect to the ETF assistant. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="ClariFi home">
          <span>ClariFi</span>
        </a>

        <div className="sidebar-section system-section">
          <p className="sidebar-label">SYSTEM STATUS</p>
          <div className="system-connection">
            <span
              className={`status-dot${systemStats?.neo4j?.connected ? '' : ' is-offline'}`}
            />
            <span>
              {systemStats?.neo4j?.connected
                ? `Neo4j connected`
                : statsError
                  ? 'Neo4j unavailable'
                  : 'Checking Neo4j…'}
            </span>
          </div>
          {systemStats?.neo4j?.server_agent && (
            <p className="database-version">{systemStats.neo4j.server_agent}</p>
          )}
          {systemStats?.neo4j?.apoc_installed && (
            <p className="apoc-status">APOC enabled</p>
          )}
          {statsError && <p className="system-error">{statsError}</p>}

          {systemStats?.models && (
            <div className="model-list">
              <div><span>LLM</span><strong>{systemStats.models.llm}</strong></div>
              <div>
                <span>Embeddings</span>
                <strong>
                  {systemStats.models.embeddings} · {systemStats.models.embedding_dim}d
                </strong>
              </div>
              <div><span>VLM</span><strong>{systemStats.models.vlm}</strong></div>
            </div>
          )}
        </div>

        {systemStats?.metrics && (
          <div className="sidebar-section graph-section">
            <p className="sidebar-label">GRAPH DATABASE</p>
            <div className="graph-metrics">
              <div><strong>{systemStats.metrics.documents}</strong><span>Documents</span></div>
              <div><strong>{systemStats.metrics.chunks}</strong><span>Chunks</span></div>
              <div><strong>{systemStats.metrics.tables}</strong><span>Tables</span></div>
              <div><strong>{systemStats.metrics.edges}</strong><span>Edges</span></div>
            </div>
          </div>
        )}

        <div className="sidebar-bottom">
          <span className={`status-dot${statsError ? ' is-offline' : ''}`} />
          <span>Local research assistant</span>
        </div>
      </aside>

      <main className="chat-page">
        <header className="topbar">
          <div className="mobile-brand">
            ClariFi
          </div>
          <div className="topbar-context">
            <span>Vanguard Australian Shares Index ETF</span>
            <span className="ticker-pill">VAS</span>
          </div>
        </header>

        <details className="mobile-system-panel">
          <summary>
            <span className={`status-dot${systemStats?.neo4j?.connected ? '' : ' is-offline'}`} />
            {systemStats?.neo4j?.connected
              ? `Neo4j connected · ${systemStats.metrics.chunks} chunks`
              : statsError
                ? 'System status unavailable'
                : 'Checking system status…'}
          </summary>
          {systemStats && (
            <div className="mobile-system-content">
              <div className="mobile-graph-metrics">
                <span>{systemStats.metrics.documents} documents</span>
                <span>{systemStats.metrics.chunks} chunks</span>
                <span>{systemStats.metrics.tables} tables</span>
                <span>{systemStats.metrics.edges} edges</span>
              </div>
              <p>LLM · {systemStats.models.llm}</p>
              <p>
                Embeddings · {systemStats.models.embeddings} · {systemStats.models.embedding_dim}d
              </p>
              <p>VLM · {systemStats.models.vlm}</p>
            </div>
          )}
        </details>

        <section className={`conversation${askedQuestion ? ' has-answer' : ''}`}>
          {!askedQuestion && (
            <div className="welcome">
              <p className="eyebrow">CLARITY FOR YOUR ETF</p>
              <h1>Good questions deserve<br />grounded answers.</h1>
              <p className="welcome-copy">
                Ask about VAS. I’ll look through its official documents and
                show you where the answer comes from.
              </p>

              <div className="suggestions">
                {suggestedQuestions.map((item) => (
                  <button
                    className="suggestion-card"
                    key={item.question}
                    onClick={() => setQuestion(item.question)}
                    type="button"
                  >
                    <span className="suggestion-icon" aria-hidden="true">
                      {item.icon}
                    </span>
                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.question}</small>
                    </span>
                    <span className="suggestion-arrow" aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {askedQuestion && (
            <div className="message-thread">
              <div className="user-message">
                <p>{askedQuestion}</p>
              </div>

              <article className="assistant-message">
                <div className="assistant-avatar" aria-hidden="true">C</div>
                <div className="assistant-content">
                  <p className="assistant-name">ClariFi</p>
                  {loading ? (
                    <div className="thinking">
                      <span className="thinking-dots"><i /><i /><i /></span>
                      <span>Searching official documents…</span>
                    </div>
                  ) : answer ? (
                    <>
                      <p className="answer-text">{answer}</p>

                      {citations.length > 0 && (
                        <div className="citation-list">
                          <p className="source-heading">SOURCES IN THE DOCUMENT</p>
                          {citations.map((citation, index) => (
                            <a
                              className="citation-card"
                              href={citation.pdf_url}
                              key={citation.chunk_id || index}
                              rel="noreferrer"
                              target="_blank"
                            >
                              <span className="pdf-icon" aria-hidden="true">PDF</span>
                              <span className="citation-detail">
                                <strong>{citation.doc_title}</strong>
                                <small>
                                  Page {citation.page}
                                  {citation.quote ? ` · “${citation.quote}”` : ''}
                                </small>
                              </span>
                              <span className="external-link" aria-hidden="true">↗</span>
                            </a>
                          ))}
                        </div>
                      )}

                      {sources.length > 0 && (
                        <details className="evidence-details">
                          <summary>
                            Retrieved evidence <span>{sources.length} excerpts</span>
                          </summary>
                          <div className="evidence-list">
                            {sources.map((source, index) => (
                              <div
                                className="evidence-item"
                                key={source.chunk_id || index}
                              >
                                <strong>
                                  Page {source.page_numbers?.join(', ') || '—'}
                                </strong>
                                <p>{source.text}</p>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </>
                  ) : null}
                </div>
              </article>
            </div>
          )}
        </section>

        <footer className="composer-area">
          {error && <p className="error-message">{error}</p>}
          <form className="composer" onSubmit={askQuestion}>
            <textarea
              aria-label="Ask a question about VAS"
              disabled={loading}
              onChange={(event) => {
                setQuestion(event.target.value)
                setError('')
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  askQuestion(event)
                }
              }}
              placeholder="Ask anything about VAS..."
              rows={2}
              value={question}
            />
            <div className="composer-tools">
              <span className="composer-hint">Answers grounded in official fund documents</span>
              <button
                aria-label={loading ? 'Searching' : 'Send question'}
                className="send-button"
                disabled={loading || !question.trim()}
                type="submit"
              >
                {loading ? <span className="button-spinner" /> : '↑'}
              </button>
            </div>
          </form>
          <p className="disclaimer">
            For information only, not personal financial advice.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default App
