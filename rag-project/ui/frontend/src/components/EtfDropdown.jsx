import React, { useState, useRef, useEffect } from 'react'
import { ChevronDownIcon } from './Icons'

export const VANGUARD_ETFS = [
  {
    ticker: 'VAS',
    asxCode: 'ASX: VAS',
    name: 'Vanguard Australian Shares Index ETF',
    shortName: 'Australian Shares',
    benchmark: 'S&P/ASX 300 Index',
    pdsDoc: 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
    description: 'Tracks the S&P/ASX 300, providing low-cost exposure to the top 300 companies on the ASX.',
  },
  {
    ticker: 'VHY',
    asxCode: 'ASX: VHY',
    name: 'Vanguard Australian Shares High Yield ETF',
    shortName: 'Australian High Yield',
    benchmark: 'FTSE Australia High Dividend Yield Index',
    pdsDoc: 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
    description: 'Targeted exposure to higher-yielding Australian companies with dividend focus.',
  },
  {
    ticker: 'VAP',
    asxCode: 'ASX: VAP',
    name: 'Vanguard Australian Property Securities Index ETF',
    shortName: 'Australian Property',
    benchmark: 'S&P/ASX 300 A-REIT Index',
    pdsDoc: 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
    description: 'Direct exposure to Australian listed Real Estate Investment Trusts (A-REITs).',
  },
  {
    ticker: 'VLC',
    asxCode: 'ASX: VLC',
    name: 'Vanguard MSCI Australian Large Companies Index ETF',
    shortName: 'Australian Large Companies',
    benchmark: 'MSCI Australian Shares Large Cap Index',
    pdsDoc: 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
    description: 'Concentrated exposure to Australia’s largest mega-cap market leaders.',
  },
  {
    ticker: 'VSO',
    asxCode: 'ASX: VSO',
    name: 'Vanguard MSCI Australian Small Companies Index ETF',
    shortName: 'Australian Small Companies',
    benchmark: 'MSCI Australian Shares Small Cap Index',
    pdsDoc: 'AU-ETFPDS-Vanguard_Australian_Shares_ETFs-VAS-VHY-VAP-VLC-VSO.pdf',
    description: 'Targeted exposure to small-cap Australian companies offering growth potential.',
  },
]

export default function EtfDropdown({ selectedEtf, onSelectEtf }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick)
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
    }
  }, [isOpen])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  return (
    <div className="etf-dropdown-wrapper" ref={dropdownRef}>
      <button
        type="button"
        className={`etf-dropdown-trigger ${isOpen ? 'is-open' : ''}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        title="Select Vanguard ETF from PDS Suite"
      >
        <span className="etf-trigger-name">{selectedEtf?.name || 'Vanguard Australian Shares Index ETF'}</span>
        <span className="ticker-pill">{selectedEtf?.asxCode || 'ASX: VAS'}</span>
        <ChevronDownIcon size={13} className={`etf-chevron ${isOpen ? 'rotated' : ''}`} />
      </button>

      {isOpen && (
        <div className="etf-menu-dropdown fade-in" role="listbox">
          <div className="etf-menu-header">
            <span className="etf-menu-label">VANGUARD AUSTRALIA ETF PDS SUITE</span>
          </div>
          <div className="etf-menu-list">
            {VANGUARD_ETFS.map((etf) => {
              const isSelected = selectedEtf?.ticker === etf.ticker
              return (
                <button
                  key={etf.ticker}
                  type="button"
                  className={`etf-menu-item ${isSelected ? 'is-selected' : ''}`}
                  onClick={() => {
                    onSelectEtf(etf)
                    setIsOpen(false)
                  }}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="etf-item-left">
                    <span className="etf-ticker-badge">{etf.ticker}</span>
                    <div className="etf-item-meta">
                      <strong className="etf-item-title">{etf.name}</strong>
                      <span className="etf-item-benchmark">Benchmark: {etf.benchmark}</span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="etf-selected-dot" aria-label="Selected ETF">
                      Active
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
