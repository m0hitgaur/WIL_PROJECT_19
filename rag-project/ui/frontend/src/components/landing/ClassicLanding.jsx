import React from 'react'
import { LayersIcon, ChevronRightIcon, ExternalLinkIcon } from '../Icons'

export default function ClassicLanding({
  theme = 'dark',
  onOpenTour,
  onSelectQuestion,
  suggestedQuestions = [],
}) {
  return (
    <div className="welcome">
      <div className="welcome-logo-badge">
        <img
          src={theme === 'light' ? '/brand/clarifi-logo-no-bg.png' : '/brand/clarifi-w-logo-no-bg.png'}
          alt="ClariFi"
          className="welcome-logo-img"
        />
      </div>
      <p className="eyebrow">VERIFIABLE ETF RESEARCH</p>
      <h1>Good questions deserve<br />grounded answers.</h1>
      <p className="welcome-copy">
        Ask about VAS fees, benchmarks, or distributions. Every response is verified
        against official Vanguard disclosure documents with mathematical provenance.
      </p>

      {onOpenTour && (
        <button
          type="button"
          className="welcome-tour-cta"
          onClick={onOpenTour}
        >
          <LayersIcon size={15} />
          <span>Explore ClariFi Feature Slideshow (6 Cards)</span>
          <ChevronRightIcon size={14} />
        </button>
      )}

      {suggestedQuestions.length > 0 && (
        <div className="suggestions">
          {suggestedQuestions.map((item) => (
            <button
              className="suggestion-card"
              key={item.question}
              onClick={() => onSelectQuestion?.(item.question)}
              type="button"
            >
              <span className="suggestion-icon" aria-hidden="true">
                {item.icon}
              </span>
              <strong>{item.title}</strong>
              <small>{item.question}</small>
              <span className="suggestion-arrow" aria-hidden="true">
                <ExternalLinkIcon size={12} />
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
