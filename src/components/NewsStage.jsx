import { forwardRef, useEffect, useRef, useState } from 'react'
import { ANCHOR_IMAGE, ANCHOR_VIDEO } from '../data/newsroom.js'
import { voiceLevel } from '../hooks/useAnchorVoice.js'
import logo from '../assets/logo.png'
import './NewsStage.css'

function useClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return now
}

function AnchorPlaceholder({ speaking }) {
  return (
    <div className={`anchor-ph ${speaking ? 'is-speaking' : ''}`}>
      <svg viewBox="0 0 200 220" aria-hidden="true">
        <defs>
          <linearGradient id="suit" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#2a2c33" />
            <stop offset="1" stopColor="#111216" />
          </linearGradient>
        </defs>
        <circle cx="100" cy="70" r="38" fill="#3a3d46" />
        <path d="M20 220c4-62 38-92 80-92s76 30 80 92z" fill="url(#suit)" />
        <path d="M88 130l12 34 12-34z" fill="#e2231a" />
      </svg>
      <span className="anchor-ph-label">AI ANCHOR</span>
      <span className="anchor-ph-wave">
        <i /><i /><i /><i /><i />
      </span>
    </div>
  )
}

// Talking photo anchor: the real head photo (public/anchor.png), unmodified,
// with a dark mouth cut-out that opens on the live voice level via --jaw. No
// drawn body, no head tilt/nod/sway — the photo stays exactly as it is, and
// the only motion is the mouth, so it reads as the real person speaking.
function PhotoAnchor({ src, speaking, onError }) {
  const elRef = useRef(null)

  useEffect(() => {
    const el = elRef.current
    if (!el) return undefined
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    let jaw = 0
    let syll = 0
    let syllTarget = 0
    let nextSyll = 0

    const frame = (now) => {
      let target = 0
      if (voiceLevel.active) {
        if (voiceLevel.source === 'audio') {
          target = Math.min(1, Math.max(0, (voiceLevel.value - 0.05) * 1.25)) // ignore hiss
        } else {
          // No audio to measure (browser voice): a syllable rhythm of ~6–9 per second.
          if (now > nextSyll) {
            syllTarget = Math.random() < 0.15 ? 0.1 : 0.45 + Math.random() * 0.55
            nextSyll = now + 110 + Math.random() * 60
          }
          syll += (syllTarget - syll) * 0.35
          target = syll
        }
      }
      jaw += (target - jaw) * (target > jaw ? 0.55 : 0.3) // open fast, close a bit slower
      el.style.setProperty('--jaw', reduce ? '0' : jaw.toFixed(3))
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div ref={elRef} className={`anchor-photo ${speaking ? 'is-speaking' : ''}`}>
      <img className="anchor-base" src={src} alt="TV24 news anchor" onError={onError} />
      <span className="anchor-mouth" aria-hidden="true" />
      <img className="anchor-jaw" src={src} alt="" aria-hidden="true" />
      <span className="anchor-tally" aria-hidden="true" />
    </div>
  )
}

const NewsStage = forwardRef(function NewsStage(
  { segment, index, total, caption, ticker, speaking, onFullscreen },
  ref,
) {
  const now = useClock()
  const videoRef = useRef(null)
  // Anchor source, in order of preference: base video → photo cut-out → drawn placeholder.
  const [anchor, setAnchor] = useState('video')
  const videoOk = anchor === 'video'

  // The base anchor video only "talks" while the voice is speaking.
  useEffect(() => {
    const v = videoRef.current
    if (!v || !videoOk) return
    if (speaking) v.play().catch(() => {})
    else v.pause()
  }, [speaking, videoOk])

  const isStory = segment?.kind === 'story'
  const tickerLine = ticker.length ? ticker.join('   ◆   ') : 'TV24 స్టూడియో — తెలుగు రాజకీయ వార్తలు'
  const time = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })

  return (
    <div className="stage" ref={ref}>
      <div className="stage-bg" />

      <div className="stage-anchor">
        {anchor === 'video' && (
          <video
            ref={videoRef}
            src={ANCHOR_VIDEO}
            muted
            loop
            playsInline
            preload="auto"
            onError={() => setAnchor('image')}
          />
        )}
        {anchor === 'image' && (
          <PhotoAnchor src={ANCHOR_IMAGE} speaking={speaking} onError={() => setAnchor('none')} />
        )}
        {anchor === 'none' && <AnchorPlaceholder speaking={speaking} />}
      </div>

      {/* top-left channel bug */}
      <div className="stage-bug">
        <img src={logo} alt="TV24 Studio" className="bug-logo" />
      </div>

      {/* top-right live + clock */}
      <div className="stage-live">
        <span className="badge">
          <span className="badge-dot" /> Live
        </span>
        <span className="stage-clock">{time}</span>
      </div>

      {/* story window */}
      {segment && (
        <div className="stage-window" key={segment.id}>
          <span className="window-cat">{segment.category}</span>
          {isStory ? (
            <span className="window-count">
              {String(index).padStart(2, '0')}
              <small>/{String(total).padStart(2, '0')}</small>
            </span>
          ) : (
            <span className="window-count window-count-text">TV24 న్యూస్</span>
          )}
          {segment.source && <span className="window-src">{segment.source}</span>}
        </div>
      )}

      {segment?.breaking && (
        <div className="stage-breaking" key={`b-${segment.id}`}>
          <span>బ్రేకింగ్ న్యూస్</span>
        </div>
      )}

      {/* lower third */}
      {segment && (
        <div className="lower-third" key={`lt-${segment.id}`}>
          <div className="lt-head">
            <span className="lt-tag">{segment.breaking ? 'BREAKING' : segment.category}</span>
            <h2 className="lt-headline">{segment.headline}</h2>
          </div>
          <div className="lt-caption">{caption}</div>
        </div>
      )}

      {/* ticker */}
      <div className="stage-ticker">
        <span className="ticker-label">ముఖ్యాంశాలు</span>
        <div className="ticker-track">
          <div className="ticker-move" style={{ animationDuration: `${Math.max(25, tickerLine.length / 4)}s` }}>
            <span>{tickerLine}   ◆   </span>
            <span>{tickerLine}   ◆   </span>
          </div>
        </div>
      </div>

      {onFullscreen && (
        <button className="stage-fs" onClick={onFullscreen} aria-label="Full screen">
          ⛶
        </button>
      )}
    </div>
  )
})

export default NewsStage
