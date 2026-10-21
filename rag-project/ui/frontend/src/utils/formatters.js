/**
 * Formats lengthy regulatory PDF filenames into crisp, human-readable document titles.
 */
export function formatDocTitle(filename) {
  if (!filename) return 'Document Source'

  const lower = filename.toLowerCase()

  if (lower.includes('etfpds') || lower.includes('shares_etfs-vas')) {
    return 'VAS Product Disclosure Statement'
  }
  if (lower.includes('fs_vas') || lower.includes('fact_sheet') || lower.includes('factsheet')) {
    return 'VAS Fund Factsheet'
  }
  if (lower.includes('annual_report')) {
    return 'Vanguard Annual Report'
  }
  if (lower.includes('half-year') || lower.includes('half_year')) {
    return 'Vanguard Half-Year Report'
  }
  if (lower.includes('tmd')) {
    return 'Target Market Determination (TMD)'
  }
  if (lower.includes('performance_summary')) {
    return 'Performance Summary Report'
  }

  // General clean-up fallback
  return filename
    .replace(/\.pdf$/i, '')
    .replace(/^AU-/, '')
    .replace(/^ETF-/, '')
    .replace(/_/g, ' ')
    .trim()
}

/**
 * Formats timestamp for message bubbles.
 */
export function formatTime(date = new Date()) {
  const d = typeof date === 'string' ? new Date(date) : date
  if (isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
