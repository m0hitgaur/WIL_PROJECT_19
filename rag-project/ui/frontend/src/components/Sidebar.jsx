import React from 'react'
import {
  PlusIcon,
  LayersIcon,
  MessageSquareIcon,
  CloseIcon,
  SunIcon,
  MoonIcon,
} from './Icons'

export default function Sidebar({
  onNewChat,
  onOpenSettings,
  onOpenTour,
  systemStats,
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  theme,
  onToggleTheme,
}) {
  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand-wrapper">
        <a className="sidebar-brand" href="/" onClick={(e) => { e.preventDefault(); onNewChat(); }} title="ClariFi Home / New Chat">
          <img
            src={theme === 'light' ? '/brand/clarifi-logo-no-bg.png' : '/brand/clarifi-w-logo-no-bg.png'}
            alt="ClariFi"
            className="sidebar-brand-img"
          />
        </a>
      </div>

      {/* New Chat Button */}
      <button type="button" className="new-chat-btn" onClick={onNewChat}>
        <PlusIcon size={14} className="plus-icon" />
        <span>New conversation</span>
        <span className="shortcut-hint">⌘K</span>
      </button>

      {/* Feature Tour Shortcut */}
      <button type="button" className="tour-nav-btn" onClick={onOpenTour}>
        <LayersIcon size={14} className="tour-sparkle" />
        <span>Feature Tour</span>
        <span className="tour-tag">6 Cards</span>
      </button>

      {/* Chat History Section */}
      <div className="sidebar-history-section">
        <div className="sidebar-section-header">
          <span>RECENT CONVERSATIONS</span>
        </div>

        <div className="history-list">
          {conversations.length === 0 ? (
            <div className="history-empty">
              <span>No prior conversations</span>
              <small>Ask a question to begin a new thread</small>
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`history-item ${conv.id === activeConversationId ? 'is-active' : ''}`}
                onClick={() => onSelectConversation && onSelectConversation(conv.id)}
              >
                <MessageSquareIcon size={13} className="history-item-icon" />
                <span className="history-item-title" title={conv.title}>
                  {conv.title}
                </span>
                {onDeleteConversation && (
                  <button
                    type="button"
                    className="history-item-delete"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteConversation(conv.id)
                    }}
                    title="Delete conversation"
                  >
                    <CloseIcon size={11} />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Sidebar Footer with User Profile and Settings Gear */}
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar" title="Adrian P.">
            AP
          </div>
          <div className="user-details">
            <span className="user-name">Adrian P.</span>
            <span className="user-status-row">
              <span className={`status-dot-mini ${systemStats?.neo4j?.connected ? 'online' : 'offline'}`} />
              <span className="user-role">Pro user</span>
            </span>
          </div>
        </div>

        <div className="sidebar-footer-actions">
          {onToggleTheme && (
            <button
              type="button"
              className="theme-quick-btn"
              onClick={onToggleTheme}
              title={theme === 'light' ? 'Switch to Dark Theme (Cmd+Shift+T)' : 'Switch to Light Theme (Cmd+Shift+T)'}
              aria-label="Toggle light or dark theme"
            >
              {theme === 'light' ? <MoonIcon size={15} /> : <SunIcon size={15} />}
            </button>
          )}

          <button
            type="button"
            className="settings-gear-btn"
            onClick={onOpenSettings}
            title="System Settings & Telemetry (Gear)"
            aria-label="System Settings & Telemetry"
          >
            <svg className="gear-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}
