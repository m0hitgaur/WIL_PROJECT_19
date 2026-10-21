import React from 'react'

export default function MinimalVideoLanding({ theme = 'dark' }) {
  return (
    <div className="minimal-video-landing">
      <div className="minimal-video-container">
        <video
          className="minimal-landing-video"
          src="/brand/clarifi-w.mp4"
          autoPlay
          loop
          muted
          playsInline
          aria-label="ClariFi Animated Logo"
        />
      </div>
    </div>
  )
}
