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

// How open the mouth should be for one character of the on-air script —
// a cheap Telugu "viseme" guess with no audio needed: independent vowels and
// vowel signs (maatras) open the mouth, a virama/space/punctuation closes it,
// a bare consonant sits at its inherent half-open 'a'. Unicode block: Telugu
// U+0C00–U+0C7F (ఁ..౿). This is what lets the mouth follow the actual script
// — a news reader "reading", not a random flapping rhythm.
function teluguOpenness(ch) {
  if (!ch) return 0.05
  const c = ch.codePointAt(0)
  if (c >= 0x0c05 && c <= 0x0c14) return 0.92 // అ ఆ ఇ ఈ … independent vowels
  if (c >= 0x0c3e && c <= 0x0c4c) return 0.78 // ా ి ీ ు ూ ె ే ై ొ ో ౌ … vowel signs
  if (c === 0x0c4d) return 0.08 // ్ virama — kills the vowel, mouth shuts
  if (c >= 0x0c02 && c <= 0x0c03) return 0.3 // ం ః anusvara / visarga
  if ((c >= 0x0c15 && c <= 0x0c39) || (c >= 0x0c58 && c <= 0x0c5a)) return 0.48 // consonants, inherent 'a'
  if (ch === ' ' || ch === '\t' || ch === '\n') return 0.04
  if ('.!?,।॥'.includes(ch)) return 0.03
  return 0.32 // digits, Latin, anything else
}

// Interpolated openness at fractional position t (0..1) through the text.
function sampleOpenness(text, t) {
  if (!text) return 0.05
  const pos = Math.min(text.length - 1, Math.max(0, t * text.length))
  const i0 = Math.floor(pos)
  const i1 = Math.min(text.length - 1, i0 + 1)
  const frac = pos - i0
  const w0 = teluguOpenness(text[i0])
  const w1 = teluguOpenness(text[i1])
  return w0 + (w1 - w0) * frac
}

// Talking photo anchor: the real photo (public/anchor.png), unmodified, with
// a dark mouth cut-out that opens on --jaw. No drawn body, no head tilt/nod —
// the only motion is the mouth, paced by the actual caption on screen (the
// sentence currently on air), so it reads as reading rather than flapping.
// Real audio level (when the server recorded MP3 is playing) still modulates
// how wide it opens; the script always drives the rhythm/shape.
function PhotoAnchor({ src, speaking, caption, onError }) {
  const elRef = useRef(null)
  const textRef = useRef({ text: '', start: 0, duration: 1200 })

  // A new sentence on screen = a fresh read-through of its characters.
  useEffect(() => {
    textRef.current = {
      text: caption || '',
      start: performance.now(),
      duration: Math.max(1200, (caption || '').length * 68),
    }
  }, [caption])

  useEffect(() => {
    const el = elRef.current
    if (!el) return undefined
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    let jaw = 0

    const frame = (now) => {
      let target = 0
      if (voiceLevel.active) {
        const { text, start, duration } = textRef.current
        const t = Math.min(1, (now - start) / duration)
        const base = sampleOpenness(text, t)
        if (voiceLevel.source === 'audio') {
          // Real loudness still shapes it a little (pauses dip further, loud syllables pop more).
          const level = Math.min(1, Math.max(0, (voiceLevel.value - 0.04) * 1.3))
          target = base * (0.35 + 0.65 * level)
        } else {
          target = base
        }
      }
      jaw += (target - jaw) * (target > jaw ? 0.6 : 0.34) // open fast, close a bit slower
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
          <PhotoAnchor src={ANCHOR_IMAGE} speaking={speaking} caption={caption} onError={() => setAnchor('none')} />
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
