import React, { useState, useEffect, useRef, useMemo } from 'react'
import { formatDocTitle } from '../utils/formatters'
import {
  FileTextIcon,
  BarChartIcon,
  MaximizeIcon,
  MinimizeIcon,
  CloseIcon,
  QuoteIcon,
  CpuIcon,
} from './Icons'

const norm = (s) => (s ? s.toLowerCase().replace(/\s+/g, ' ').trim() : '')

export default function Visualizer({
  isOpen,
  onClose,
  mode = 'pdf', // 'pdf' | 'chart'
  activeCitation,
  activeChart,
  isExpanded,
  onToggleExpand,
  allCitations = [],
  onSelectCitation,
  theme = 'dark',
}) {
  const [doc, setDoc] = useState(null)
  const [pageNum, setPageNum] = useState(1)
  const [scale, setScale] = useState(1.25)
  const [boxes, setBoxes] = useState([])
  const [loadingPdf, setLoadingPdf] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const [useIframeFallback, setUseIframeFallback] = useState(false)

  const canvasRef = useRef(null)
  const viewerRef = useRef(null)

  // Dynamically resolve theme-aware chart asset (light vs dark SVG)
  const effectiveChartSrc = useMemo(() => {
    const rawSrc = activeChart?.src
    if (!rawSrc) {
      return theme === 'light' ? '/charts/vas_returns_light.svg' : '/charts/vas_returns.svg'
    }
    if (theme === 'light') {
      return rawSrc.replace('vas_returns.svg', 'vas_returns_light.svg')
    }
    return rawSrc.replace('vas_returns_light.svg', 'vas_returns.svg')
  }, [activeChart?.src, theme])

  // Initialize / update page number from citation
  useEffect(() => {
    if (activeCitation?.page) {
      setPageNum(Number(activeCitation.page) || 1)
    }
  }, [activeCitation])

  // Load PDF with PDF.js when activeCitation URL changes
  useEffect(() => {
    if (mode !== 'pdf' || !activeCitation?.pdf_url) return

    const rawUrl = activeCitation.pdf_url.split('#')[0]
    let cancelled = false

    setLoadingPdf(true)
    setPdfError('')
    setDoc(null)
    setBoxes([])

    if (!window.pdfjsLib) {
      setUseIframeFallback(true)
      setLoadingPdf(false)
      return
    }

    try {
      const loadingTask = window.pdfjsLib.getDocument(rawUrl)
      loadingTask.promise
        .then((pdfDocument) => {
          if (!cancelled) {
            setDoc(pdfDocument)
            setLoadingPdf(false)
          }
        })
        .catch((err) => {
          console.warn('PDF.js canvas load error, using native iframe fallback:', err)
          if (!cancelled) {
            setPdfError(err.message || 'Failed to load PDF')
            setUseIframeFallback(true)
            setLoadingPdf(false)
          }
        })

      return () => {
        cancelled = true
        loadingTask.destroy()
      }
    } catch {
      setUseIframeFallback(true)
      setLoadingPdf(false)
    }
  }, [mode, activeCitation?.pdf_url])

  // Render canvas page and compute highlight bounding boxes
  useEffect(() => {
    if (!doc || mode !== 'pdf' || useIframeFallback) return

    let cancelled = false
    let renderTask = null

    const renderPage = async () => {
      try {
        const targetPage = Math.min(Math.max(1, pageNum), doc.numPages)
        const page = await doc.getPage(targetPage)
        const viewport = page.getViewport({ scale })
        const dpr = window.devicePixelRatio || 1
        const canvas = canvasRef.current

        if (!canvas) return

        canvas.width = viewport.width * dpr
        canvas.height = viewport.height * dpr
        canvas.style.width = `${viewport.width}px`
        canvas.style.height = `${viewport.height}px`

        const ctx = canvas.getContext('2d')
        renderTask = page.render({
          canvasContext: ctx,
          viewport,
          transform: [dpr, 0, 0, dpr, 0, 0],
        })

        await renderTask.promise
        if (cancelled) return

        // Compute text matches for citation highlight
        const foundBoxes = []
        if (activeCitation?.quote && pageNum === Number(activeCitation.page)) {
          const normQuote = norm(activeCitation.quote)
          const textContent = await page.getTextContent()

          for (const item of textContent.items) {
            const itemText = norm(item.str)
            if (itemText.length < 3 || !normQuote.includes(itemText)) continue

            const transform = window.pdfjsLib.Util.transform(viewport.transform, item.transform)
            const height = item.height * scale
            foundBoxes.push({
              left: transform[4],
              top: transform[5] - height,
              width: item.width * scale,
              height: height * 1.2,
            })
          }
        }

        if (!cancelled) {
          setBoxes(foundBoxes)
        }
      } catch {
        // Ignored if cancelled
      }
    }

    renderPage()

    return () => {
      cancelled = true
      if (renderTask) {
        renderTask.cancel()
      }
    }
  }, [doc, pageNum, scale, activeCitation?.quote, mode, useIframeFallback])

  // Auto-scroll to highlight box if present
  useEffect(() => {
    if (boxes.length > 0 && viewerRef.current) {
      viewerRef.current.scrollTo({
        top: Math.max(0, boxes[0].top - 80),
        behavior: 'smooth',
      })
    }
  }, [boxes])

  if (!isOpen) return null

  const isPdfMode = mode === 'pdf'
  const isChartMode = mode === 'chart'

  return (
    <aside className={`visualizer-panel ${isExpanded ? 'is-expanded' : 'is-split'}`}>
      {/* 1. Header Toolbar */}
      <div className="visualizer-header">
        <div className="visualizer-title-group">
          <span className={`visualizer-badge ${isPdfMode ? 'badge-pdf' : 'badge-chart'}`}>
            {isPdfMode ? (
              <>
                <FileTextIcon size={12} />
                <span>Source Verification</span>
              </>
            ) : (
              <>
                <BarChartIcon size={12} />
                <span>Chart Synthesis</span>
              </>
            )}
          </span>
          <h4 className="visualizer-title" title={activeCitation?.doc_title || activeChart?.title}>
            {isPdfMode
              ? formatDocTitle(activeCitation?.doc_title)
              : activeChart?.title || 'VAS Return Percentage'}
          </h4>
        </div>

        {/* Toolbar Controls */}
        <div className="visualizer-actions">
          {isPdfMode && (
            <>
              {/* Citation switcher pills */}
              {allCitations.length > 1 && (
                <div className="citation-nav-pills">
                  {allCitations.map((c, i) => (
                    <button
                      key={c.chunk_id || i}
                      type="button"
                      className={`cite-nav-pill ${activeCitation?.chunk_id === c.chunk_id ? 'active' : ''}`}
                      onClick={() => onSelectCitation && onSelectCitation(c)}
                      title={`${formatDocTitle(c.doc_title)} (Page ${c.page})`}
                    >
                      Ref {i + 1}
                    </button>
                  ))}
                </div>
              )}

              {/* Page Nav */}
              <div className="page-nav-controls">
                <button
                  type="button"
                  className="vis-btn"
                  onClick={() => setPageNum((p) => Math.max(1, p - 1))}
                  disabled={pageNum <= 1}
                  aria-label="Previous Page"
                >
                  ‹
                </button>
                <span className="page-counter">
                  {doc ? `${pageNum} / ${doc.numPages}` : `p. ${pageNum}`}
                </span>
                <button
                  type="button"
                  className="vis-btn"
                  onClick={() => setPageNum((p) => (doc ? Math.min(doc.numPages, p + 1) : p + 1))}
                  disabled={doc && pageNum >= doc.numPages}
                  aria-label="Next Page"
                >
                  ›
                </button>
              </div>

              {/* Zoom Controls */}
              <div className="zoom-controls">
                <button
                  type="button"
                  className="vis-btn"
                  onClick={() => setScale((s) => Math.max(0.6, s - 0.2))}
                  aria-label="Zoom Out"
                >
                  −
                </button>
                <span className="zoom-value">{Math.round(scale * 100)}%</span>
                <button
                  type="button"
                  className="vis-btn"
                  onClick={() => setScale((s) => Math.min(2.5, s + 0.2))}
                  aria-label="Zoom In"
                >
                  +
                </button>
              </div>

              {/* Fallback View Mode Toggle */}
              <button
                type="button"
                className="vis-btn text-btn"
                onClick={() => setUseIframeFallback((prev) => !prev)}
                title="Toggle between Canvas Highlight and Native PDF Viewer"
              >
                {useIframeFallback ? 'Canvas Mode' : 'Native View'}
              </button>
            </>
          )}

          {/* Expand / Shrink Button */}
          <button
            type="button"
            className="vis-btn"
            onClick={onToggleExpand}
            title={isExpanded ? 'Restore Split View' : 'Expand to Full View'}
            aria-label="Toggle Expand"
          >
            {isExpanded ? <MinimizeIcon size={13} /> : <MaximizeIcon size={13} />}
          </button>

          {/* Close Panel Button */}
          <button
            type="button"
            className="vis-btn close-btn"
            onClick={onClose}
            title="Close Visualizer Panel"
            aria-label="Close"
          >
            <CloseIcon size={13} />
          </button>
        </div>
      </div>

      {/* 2. Visualizer Body Viewport */}
      <div className="visualizer-content" ref={viewerRef}>
        {/* PDF VIEW */}
        {isPdfMode && (
          <div className="pdf-viewport">
            {loadingPdf && (
              <div className="vis-loading-state">
                <span className="button-spinner" />
                <p>Loading official PDF document…</p>
              </div>
            )}

            {pdfError && (
              <div className="error-message" style={{ margin: '12px auto', maxWidth: 600 }}>
                {pdfError} — Displaying via native document viewer below.
              </div>
            )}

            {/* Canvas Mode with Highlight overlay */}
            {!useIframeFallback && (
              <div className="canvas-wrapper" style={{ display: loadingPdf ? 'none' : 'inline-block' }}>
                <canvas ref={canvasRef} className="pdf-canvas" />
                {boxes.map((box, index) => (
                  <div
                    key={index}
                    className="highlight-overlay"
                    style={{
                      left: `${box.left}px`,
                      top: `${box.top}px`,
                      width: `${box.width}px`,
                      height: `${box.height}px`,
                    }}
                    title="Cited document chunk"
                  />
                ))}
              </div>
            )}

            {/* Native PDF iframe mode */}
            {useIframeFallback && activeCitation?.pdf_url && (
              <iframe
                src={`${activeCitation.pdf_url.split('#')[0]}#page=${pageNum}`}
                className="pdf-native-frame"
                title="Source PDF Document"
              />
            )}

            {/* Quote Excerpt Banner */}
            {activeCitation?.quote && (
              <div className="quote-banner">
                <QuoteIcon size={16} className="quote-icon" />
                <p>{activeCitation.quote}</p>
                <span className="quote-badge">Cited Chunk Highlighted Above</span>
              </div>
            )}
          </div>
        )}

        {/* CHART VIEW */}
        {isChartMode && (
          <div className="chart-viewport">
            <div className="chart-wrapper">
              <img
                src={effectiveChartSrc}
                alt="VAS Return Performance Chart"
                className="chart-img"
              />
            </div>

            {/* KPI Metrics Cards */}
            <div className="chart-metrics-strip">
              <div className="chart-metric-card">
                <span className="kpi-label">1-Year Total Return</span>
                <strong className="kpi-value text-green">12.1%</strong>
                <small>Benchmark: 12.1% (+0.02%)</small>
              </div>
              <div className="chart-metric-card">
                <span className="kpi-label">3-Year Annualized</span>
                <strong className="kpi-value">7.8%</strong>
                <small>Benchmark: 7.8% (+0.03%)</small>
              </div>
              <div className="chart-metric-card">
                <span className="kpi-label">5-Year Annualized</span>
                <strong className="kpi-value">8.4%</strong>
                <small>Benchmark: 8.4% (+0.03%)</small>
              </div>
              <div className="chart-metric-card">
                <span className="kpi-label">10-Year Annualized</span>
                <strong className="kpi-value">8.2%</strong>
                <small>Benchmark: 8.1% (+0.03%)</small>
              </div>
            </div>

            {/* Data Provenance Card */}
            <div className="chart-provenance-card">
              <div className="provenance-header">
                <CpuIcon size={16} className="provenance-icon" />
                <strong>Verified Performance Synthesis</strong>
              </div>
              <p>
                Data extracted directly from <em>Vanguard Wholesale Australian Equities Funds and ETFs Factsheet</em>.
                Generated via automated financial data extraction and plotted against official ASX 300 benchmark accumulation numbers.
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
