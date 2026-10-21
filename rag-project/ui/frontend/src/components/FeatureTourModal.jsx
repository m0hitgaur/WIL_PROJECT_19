import React, { useState, useEffect } from 'react'
import {
  CloseIcon,
  CoinsIcon,
  TrendingUpIcon,
  CalendarIcon,
  BarChartIcon,
  FileTextIcon,
  DatabaseIcon,
  ActivityIcon,
  ExternalLinkIcon,
} from './Icons'

export default function FeatureTourModal({
  isOpen,
  theme = 'dark',
  onClose,
  onSelectQuestion,
  onOpenSettings,
}) {
  const [currentSlide, setCurrentSlide] = useState(0)

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') handleNext()
      if (e.key === 'ArrowLeft') handlePrev()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, currentSlide])

  if (!isOpen) return null

  const totalSlides = 6

  const handleNext = () => {
    if (currentSlide < totalSlides - 1) {
      setCurrentSlide((prev) => prev + 1)
    } else {
      onClose()
    }
  }

  const handlePrev = () => {
    if (currentSlide > 0) {
      setCurrentSlide((prev) => prev - 1)
    }
  }

  const handlePickQuestion = (q) => {
    onSelectQuestion(q)
    onClose()
  }

  return (
    <div className="modal-backdrop tour-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-container tour-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header with Progress */}
        <div className="tour-modal-header">
          <div className="tour-step-badge">
            Step {currentSlide + 1} of {totalSlides}
          </div>
          <div className="tour-dots">
            {Array.from({ length: totalSlides }).map((_, index) => (
              <button
                key={index}
                className={`tour-dot ${index === currentSlide ? 'active' : ''}`}
                onClick={() => setCurrentSlide(index)}
                aria-label={`Jump to slide ${index + 1}`}
              />
            ))}
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close tour">
            <CloseIcon size={14} />
          </button>
        </div>

        {/* Slide Contents */}
        <div className="tour-slide-viewport">
          {/* SLIDE 1: Welcome to ClariFi */}
          {currentSlide === 0 && (
            <div className="tour-slide slide-welcome">
              <div className="tour-media-box">
                <video autoPlay loop muted playsInline className="tour-animated-logo">
                  <source src="/brand/clarifi-w.mp4" type="video/mp4" />
                  <img
                    src={theme === 'light' ? '/brand/clarifi-logo-no-bg.png' : '/brand/clarifi-w-logo-no-bg.png'}
                    alt="ClariFi Logo"
                    className="tour-static-logo"
                  />
                </video>
              </div>
              <p className="tour-eyebrow">INTELLIGENT FINANCIAL RESEARCH</p>
              <h2 className="tour-title">Welcome to ClariFi</h2>
              <p className="tour-copy">
                Good financial decisions demand verifiable clarity. ClariFi is an agentic RAG assistant
                engineered specifically for Vanguard ETFs, grounding every answer in official product disclosure
                statements, annual reports, and regulatory filings.
              </p>
              <div className="feature-badges">
                <span className="pill-badge">
                  <ActivityIcon size={12} /> LangGraph Orchestration
                </span>
                <span className="pill-badge">
                  <DatabaseIcon size={12} /> Neo4j Knowledge Graph
                </span>
                <span className="pill-badge">
                  <FileTextIcon size={12} /> High-Fidelity PDF Grounding
                </span>
              </div>
            </div>
          )}

          {/* SLIDE 2: Use Cases / Starter Questions */}
          {currentSlide === 1 && (
            <div className="tour-slide slide-usecases">
              <p className="tour-eyebrow">CORE CAPABILITIES</p>
              <h2 className="tour-title">Use Cases & Starter Inquiries</h2>
              <p className="tour-copy">
                Select a sample prompt below to inspect how ClariFi extracts exact disclosures and maps evidence:
              </p>

              <div className="tour-question-grid">
                <button
                  type="button"
                  className="tour-question-card"
                  onClick={() => handlePickQuestion('What are the management fees?')}
                >
                  <span className="card-icon">
                    <CoinsIcon size={18} />
                  </span>
                  <div className="card-text">
                    <strong>Understand Fund Fees</strong>
                    <small>“What are the management fees?”</small>
                  </div>
                  <ExternalLinkIcon size={12} className="card-arrow" />
                </button>

                <button
                  type="button"
                  className="tour-question-card"
                  onClick={() => handlePickQuestion('What index does VAS track?')}
                >
                  <span className="card-icon">
                    <TrendingUpIcon size={18} />
                  </span>
                  <div className="card-text">
                    <strong>Index & Benchmark</strong>
                    <small>“What index does VAS track?”</small>
                  </div>
                  <ExternalLinkIcon size={12} className="card-arrow" />
                </button>

                <button
                  type="button"
                  className="tour-question-card"
                  onClick={() => handlePickQuestion('How often are distributions paid?')}
                >
                  <span className="card-icon">
                    <CalendarIcon size={18} />
                  </span>
                  <div className="card-text">
                    <strong>Distributions Schedule</strong>
                    <small>“How often are distributions paid?”</small>
                  </div>
                  <ExternalLinkIcon size={12} className="card-arrow" />
                </button>

                <button
                  type="button"
                  className="tour-question-card"
                  onClick={() => handlePickQuestion('build a plot with this years return percentage')}
                >
                  <span className="card-icon">
                    <BarChartIcon size={18} />
                  </span>
                  <div className="card-text">
                    <strong>Visual Return Plotting</strong>
                    <small>“build a plot with this years return percentage”</small>
                  </div>
                  <ExternalLinkIcon size={12} className="card-arrow" />
                </button>
              </div>
            </div>
          )}

          {/* SLIDE 3: Feature 1: Graph Database & Self Healing */}
          {currentSlide === 2 && (
            <div className="tour-slide slide-feature">
              <p className="tour-eyebrow">ARCHITECTURE</p>
              <h2 className="tour-title">Graph Database & Self-Healing RAG</h2>
              <p className="tour-copy">
                Traditional RAG loses structural relationships across document sections. ClariFi builds an interconnected
                Neo4j Knowledge Graph connecting Documents, Chunks, and Financial Entities.
              </p>

              <div className="graph-animation-placeholder">
                <svg viewBox="0 0 500 180" className="graph-svg">
                  {/* Edges */}
                  <line x1="80" y1="90" x2="210" y2="45" className="graph-edge pulse-edge" />
                  <line x1="80" y1="90" x2="210" y2="135" className="graph-edge pulse-edge" />
                  <line x1="210" y1="45" x2="350" y2="45" className="graph-edge pulse-edge" />
                  <line x1="210" y1="135" x2="350" y2="135" className="graph-edge pulse-edge" />
                  <line x1="350" y1="45" x2="440" y2="90" className="graph-edge heal-edge" />
                  <line x1="350" y1="135" x2="440" y2="90" className="graph-edge heal-edge" />

                  {/* Nodes */}
                  <g className="graph-node-group">
                    <circle cx="80" cy="90" r="28" className="node-doc" />
                    <text x="80" y="94" textAnchor="middle" className="node-label">Document</text>
                  </g>

                  <g className="graph-node-group">
                    <circle cx="210" cy="45" r="22" className="node-chunk" />
                    <text x="210" y="49" textAnchor="middle" className="node-label">Chunk A</text>
                  </g>

                  <g className="graph-node-group">
                    <circle cx="210" cy="135" r="22" className="node-chunk" />
                    <text x="210" y="139" textAnchor="middle" className="node-label">Chunk B</text>
                  </g>

                  <g className="graph-node-group">
                    <circle cx="350" cy="45" r="22" className="node-table" />
                    <text x="350" y="49" textAnchor="middle" className="node-label">VAS Table</text>
                  </g>

                  <g className="graph-node-group">
                    <circle cx="350" cy="135" r="22" className="node-fact" />
                    <text x="350" y="139" textAnchor="middle" className="node-label">Fee Node</text>
                  </g>

                  <g className="graph-node-group node-healing-pulse">
                    <circle cx="440" cy="90" r="26" className="node-agent" />
                    <text x="440" y="94" textAnchor="middle" className="node-label">Self-Heal</text>
                  </g>
                </svg>
              </div>

              <div className="tour-feature-highlights">
                <div>
                  <strong>Bi-directional Traversal</strong>
                  <span>Discovers related clauses across multiple ETF annual filings.</span>
                </div>
                <div>
                  <strong>Self-Healing Guardrails</strong>
                  <span>Hallucination grader verifies citation alignment before streaming answers.</span>
                </div>
              </div>
            </div>
          )}

          {/* SLIDE 4: Feature 2: Table Extraction */}
          {currentSlide === 3 && (
            <div className="tour-slide slide-feature">
              <p className="tour-eyebrow">VLM PIPELINE</p>
              <h2 className="tour-title">Multimodal Table Extraction</h2>
              <p className="tour-copy">
                Standard OCR scrambles dense financial tables. ClariFi executes high-resolution Vision-Language
                extraction (`Qwen2.5-VL`), converting raw PDF tabular blocks into clean structured data.
              </p>

              <div className="table-crop-placeholder">
                <div className="crop-preview-wrapper">
                  <img
                    src="/crops/ETF-Vanguard_Australian_Shares_Index_ETF_8205_FS_VAS_table_0.png"
                    alt="Extracted ETF table sample"
                    className="table-crop-img"
                    onError={(e) => {
                      e.target.style.display = 'none'
                    }}
                  />
                  <div className="scan-line-animation" />
                  <span className="crop-badge">VLM Parsed Table · Vanguard Factsheet</span>
                </div>
              </div>

              <div className="tour-feature-highlights">
                <div>
                  <strong>Aligned Column Geometry</strong>
                  <span>Preserves 1-year, 3-year, and 5-year annualized returns accurately.</span>
                </div>
                <div>
                  <strong>Direct Table Querying</strong>
                  <span>Enables numerical queries like total expense ratios and NAV without hallucination.</span>
                </div>
              </div>
            </div>
          )}

          {/* SLIDE 5: Feature 3: PDF Visualization & Chart Creation */}
          {currentSlide === 4 && (
            <div className="tour-slide slide-feature">
              <p className="tour-eyebrow">INTERACTIVE VISUALIZER</p>
              <h2 className="tour-title">PDF Grounding & Agentic Visualizations</h2>
              <p className="tour-copy">
                ClariFi combines instant source document verification with automated chart creation:
              </p>

              <div className="visualizer-mockup-grid">
                <div className="mockup-card">
                  <div className="mockup-header">
                    <span className="mockup-pill red">PDF Viewer</span>
                    <span>VAS PDS · Page 2</span>
                  </div>
                  <div className="mockup-body pdf-mockup-body">
                    <div className="mockup-text-line full" />
                    <div className="mockup-text-line hl-line">
                      <span>Highlighted Cited Text Chunk</span>
                    </div>
                    <div className="mockup-text-line three-quarter" />
                    <div className="mockup-text-line half" />
                  </div>
                  <small>Click any reference bubble to jump directly to the exact page & highlighted quote.</small>
                </div>

                <div className="mockup-card">
                  <div className="mockup-header">
                    <span className="mockup-pill blue">Chart Agent</span>
                    <span>VAS Annual Returns</span>
                  </div>
                  <div className="mockup-body chart-mockup-body">
                    <div className="chart-bar-mock b1" style={{ height: '40%' }}><span>2022</span></div>
                    <div className="chart-bar-mock b2" style={{ height: '68%' }}><span>2023</span></div>
                    <div className="chart-bar-mock b3" style={{ height: '88%' }}><span>2024</span></div>
                  </div>
                  <small>Request visualizations from tabular data and view responsive charts side-by-side.</small>
                </div>
              </div>
            </div>
          )}

          {/* SLIDE 6: Get Started */}
          {currentSlide === 5 && (
            <div className="tour-slide slide-get-started">
              <div className="tour-badge-circle">
                <TrendingUpIcon size={24} />
              </div>
              <p className="tour-eyebrow">READY FOR RESEARCH</p>
              <h2 className="tour-title">Start Exploring ClariFi</h2>
              <p className="tour-copy">
                The full Vanguard Australian Shares Index ETF (VAS) knowledge base is loaded and indexed.
                Ask any question about investment objectives, risk factors, or historical distributions.
              </p>

              <div className="get-started-actions">
                <button
                  type="button"
                  className="btn-primary btn-large"
                  onClick={onClose}
                >
                  Start Exploring VAS
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    onClose()
                    onOpenSettings()
                  }}
                >
                  Review System Telemetry
                </button>
              </div>

              <p className="tour-disclaimer">
                ClariFi operates with 100% citation grounding. For information and educational research only.
              </p>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="tour-modal-footer">
          <button
            type="button"
            className="btn-ghost"
            onClick={onClose}
          >
            Skip Tour
          </button>

          <div className="tour-nav-buttons">
            <button
              type="button"
              className="btn-secondary"
              disabled={currentSlide === 0}
              onClick={handlePrev}
            >
              ‹ Back
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleNext}
            >
              {currentSlide === totalSlides - 1 ? 'Get Started' : 'Next ›'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
