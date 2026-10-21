import React from 'react'
import ClassicLanding from './ClassicLanding'
import MinimalVideoLanding from './MinimalVideoLanding'

/**
 * Modular Chat Landing Page Coordinator
 * Allows seamless switching between:
 * - 'minimal': Just the looping clarifi-w.mp4 animated mark with zero distracting text (Task 6)
 * - 'classic': Original welcome screen with hero typography, tour CTA, and starter question cards
 */
export default function ChatLanding({
  variant = 'minimal',
  theme = 'dark',
  onOpenTour,
  onSelectQuestion,
  suggestedQuestions = [],
}) {
  if (variant === 'classic') {
    return (
      <ClassicLanding
        theme={theme}
        onOpenTour={onOpenTour}
        onSelectQuestion={onSelectQuestion}
        suggestedQuestions={suggestedQuestions}
      />
    )
  }

  return <MinimalVideoLanding theme={theme} />
}
