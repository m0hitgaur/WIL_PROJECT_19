import React, { useState, useEffect } from 'react'
import { formatDocTitle } from '../utils/formatters'
import { BarChartIcon, FileTextIcon, ExternalLinkIcon } from './Icons'
import MarkdownRenderer from './MarkdownRenderer'

export default function ChatMessage({
  msg,
  isLatest,
  isNewlyGenerated = false,
  activeCitation,
  isVisualizerOpen,
  visualizerMode,
  onOpenCitation,
  onOpenChart,
  onStageChange,
  onAnimationComplete,
}) {
  // Reveal stage: 0 = answer text only, 1 = reference/chart bubbles, 2 = evidence drawer
  // ONLY run progressive staged reveal if this message was newly generated in the active session.
  // Historical / loaded messages render immediately at full stage 2 with no delays.
  const [stage, setStage] = useState(() => (msg.role === 'assistant' && isNewlyGenerated ? 0 : 2))

  useEffect(() => {
    if (msg.role === 'assistant' && isNewlyGenerated && stage < 2) {
      const timer1 = setTimeout(() => {
        setStage(1)
        onStageChange?.()
      }, 420)

      const timer2 = setTimeout(() => {
        setStage(2)
        onStageChange?.()
        onAnimationComplete?.(msg.id)
      }, 880)

      return () => {
        clearTimeout(timer1)
        clearTimeout(timer2)
      }
    }
  }, [msg.role, isNewlyGenerated, stage, onStageChange, onAnimationComplete, msg.id])

  // User Message
  if (msg.role === 'user') {
    return (
      <div className={`user-message-wrapper ${isNewlyGenerated ? 'fade-in-up' : ''}`}>
        <div className="user-message">
          <p>{msg.content}</p>
        </div>
        {msg.timestamp && <span className="message-meta">{msg.timestamp}</span>}
      </div>
    )
  }

  // Determine effective citations: use explicit citations or synthesize from sources
  const effectiveCitations =
    msg.citations && msg.citations.length > 0
      ? msg.citations
      : (msg.sources || []).map((s, idx) => ({
          chunk_id: s.chunk_id || `chunk-${idx}`,
          doc_title: s.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
          page: Number(s.page || (s.page_numbers && s.page_numbers[0]) || 1),
          quote: s.quote || s.text || '',
          pdf_url:
            s.pdf_url ||
            `/api/pdf/${s.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf'}#page=${Number(s.page || (s.page_numbers && s.page_numbers[0]) || 1)}`,
        }))

  return (
    <article className={`assistant-message ${msg.error ? 'is-error' : ''} ${isNewlyGenerated ? 'fade-in-up' : ''}`}>
      <div className="assistant-avatar" aria-hidden="true">
        C
      </div>
      <div className="assistant-content">
        <p className="assistant-name">ClariFi Research Assistant</p>

        {/* Step 1: Answer Text (Revealed first) */}
        <div className={`answer-text ${isNewlyGenerated ? 'fade-in-up' : ''}`}>
          <MarkdownRenderer content={msg.content} />
        </div>

        {/* Step 2: Chart Bubble / Reference Bubbles (Revealed second with smooth animation) */}
        {stage >= 1 && (
          <div className={`progressive-step ${isNewlyGenerated ? 'fade-in-up' : ''}`}>
            {/* Chart Launch Bubble */}
            {msg.chartData && (
              <div>
                <button
                  type="button"
                  className="chart-launch-bubble"
                  onClick={() => onOpenChart(msg.chartData)}
                  title="Click to launch the interactive Return Plot in the Visualizer"
                >
                  <BarChartIcon size={14} className="chart-bubble-icon" />
                  <span className="chart-bubble-title">Launch Return Plot Visualizer</span>
                  <span className="chart-bubble-tag">Interactive Chart</span>
                  <ExternalLinkIcon size={12} className="chart-bubble-arrow" />
                </button>
              </div>
            )}

            {/* Reference Bubbles underneath response */}
            {effectiveCitations.length > 0 && (
              <div className="reference-bubbles-container">
                <span className="reference-label">Referenced Sources</span>
                <div className="reference-bubbles">
                  {effectiveCitations.map((c, i) => (
                    <button
                      key={c.chunk_id || i}
                      type="button"
                      className={`reference-bubble ${
                        activeCitation?.chunk_id === c.chunk_id &&
                        isVisualizerOpen &&
                        visualizerMode === 'pdf'
                          ? 'active'
                          : ''
                      }`}
                      onClick={() => onOpenCitation(c)}
                      title={`Click to inspect in Visualizer: ${c.doc_title} (Page ${c.page})`}
                    >
                      <FileTextIcon size={12} className="bubble-icon" />
                      <span className="bubble-title">{formatDocTitle(c.doc_title)}</span>
                      <span className="bubble-page">Page {c.page}</span>
                      <ExternalLinkIcon size={11} className="bubble-indicator" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Retrieved Evidence Drawer (Revealed third with smooth animation) */}
        {stage >= 2 && msg.sources && msg.sources.length > 0 && (
          <div className={`progressive-step ${isNewlyGenerated ? 'fade-in-up' : ''}`}>
            <details className="evidence-details">
              <summary>
                Regulatory Evidence Excerpts ({msg.sources.length})
              </summary>
              <div className="evidence-list">
                {msg.sources.map((source, index) => {
                  const sourceCite = {
                    chunk_id: source.chunk_id || `chunk-${index}`,
                    doc_title: source.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
                    page: Number(source.page || (source.page_numbers && source.page_numbers[0]) || 1),
                    quote: source.quote || source.text || '',
                    pdf_url:
                      source.pdf_url ||
                      `/api/pdf/${source.doc_title || 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf'}#page=${Number(source.page || (source.page_numbers && source.page_numbers[0]) || 1)}`,
                  }

                  return (
                    <div
                      className="evidence-item clickable-evidence"
                      key={source.chunk_id || index}
                      onClick={() => onOpenCitation(sourceCite)}
                      title="Click to open and highlight this excerpt in the PDF Visualizer"
                    >
                      <div className="evidence-item-header">
                        <strong>
                          Page {source.page_numbers?.join(', ') || source.page || 1} · Chunk{' '}
                          {source.chunk_id || `chunk-${index}`}
                        </strong>
                        <button
                          type="button"
                          className="evidence-inspect-btn"
                          onClick={(e) => {
                            e.stopPropagation()
                            onOpenCitation(sourceCite)
                          }}
                        >
                          <span>Inspect in PDF</span>
                          <ExternalLinkIcon size={11} />
                        </button>
                      </div>
                      <p>{source.text}</p>
                    </div>
                  )
                })}
              </div>
            </details>
          </div>
        )}

        {msg.timestamp && <span className="message-meta">{msg.timestamp}</span>}
      </div>
    </article>
  )
}
