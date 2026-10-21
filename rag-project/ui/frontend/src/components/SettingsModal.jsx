import React, { useEffect } from 'react'
import { SettingsIcon, CloseIcon, MoonIcon, SunIcon } from './Icons'

export default function SettingsModal({
  isOpen,
  onClose,
  systemStats,
  statsError,
  onOpenTour,
  theme,
  onToggleTheme,
  font = 'inter',
  onSelectFont,
  landingVariant = 'minimal',
  onSelectLandingVariant,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-container settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <SettingsIcon size={20} className="modal-icon" />
            <div>
              <h3>System Settings & Telemetry</h3>
              <p className="modal-subtitle">Engine configuration and knowledge graph metrics</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close settings">
            <CloseIcon size={14} />
          </button>
        </div>

        <div className="modal-body settings-body">
          {/* Section 1: System Connection */}
          <div className="settings-section">
            <h4 className="section-title">DATABASE CONNECTIVITY</h4>
            <div className="status-grid">
              <div className="status-card">
                <div className="status-header">
                  <span className={`status-indicator ${systemStats?.neo4j?.connected ? 'online' : 'offline'}`} />
                  <strong>Neo4j Graph Database</strong>
                </div>
                <div className="status-detail">
                  <span>Connection:</span>
                  <strong>{systemStats?.neo4j?.connected ? 'Online (Active)' : statsError || 'Unavailable'}</strong>
                </div>
                {systemStats?.neo4j?.server_agent && (
                  <div className="status-detail">
                    <span>Engine:</span>
                    <code>{systemStats.neo4j.server_agent}</code>
                  </div>
                )}
                <div className="status-detail">
                  <span>APOC Extension:</span>
                  <strong>{systemStats?.neo4j?.apoc_installed ? 'Installed & Enabled' : 'Not Detected'}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Model Stack */}
          <div className="settings-section">
            <h4 className="section-title">AI MODEL ARCHITECTURE</h4>
            <div className="model-grid">
              <div className="model-card">
                <span className="model-tag">LLM INFERENCE</span>
                <h4>{systemStats?.models?.llm || 'gemma4:e4b'}</h4>
                <p>Local Ollama model tuned for grounded financial question-answering.</p>
              </div>
              <div className="model-card">
                <span className="model-tag">EMBEDDINGS</span>
                <h4>{systemStats?.models?.embeddings || 'qwen3-embedding:4b'}</h4>
                <p>{systemStats?.models?.embedding_dim || 2560} dimensions · Dense semantic vector indexing.</p>
              </div>
              <div className="model-card">
                <span className="model-tag">VISION-LANGUAGE</span>
                <h4>{systemStats?.models?.vlm || 'qwen2.5-vl:7b'}</h4>
                <p>Dedicated multimodal parsing for financial tables & PDF figures.</p>
              </div>
            </div>
          </div>

          {/* Section 3: Knowledge Graph Metrics */}
          <div className="settings-section">
            <h4 className="section-title">KNOWLEDGE GRAPH STATISTICS</h4>
            <div className="metrics-grid">
              <div className="metric-box">
                <span className="metric-val">{systemStats?.metrics?.documents ?? 1}</span>
                <span className="metric-lbl">Indexed Documents</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{systemStats?.metrics?.chunks ?? 49}</span>
                <span className="metric-lbl">Text Chunks</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{systemStats?.metrics?.tables ?? 2}</span>
                <span className="metric-lbl">Extracted Tables</span>
              </div>
              <div className="metric-box">
                <span className="metric-val">{systemStats?.metrics?.edges ?? 12}</span>
                <span className="metric-lbl">Graph Relationships</span>
              </div>
            </div>
          </div>

          {/* Section 4: Appearance & Typography Preferences */}
          <div className="settings-section">
            <h4 className="section-title">INTERFACE & APPEARANCE</h4>

            {/* Appearance Theme */}
            <div className="pref-row">
              <div className="pref-info">
                <strong>Color Palette</strong>
                <p>Switch between ClariFi Dark (Obsidian) and ClariFi Light (Institutional Slate).</p>
              </div>
              <div className="theme-segmented-group" role="radiogroup" aria-label="Theme mode">
                <button
                  type="button"
                  className={`theme-segment-btn ${theme === 'dark' ? 'is-active' : ''}`}
                  onClick={() => theme !== 'dark' && onToggleTheme && onToggleTheme()}
                >
                  <MoonIcon size={14} className="segment-icon" />
                  <span>Dark</span>
                </button>
                <button
                  type="button"
                  className={`theme-segment-btn ${theme === 'light' ? 'is-active' : ''}`}
                  onClick={() => theme !== 'light' && onToggleTheme && onToggleTheme()}
                >
                  <SunIcon size={14} className="segment-icon" />
                  <span>Light</span>
                </button>
              </div>
            </div>

            {/* Chat Landing Screen Variant */}
            {onSelectLandingVariant && (
              <div className="pref-row">
                <div className="pref-info">
                  <strong>Landing Screen Layout</strong>
                  <p>Choose between the minimal looping video mark and the classic cards overview.</p>
                </div>
                <div className="theme-segmented-group" role="radiogroup" aria-label="Landing page style">
                  <button
                    type="button"
                    className={`theme-segment-btn ${landingVariant === 'minimal' ? 'is-active' : ''}`}
                    onClick={() => onSelectLandingVariant('minimal')}
                  >
                    <span>Minimal Video</span>
                  </button>
                  <button
                    type="button"
                    className={`theme-segment-btn ${landingVariant === 'classic' ? 'is-active' : ''}`}
                    onClick={() => onSelectLandingVariant('classic')}
                  >
                    <span>Classic Cards</span>
                  </button>
                </div>
              </div>
            )}

            {/* Typography / Font Decision & Selection */}
            <div className="pref-row font-pref-block">
              <div className="pref-info">
                <strong>Typography & Font Decision</strong>
                <p>
                  Standardized on <strong>Inter</strong> with OpenType tabular figures (<code>tnum</code>) and contextual alternates (<code>cv02, cv03</code>) for optimal financial legibility.
                </p>
              </div>

              {onSelectFont && (
                <div className="font-options-grid">
                  <button
                    type="button"
                    className={`font-option-card ${font === 'inter' ? 'is-active' : ''}`}
                    onClick={() => onSelectFont('inter')}
                  >
                    <div className="font-option-header">
                      <strong>Inter (Recommended)</strong>
                      {font === 'inter' && <span className="font-active-badge">Active</span>}
                    </div>
                    <span className="font-spec">OpenType Tabular · High-density readability</span>
                    <div className="font-preview-pill" style={{ fontFamily: 'Inter, sans-serif' }}>
                      VAS +12.1% · $84.20 · PDS Page 4
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`font-option-card ${font === 'jakarta' ? 'is-active' : ''}`}
                    onClick={() => onSelectFont('jakarta')}
                  >
                    <div className="font-option-header">
                      <strong>Plus Jakarta Sans</strong>
                      {font === 'jakarta' && <span className="font-active-badge">Active</span>}
                    </div>
                    <span className="font-spec">Executive Sans · Corporate clarity</span>
                    <div className="font-preview-pill" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                      VAS +12.1% · $84.20 · PDS Page 4
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`font-option-card ${font === 'mono' ? 'is-active' : ''}`}
                    onClick={() => onSelectFont('mono')}
                  >
                    <div className="font-option-header">
                      <strong>JetBrains Mono</strong>
                      {font === 'mono' && <span className="font-active-badge">Active</span>}
                    </div>
                    <span className="font-spec">Quantitative · Fixed-width terminal</span>
                    <div className="font-preview-pill" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      VAS +12.1% · $84.20 · PDS Page 4
                    </div>
                  </button>
                </div>
              )}
            </div>

            {/* Product Tour shortcut */}
            <div className="action-row">
              <div className="action-info">
                <strong>ClariFi Feature Tour</strong>
                <p>Revisit the 6-step interactive presentation showcasing RAG capabilities.</p>
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  onClose()
                  onOpenTour()
                }}
              >
                Launch Feature Tour
              </button>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <span className="engine-badge">ClariFi Agent v1.0 · Port 8000</span>
          <button className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
