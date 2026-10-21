import React from 'react'

/**
 * Tokenizes inline Markdown syntax:
 * - Inline code: `code`
 * - Links: [text](url)
 * - Bold + Italic: ***text***
 * - Bold: **text** or __text__
 * - Italic: *text* or _text_
 * - Strikethrough: ~~text~~
 * - Text fallbacks
 */
function parseInlineTokens(text) {
  if (!text) return []

  const tokens = []
  let remaining = String(text)

  // 1: Inline code: `...`
  // 2: Link: [...](...) (3: text, 4: href)
  // 5: Bold+Italic: ***...*** (6: content)
  // 7: Bold: **...** or __...__ (8: ** content, 9: __ content)
  // 10: Italic: *...* or _..._ (10: * content, 11: _ content)
  // 12: Strikethrough: ~~...~~ (13: content)
  const inlineRegex =
    /(`[^`]+`)|(\[([^\]]+)\]\(([^)\s]+)\))|(\*\*\*(.+?)\*\*\*)|(\*\*(.+?)\*\*|(?:\b|(?<=\s))__(.+?)__(?:\b|(?=\s)))|(?:\*(?!\*)([^\s*](?:[^*\n]*?[^\s*])?)\*|(?<=\s|^|[([{"'])_([^\s_](?:[^_\n]*?[^\s_])?)_(?=[\s)\]}"'.,;:!?]|$))|(~~(.+?)~~)/

  while (remaining.length > 0) {
    const match = remaining.match(inlineRegex)
    if (!match) {
      tokens.push({ type: 'text', value: remaining })
      break
    }

    const matchIndex = match.index
    if (matchIndex > 0) {
      tokens.push({ type: 'text', value: remaining.slice(0, matchIndex) })
    }

    const fullMatch = match[0]

    if (match[1]) {
      tokens.push({ type: 'code', value: fullMatch.slice(1, -1) })
    } else if (match[2]) {
      tokens.push({ type: 'link', text: match[3], href: match[4] })
    } else if (match[5]) {
      tokens.push({ type: 'bold_italic', children: parseInlineTokens(match[6]) })
    } else if (match[7]) {
      const boldContent = match[8] || match[9]
      tokens.push({ type: 'bold', children: parseInlineTokens(boldContent) })
    } else if (match[10] !== undefined || match[11] !== undefined) {
      const italicContent = match[10] !== undefined ? match[10] : match[11]
      tokens.push({ type: 'italic', children: parseInlineTokens(italicContent) })
    } else if (match[12]) {
      tokens.push({ type: 'strikethrough', children: parseInlineTokens(match[13]) })
    }

    remaining = remaining.slice(matchIndex + fullMatch.length)
  }

  return tokens
}

/**
 * Parses block-level Markdown structures:
 * - Fenced code blocks
 * - Headings (# to ######)
 * - Horizontal rules (---, ***, ___)
 * - Blockquotes (> quote)
 * - Tables (| a | b |)
 * - Lists (unordered with •, -, *, + and ordered with 1., 2.)
 * - Paragraphs
 */
function parseMarkdownBlocks(markdown) {
  if (!markdown) return []

  const lines = String(markdown).replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Skip leading empty lines between blocks
    if (!line.trim()) {
      i++
      continue
    }

    // 1. Fenced code block
    const fenceMatch = line.match(/^```(\w*)/)
    if (fenceMatch) {
      const language = fenceMatch[1] || ''
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      if (i < lines.length) i++ // skip closing ```
      blocks.push({
        type: 'code_block',
        language,
        code: codeLines.join('\n'),
      })
      continue
    }

    // 2. Heading (# to ######)
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      })
      i++
      continue
    }

    // 3. Horizontal Rule
    if (/^(?:---|\*\*\*|___)\s*$/.test(line)) {
      blocks.push({ type: 'hr' })
      i++
      continue
    }

    // 4. Blockquote
    if (line.match(/^>\s?(.*)$/)) {
      const quoteLines = []
      while (i < lines.length && lines[i].match(/^>\s?(.*)$/)) {
        const qMatch = lines[i].match(/^>\s?(.*)$/)
        quoteLines.push(qMatch[1])
        i++
      }
      blocks.push({
        type: 'blockquote',
        text: quoteLines.join('\n'),
      })
      continue
    }

    // 5. Table (GFM format)
    if (
      line.includes('|') &&
      i + 1 < lines.length &&
      /^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)+\|?\s*$/.test(lines[i + 1])
    ) {
      const headerRow = line
      i += 2
      const dataRows = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        dataRows.push(lines[i])
        i++
      }

      const parseCells = (rowStr) => {
        let trimmed = rowStr.trim()
        if (trimmed.startsWith('|')) trimmed = trimmed.slice(1)
        if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1)
        return trimmed.split('|').map((c) => c.trim())
      }

      blocks.push({
        type: 'table',
        headers: parseCells(headerRow),
        rows: dataRows.map(parseCells),
      })
      continue
    }

    // 6. Lists (Unordered vs Ordered)
    const unorderedMatch = line.match(/^([ \t]*)(?:[•\u2022\u2013\u2014\-+]|\*(?!\*))\s+(.+)$/)
    const orderedMatch = line.match(/^([ \t]*)(\d+)[.)]\s+(.+)$/)

    if (unorderedMatch || orderedMatch) {
      const isOrdered = Boolean(orderedMatch)
      const listItems = []

      while (i < lines.length) {
        const curLine = lines[i]
        if (!curLine.trim()) {
          // If followed by another list item, list continues
          if (i + 1 < lines.length) {
            const nextMatch = lines[i + 1].match(
              /^([ \t]*)(?:(?:[•\u2022\u2013\u2014\-+]|\*(?!\*))|\d+[.)])\s+(.+)$/
            )
            if (nextMatch) {
              i++
              continue
            }
          }
          break
        }

        const curUnordered = curLine.match(
          /^([ \t]*)(?:[•\u2022\u2013\u2014\-+]|\*(?!\*))\s+(.+)$/
        )
        const curOrdered = curLine.match(/^([ \t]*)(\d+)[.)]\s+(.+)$/)

        if (isOrdered && curOrdered) {
          listItems.push(curOrdered[3])
          i++
        } else if (!isOrdered && curUnordered) {
          listItems.push(curUnordered[2])
          i++
        } else if (curLine.match(/^[ \t]{2,}\S/)) {
          // Multiline continuation
          if (listItems.length > 0) {
            listItems[listItems.length - 1] += ' ' + curLine.trim()
          }
          i++
        } else {
          break
        }
      }

      blocks.push({
        type: isOrdered ? 'ordered_list' : 'unordered_list',
        items: listItems,
      })
      continue
    }

    // 7. Regular paragraph
    const paragraphLines = []
    while (i < lines.length && lines[i].trim() !== '') {
      const curLine = lines[i]
      if (
        curLine.match(/^```/) ||
        curLine.match(/^#{1,6}\s+/) ||
        /^(?:---|\*\*\*|___)\s*$/.test(curLine) ||
        curLine.match(/^>\s?/) ||
        curLine.match(/^[ \t]*(?:[•\u2022\u2013\u2014\-+]|\*(?!\*))\s+/) ||
        curLine.match(/^[ \t]*\d+[.)]\s+/) ||
        (curLine.includes('|') &&
          i + 1 < lines.length &&
          /^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)+\|?\s*$/.test(lines[i + 1]))
      ) {
        break
      }
      paragraphLines.push(curLine)
      i++
    }

    if (paragraphLines.length > 0) {
      blocks.push({
        type: 'paragraph',
        text: paragraphLines.join('\n'),
      })
    }
  }

  return blocks
}

/**
 * Recursively renders inline token objects into React DOM nodes.
 */
function renderInlineTokens(tokens, keyPrefix = 'tok') {
  return tokens.map((token, idx) => {
    const key = `${keyPrefix}-${idx}`
    switch (token.type) {
      case 'text':
        return token.value
      case 'code':
        return (
          <code key={key} className="inline-code">
            {token.value}
          </code>
        )
      case 'link':
        return (
          <a
            key={key}
            href={token.href}
            className="markdown-link"
            target="_blank"
            rel="noopener noreferrer"
          >
            {token.text}
          </a>
        )
      case 'bold_italic':
        return (
          <strong key={key}>
            <em>{renderInlineTokens(token.children, `${key}-bi`)}</em>
          </strong>
        )
      case 'bold':
        return (
          <strong key={key}>
            {renderInlineTokens(token.children, `${key}-b`)}
          </strong>
        )
      case 'italic':
        return (
          <em key={key}>
            {renderInlineTokens(token.children, `${key}-i`)}
          </em>
        )
      case 'strikethrough':
        return (
          <del key={key}>
            {renderInlineTokens(token.children, `${key}-s`)}
          </del>
        )
      default:
        return null
    }
  })
}

/**
 * Renders paragraph text, preserving single newlines as line breaks.
 */
function renderParagraphText(text, keyPrefix) {
  const lines = text.split('\n')
  return lines.map((line, idx) => {
    const tokens = parseInlineTokens(line)
    return (
      <React.Fragment key={`${keyPrefix}-l-${idx}`}>
        {renderInlineTokens(tokens, `${keyPrefix}-l-${idx}`)}
        {idx < lines.length - 1 && <br />}
      </React.Fragment>
    )
  })
}

/**
 * Main MarkdownRenderer component.
 */
export default function MarkdownRenderer({ content, className = '' }) {
  if (!content) return null

  const blocks = parseMarkdownBlocks(content)

  return (
    <div className={`markdown-body ${className}`.trim()}>
      {blocks.map((block, idx) => {
        const key = `b-${idx}`
        switch (block.type) {
          case 'paragraph':
            return <p key={key}>{renderParagraphText(block.text, key)}</p>

          case 'heading': {
            const HeadingTag = block.level <= 2 ? 'h4' : block.level === 3 ? 'h5' : 'h6'
            const tokens = parseInlineTokens(block.text)
            return <HeadingTag key={key}>{renderInlineTokens(tokens, key)}</HeadingTag>
          }

          case 'unordered_list':
            return (
              <ul key={key}>
                {block.items.map((item, itemIdx) => {
                  const itemKey = `${key}-it-${itemIdx}`
                  const tokens = parseInlineTokens(item)
                  return <li key={itemKey}>{renderInlineTokens(tokens, itemKey)}</li>
                })}
              </ul>
            )

          case 'ordered_list':
            return (
              <ol key={key}>
                {block.items.map((item, itemIdx) => {
                  const itemKey = `${key}-it-${itemIdx}`
                  const tokens = parseInlineTokens(item)
                  return <li key={itemKey}>{renderInlineTokens(tokens, itemKey)}</li>
                })}
              </ol>
            )

          case 'blockquote': {
            const tokens = parseInlineTokens(block.text)
            return (
              <blockquote key={key}>
                {renderInlineTokens(tokens, key)}
              </blockquote>
            )
          }

          case 'code_block':
            return (
              <pre key={key} className="code-block">
                <code className={block.language ? `language-${block.language}` : ''}>
                  {block.code}
                </code>
              </pre>
            )

          case 'hr':
            return <hr key={key} className="markdown-hr" />

          case 'table':
            return (
              <div key={key} className="markdown-table-wrapper">
                <table className="markdown-table">
                  <thead>
                    <tr>
                      {block.headers.map((h, hIdx) => {
                        const tokens = parseInlineTokens(h)
                        return <th key={hIdx}>{renderInlineTokens(tokens, `${key}-th-${hIdx}`)}</th>
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => {
                          const tokens = parseInlineTokens(cell)
                          return (
                            <td key={cIdx}>
                              {renderInlineTokens(tokens, `${key}-td-${rIdx}-${cIdx}`)}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )

          default:
            return null
        }
      })}
    </div>
  )
}
