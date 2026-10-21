const STORAGE_KEY = 'clarifi_conversations'

/**
 * Loads all saved conversation sessions from localStorage.
 */
export function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (err) {
    console.warn('Failed to parse saved conversations from localStorage:', err)
    return []
  }
}

/**
 * Persists all conversation sessions to localStorage.
 */
export function saveConversations(conversations) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
  } catch (err) {
    console.warn('Failed to persist conversations to localStorage:', err)
  }
}

/**
 * Creates a new blank conversation structure.
 */
export function createNewConversation(title = 'New Conversation') {
  return {
    id: `conv-${Date.now()}`,
    title,
    createdAt: new Date().toISOString(),
    messages: [],
  }
}
