import React, { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import SettingsModal from './components/SettingsModal'
import FeatureTourModal from './components/FeatureTourModal'
import Visualizer from './components/Visualizer'
import ChatMessage from './components/ChatMessage'
import ChatLanding from './components/landing/ChatLanding'
import EtfDropdown, { VANGUARD_ETFS } from './components/EtfDropdown'
import {
  CoinsIcon,
  TrendingUpIcon,
  CalendarIcon,
  BarChartIcon,
  FileTextIcon,
  SendIcon,
  LayersIcon,
  ChevronRightIcon,
  ExternalLinkIcon,
  SettingsIcon,
  SunIcon,
  MoonIcon,
} from './components/Icons'
import { loadConversations, saveConversations, createNewConversation } from './utils/conversationStorage'
import { formatTime } from './utils/formatters'
import './App.css'

const suggestedQuestions = [
  {
    title: 'Understand the fees',
    question: 'What are the management fees?',
    icon: <CoinsIcon size={18} />,
  },
  {
    title: 'Explore the benchmark',
    question: 'What index does VAS track?',
    icon: <TrendingUpIcon size={18} />,
  },
  {
    title: 'Check distributions',
    question: 'How often are distributions paid?',
    icon: <CalendarIcon size={18} />,
  },
  {
    title: 'Annual return chart',
    question: 'build a plot with this years return percentage',
    icon: <BarChartIcon size={18} />,
  },
]

export default function App() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [systemStats, setSystemStats] = useState(null)
  const [statsError, setStatsError] = useState('')

  // Modals & UI state (Task 6: Feature Tour auto-opens on entry)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isTourOpen, setIsTourOpen] = useState(true)
  const [landingVariant, setLandingVariant] = useState(() => localStorage.getItem('clarifi_landing_variant') || 'minimal')
  const [theme, setTheme] = useState(() => localStorage.getItem('clarifi_theme') || 'dark')
  const [font, setFont] = useState(() => localStorage.getItem('clarifi_font') || 'inter')

  // Selected ETF Context (Task 7)
  const [selectedEtf, setSelectedEtf] = useState(VANGUARD_ETFS[0])

  // Visualizer state (Task 3: Dual-Mode PDF & Chart)
  const [isVisualizerOpen, setIsVisualizerOpen] = useState(false)
  const [visualizerMode, setVisualizerMode] = useState('pdf') // 'pdf' | 'chart'
  const [activeCitation, setActiveCitation] = useState(null)
  const [activeChart, setActiveChart] = useState(null)
  const [isVisualizerExpanded, setIsVisualizerExpanded] = useState(false)

  // Conversation storage & session state
  const [conversations, setConversations] = useState(() => {
    const saved = loadConversations()
    if (saved && saved.length > 0) return saved
    return [createNewConversation('Vanguard Australian Shares (VAS)')]
  })

  const [activeConversationId, setActiveConversationId] = useState(() => {
    const saved = loadConversations()
    return saved && saved.length > 0 ? saved[0].id : 'conv-default'
  })

  // Track the ID of the newly generated message to scope sequential delayed animation exclusively to fresh answers
  const [newlyGeneratedMsgId, setNewlyGeneratedMsgId] = useState(null)

  const textareaRef = useRef(null)
  const messagesEndRef = useRef(null)

  // Persist conversations to localStorage whenever they change
  useEffect(() => {
    saveConversations(conversations)
  }, [conversations])

  // Get active conversation or fallback
  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) || conversations[0]
  const messages = activeConversation?.messages || []

  // Collect all citations across current message thread for multi-citation navigation
  const allThreadCitations = messages.flatMap((m) => {
    if (m.citations && m.citations.length > 0) return m.citations
    if (m.sources && m.sources.length > 0) {
      return m.sources.map((s, idx) => ({
        chunk_id: s.chunk_id || `chunk-${idx}`,
        doc_title: s.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
        page: s.page || (s.page_numbers && s.page_numbers[0]) || 1,
        quote: s.quote || s.text || '',
        pdf_url: s.pdf_url || `/api/pdf/AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf#page=${(s.page_numbers && s.page_numbers[0]) || 1}`,
      }))
    }
    return []
  })

  // Auto-scroll message viewport to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0 || loading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length, loading])

  // Apply theme to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('clarifi_theme', theme)
  }, [theme])

  // Apply font family attribute to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-font', font)
    localStorage.setItem('clarifi_font', font)
  }, [font])

  // Persist landing page variant ('minimal' vs 'classic')
  useEffect(() => {
    localStorage.setItem('clarifi_landing_variant', landingVariant)
  }, [landingVariant])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  // Load telemetry from Django API
  useEffect(() => {
    let cancelled = false
    const loadSystemStats = async () => {
      try {
        const response = await fetch('/api/stats/')
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

  // Keyboard shortcut: Cmd+K / Ctrl+K for new chat & Cmd+Shift+T for theme toggle
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        handleNewChat()
      } else if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'T' || e.key === 't')) {
        e.preventDefault()
        toggleTheme()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [conversations, activeConversationId])

  // Handler: Start a new conversation thread
  const handleNewChat = () => {
    if (messages.length === 0) {
      textareaRef.current?.focus()
      return
    }

    const newConv = createNewConversation('New Conversation')
    setConversations((prev) => [newConv, ...prev])
    setActiveConversationId(newConv.id)
    setNewlyGeneratedMsgId(null)
    setQuestion('')
    setError('')
    setIsVisualizerOpen(false)
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  // Handler: Delete conversation session
  const handleDeleteConversation = (convId) => {
    setNewlyGeneratedMsgId(null)
    const remaining = conversations.filter((c) => c.id !== convId)
    if (remaining.length === 0) {
      const fresh = createNewConversation('Vanguard Australian Shares (VAS)')
      setConversations([fresh])
      setActiveConversationId(fresh.id)
    } else {
      setConversations(remaining)
      if (activeConversationId === convId) {
        setActiveConversationId(remaining[0].id)
      }
    }
  }

  // Handler: Open citation in Visualizer (Requirement 3.2 & Item 1)
  const handleOpenCitationInVisualizer = (citation) => {
    const fullCitation = {
      chunk_id: citation.chunk_id || 'vas_source',
      doc_title: citation.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
      page: Number(citation.page || (citation.page_numbers && citation.page_numbers[0]) || 1),
      quote: citation.quote || citation.text || '',
      pdf_url:
        citation.pdf_url ||
        `/api/pdf/${citation.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf'}#page=${Number(citation.page || (citation.page_numbers && citation.page_numbers[0]) || 1)}`,
    }

    setActiveCitation(fullCitation)
    setVisualizerMode('pdf')
    setIsVisualizerOpen(true)
  }

  // Handler: Open chart in Visualizer (Requirement 3.3 & Item 2)
  const handleOpenChartInVisualizer = (chartData) => {
    setActiveChart(chartData)
    setVisualizerMode('chart')
    setIsVisualizerOpen(true)
  }

  // Check if query is targeting the specific hardwired chart prompt
  const isHardwiredChartPrompt = (q) => {
    const clean = q.toLowerCase().replace(/['’]/g, '').trim()
    return (
      clean === 'build a plot with this years return percentage' ||
      clean.includes('plot with this years return') ||
      clean.includes('build a plot with this year return') ||
      clean.includes('plot return percentage') ||
      (clean.includes('plot') && clean.includes('return percentage'))
    )
  }

  // Handler: Ask question / send turn
  const askQuestion = async (event, customQuestion = null) => {
    event?.preventDefault()

    const currentQuestion = (customQuestion || question).trim()
    if (!currentQuestion) {
      setError('Type a question to get started.')
      return
    }

    setQuestion('')
    setError('')
    setLoading(true)

    const userMessage = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: currentQuestion,
      timestamp: formatTime(new Date()),
    }

    setNewlyGeneratedMsgId(userMessage.id)

    // Determine updated conversation title if this is the first turn
    const isFirstTurn = messages.length === 0
    const updatedTitle = isFirstTurn
      ? currentQuestion.slice(0, 34) + (currentQuestion.length > 34 ? '…' : '')
      : activeConversation.title

    // Append user message immediately
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConversationId
          ? {
            ...c,
            title: updatedTitle,
            messages: [...c.messages, userMessage],
          }
          : c
      )
    )

    // ─────────────────────────────────────────────────────────────────────────────
    // HARDWIRED PROMPT HANDLING (Requirement 2):
    // "build a plot with this years return percentage"
    // Surpasses retrieval, adds simulated thinking delay, returns a clickable chart bubble.
    // ─────────────────────────────────────────────────────────────────────────────
    if (isHardwiredChartPrompt(currentQuestion)) {
      setTimeout(() => {
        const chartCitations = [
          {
            chunk_id: 'chart_table_0',
            doc_title: 'ETF-Vanguard_Australian_Shares_Index_ETF_8205_FS_VAS.pdf',
            page: 1,
            quote:
              'Total return performance (as at 31 Dec 2024): 1-Year VAS 12.12% vs Benchmark 12.10%; 3-Year 7.82% vs 7.79%; 5-Year 8.41% vs 8.38%; 10-Year 8.15% vs 8.12%.',
            pdf_url: '/api/pdf/ETF-Vanguard_Australian_Shares_Index_ETF_8205_FS_VAS.pdf#page=1',
          },
        ]

        const assistantMessage = {
          id: `msg-${Date.now()}-assistant`,
          role: 'assistant',
          content:
            `I have retrieved the annual performance data for the Vanguard Australian Shares Index ETF (ASX: VAS) and synthesized the total return percentages against the S&P/ASX 300 Accumulation Index benchmark:\n\n` +
            `• **1-Year Total Return**: **12.12%** (Benchmark: 12.10% · Outperformance: +0.02%)\n` +
            `• **3-Year Annualized**: **7.82%** (Benchmark: 7.79% · Tracking diff: +0.03%)\n` +
            `• **5-Year Annualized**: **8.41%** (Benchmark: 8.38% · Tracking diff: +0.03%)\n` +
            `• **10-Year Annualized**: **8.15%** (Benchmark: 8.12% · Long-term CAGR)\n\n` +
            `The visualization agent has synthesized the table disclosures and built the comparative performance plot. Click the chart bubble below to launch the visualizer:`,
          chartData: {
            title: 'VAS Annualized Return Percentage vs S&P/ASX 300',
            src: theme === 'light' ? '/charts/vas_returns_light.svg' : '/charts/vas_returns.svg',
          },
          citations: chartCitations,
          sources: [
            {
              chunk_id: 'chart_table_0',
              doc_title: 'ETF-Vanguard_Australian_Shares_Index_ETF_8205_FS_VAS.pdf',
              page: 1,
              page_numbers: [1],
              vector_score: 0.98,
              text: 'Vanguard Australian Shares Index ETF performance table: 1 yr 12.12%, 3 yr 7.82%, 5 yr 8.41%, 10 yr 8.15%. Growth of $10,000 invested.',
              pdf_url: '/api/pdf/ETF-Vanguard_Australian_Shares_Index_ETF_8205_FS_VAS.pdf#page=1',
            },
          ],
          timestamp: formatTime(new Date()),
        }

        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConversationId
              ? { ...c, messages: [...c.messages, assistantMessage] }
              : c
          )
        )

        setNewlyGeneratedMsgId(assistantMessage.id)

        // Ready the chart data in state (does NOT auto-open; user clicks chart bubble)
        setActiveChart({
          title: 'VAS Annualized Return Percentage vs S&P/ASX 300',
          src: theme === 'light' ? '/charts/vas_returns_light.svg' : '/charts/vas_returns.svg',
        })

        setLoading(false)
      }, 18000)

      return
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // STANDARD RAG PIPELINE
    // ─────────────────────────────────────────────────────────────────────────────
    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    const ragQuestion = `For the ${selectedEtf?.name || 'Vanguard Australian Shares Index ETF'} (${selectedEtf?.asxCode || 'ASX: VAS'}), ${currentQuestion}`

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: ragQuestion,
          history: historyPayload,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'The server returned an error.')
      }

      const cleanAnswer = (data.answer || '')
        .replace(/\[[^\]]+\](?!\()/g, '')
        .split('---')[0]
        .trim()

      const rawSources = Array.isArray(data.sources) ? data.sources : []
      const rawCitations = Array.isArray(data.citations) ? data.citations : []

      // If citations is empty but sources exists, synthesize citations from sources
      const resolvedCitations =
        rawCitations.length > 0
          ? rawCitations
          : rawSources.map((s, idx) => ({
            chunk_id: s.chunk_id || `source-chunk-${idx}`,
            doc_title: s.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
            page: s.page || (s.page_numbers && s.page_numbers[0]) || 1,
            quote: s.quote || s.text || '',
            pdf_url:
              s.pdf_url ||
              `/api/pdf/${s.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf'}#page=${s.page || (s.page_numbers && s.page_numbers[0]) || 1}`,
          }))

      const assistantMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: cleanAnswer || 'No answer was returned from the available documents.',
        citations: resolvedCitations,
        sources: rawSources,
        timestamp: formatTime(new Date()),
      }

      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversationId
            ? { ...c, messages: [...c.messages, assistantMessage] }
            : c
        )
      )

      setNewlyGeneratedMsgId(assistantMessage.id)

      // If visualizer is already open in PDF mode and we received citations, update view
      if (resolvedCitations.length > 0 && isVisualizerOpen && visualizerMode === 'pdf') {
        setActiveCitation(resolvedCitations[0])
      }
    } catch (err) {
      console.error('ClariFi Error:', err)
      const errorMessage = {
        id: `msg-${Date.now()}-error`,
        role: 'assistant',
        content: `Unable to connect to the ClariFi assistant: ${err.message}. Ensure the backend is reachable.`,
        error: true,
        timestamp: formatTime(new Date()),
      }

      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversationId
            ? { ...c, messages: [...c.messages, errorMessage] }
            : c
        )
      )

      setNewlyGeneratedMsgId(errorMessage.id)
    } finally {
      setLoading(false)
    }
  }

  const shellClasses = [
    'app-shell',
    isVisualizerOpen ? 'has-visualizer' : '',
    isVisualizerExpanded ? 'is-visualizer-expanded' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={shellClasses}>
      {/* 1. Restructured Sidebar */}
      <Sidebar
        onNewChat={handleNewChat}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenTour={() => setIsTourOpen(true)}
        systemStats={systemStats}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={(id) => {
          setActiveConversationId(id)
          setNewlyGeneratedMsgId(null)
          setError('')
        }}
        onDeleteConversation={handleDeleteConversation}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* 2. Main Chat Panel */}
      <main className="chat-page">
        {/* Topbar (Task 7: Decluttered, no theme/tour/settings; right-aligned ETF dropdown) */}
        <header className="topbar">
          <div className="topbar-left">
            {/* Quick Visualizer toggle button if citations or a chart are available */}
            {(allThreadCitations.length > 0 || activeChart) && (
              <button
                type="button"
                className={`topbar-visualizer-btn ${isVisualizerOpen ? 'active' : ''}`}
                onClick={() => {
                  if (!isVisualizerOpen) {
                    if (visualizerMode === 'chart' && activeChart) {
                      setIsVisualizerOpen(true)
                    } else if (allThreadCitations.length > 0) {
                      setActiveCitation(allThreadCitations[0])
                      setVisualizerMode('pdf')
                      setIsVisualizerOpen(true)
                    } else {
                      setIsVisualizerOpen(true)
                    }
                  } else {
                    setIsVisualizerOpen(false)
                  }
                }}
                title="Toggle Split-Screen Visualizer"
              >
                <span>{visualizerMode === 'chart' ? <BarChartIcon size={14} /> : <FileTextIcon size={14} />}</span>
                <span>Visualizer</span>
              </button>
            )}
          </div>

          <div className="topbar-right">
            <EtfDropdown
              selectedEtf={selectedEtf}
              onSelectEtf={(etf) => setSelectedEtf(etf)}
            />
          </div>
        </header>

        {/* Conversation Viewport */}
        <div className="conversation-scroll-wrapper">
          <section className={`conversation ${messages.length > 0 ? 'has-answer' : ''}`}>
            {/* Landing State: Shown only when thread has 0 messages */}
            {/* Landing State: Modular ChatLanding (Minimal Looping Video vs Classic Overview) */}
            {messages.length === 0 && (
              <ChatLanding
                variant={landingVariant}
                theme={theme}
                onOpenTour={() => setIsTourOpen(true)}
                onSelectQuestion={(q) => askQuestion(null, q)}
                suggestedQuestions={suggestedQuestions}
              />
            )}

            {/* Multi-turn Message Thread with Progressive Reveal */}
            {messages.length > 0 && (
              <div className="message-thread">
                {messages.map((msg, index) => (
                  <ChatMessage
                    key={msg.id}
                    msg={msg}
                    isLatest={index === messages.length - 1}
                    isNewlyGenerated={msg.id === newlyGeneratedMsgId}
                    activeCitation={activeCitation}
                    isVisualizerOpen={isVisualizerOpen}
                    visualizerMode={visualizerMode}
                    onOpenCitation={handleOpenCitationInVisualizer}
                    onOpenChart={handleOpenChartInVisualizer}
                    onStageChange={() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })}
                    onAnimationComplete={(completedId) => {
                      setNewlyGeneratedMsgId((curr) => (curr === completedId ? null : curr))
                    }}
                  />
                ))}

                {/* Thinking placeholder during inference */}
                {loading && (
                  <article className="assistant-message">
                    <div className="assistant-avatar" aria-hidden="true">
                      C
                    </div>
                    <div className="assistant-content">
                      <p className="assistant-name">ClariFi Research Assistant</p>
                      <div className="thinking">
                        <span className="thinking-dots">
                          <i />
                          <i />
                          <i />
                        </span>
                        <span>Searching official documents & traversing knowledge graph…</span>
                      </div>
                    </div>
                  </article>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </section>
        </div>

        {/* Composer Area */}
        <footer className="composer-area">
          {error && <p className="error-message">{error}</p>}
          <form className="composer" onSubmit={askQuestion}>
            <textarea
              ref={textareaRef}
              aria-label={`Ask a question about ${selectedEtf?.ticker || 'VAS'}`}
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
              placeholder={`Ask anything about ${selectedEtf?.ticker || 'VAS'} (or 'build a plot with this years return percentage')...`}
              rows={2}
              value={question}
            />
            <div className="composer-tools">
              <span className="composer-hint">Press Enter to send · Shift+Enter for new line</span>
              <button
                aria-label={loading ? 'Searching' : 'Send question'}
                className="send-button"
                disabled={loading || !question.trim()}
                type="submit"
              >
                {loading ? <span className="button-spinner" /> : <SendIcon size={14} />}
              </button>
            </div>
          </form>
          <p className="disclaimer">
            ClariFi Research Terminal · Sourced strictly from Vanguard Australia Product Disclosure Statements (PDS) & Regulatory Filings.
          </p>
        </footer>
      </main>

      {/* 3. Task 3 Dual-Mode Visualizer (Right Panel) */}
      <Visualizer
        isOpen={isVisualizerOpen}
        onClose={() => setIsVisualizerOpen(false)}
        mode={visualizerMode}
        activeCitation={activeCitation}
        activeChart={activeChart}
        isExpanded={isVisualizerExpanded}
        onToggleExpand={() => setIsVisualizerExpanded((prev) => !prev)}
        allCitations={allThreadCitations}
        onSelectCitation={(c) => setActiveCitation(c)}
        theme={theme}
      />

      {/* 4. Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        systemStats={systemStats}
        statsError={statsError}
        onOpenTour={() => {
          setIsSettingsOpen(false)
          setIsTourOpen(true)
        }}
        theme={theme}
        onToggleTheme={toggleTheme}
        font={font}
        onSelectFont={setFont}
        landingVariant={landingVariant}
        onSelectLandingVariant={setLandingVariant}
      />

      {/* 5. 6-Card Feature Tour Slideshow Modal */}
      <FeatureTourModal
        isOpen={isTourOpen}
        theme={theme}
        onClose={() => setIsTourOpen(false)}
        onSelectQuestion={(q) => {
          askQuestion(null, q)
        }}
        onOpenSettings={() => {
          setIsTourOpen(false)
          setIsSettingsOpen(true)
        }}
      />
    </div>
  )
}
