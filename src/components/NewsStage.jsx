import { forwardRef, useEffect, useRef, useState } from 'react'
import { ANCHOR_IMAGE, ANCHOR_VIDEO } from '../data/newsroom.js'
import { voiceLevel } from '../hooks/useAnchorVoice.js'
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

// Talking photo anchor. Every frame it reads the live voice level and sets
// CSS variables: --jaw opens the mouth, --tilt/--nod/--lift move the head,
// --breath/--sway move the suit (body) separately from the head.

// Suit drawn in the anchor box's 616 x 760 units. The neck of the head photo
// ends at y = 392, centred on x = 275. Mirror a left-side x with 550 - x.
const SUIT = {
  navy: '#1c2536',
  navyDark: '#111723',
  lapel: '#161d2b',
  shirt: '#f4f5f7',
  shirtShade: '#d9dce2',
  tie: '#c0211a',
  tieDark: '#8f1712',
  gold: '#f7941d',
}
const mirror = (pts) => pts.map(([x, y]) => [550 - x, y])
const poly = (pts) => pts.map((p) => p.join(',')).join(' ')
const LAPEL_L = [[226, 370], [168, 398], [186, 424], [160, 440], [275, 612], [252, 480], [238, 404]]
const COLLAR_L = [[216, 362], [232, 356], [266, 394], [254, 418], [218, 390]]

function SuitBack() {
  return (
    <svg className="anchor-suit anchor-suit-back" viewBox="0 0 616 760" aria-hidden="true">
      <defs>
        <linearGradient id="suitNavy" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={SUIT.navy} />
          <stop offset="1" stopColor={SUIT.navyDark} />
        </linearGradient>
        <radialGradient id="suitSheen" cx="0.5" cy="0.62" r="0.55">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.07" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="tieRed" x1="0" x2="1">
          <stop offset="0" stopColor={SUIT.tieDark} />
          <stop offset="0.5" stopColor={SUIT.tie} />
          <stop offset="1" stopColor={SUIT.tieDark} />
        </linearGradient>
      </defs>
      {/* jacket */}
      <path
        d="M226 370 C184 384 126 398 84 414 C44 430 24 462 18 524 L12 760 L538 760 L532 524 C526 462 506 430 466 414 C424 398 366 384 324 370 Z"
        fill="url(#suitNavy)"
      />
      <path d="M226 370 C184 384 126 398 84 414 C44 430 24 462 18 524 L12 760 L538 760 L532 524 C526 462 506 430 466 414 C424 398 366 384 324 370 Z" fill="url(#suitSheen)" />
      {/* shoulder seams */}
      <path d="M74 420 C84 484 86 580 82 760 M476 420 C466 484 464 580 468 760" stroke="#0b0f18" strokeWidth="3" fill="none" opacity="0.6" />
      {/* shirt front */}
      <polygon points="224,360 326,360 275,604" fill={SUIT.shirt} />
      <polygon points="275,420 326,360 300,520" fill={SUIT.shirtShade} opacity="0.5" />
      {/* tie blade */}
      <polygon points="265,414 285,414 300,562 275,598 250,562" fill="url(#tieRed)" />
      <g stroke={SUIT.gold} strokeWidth="3" opacity="0.55">
        <line x1="262" y1="460" x2="290" y2="440" />
        <line x1="258" y1="505" x2="294" y2="480" />
        <line x1="256" y1="550" x2="296" y2="522" />
      </g>
      {/* lapels */}
      <polygon points={poly(LAPEL_L)} fill={SUIT.lapel} stroke="#2b3550" strokeWidth="2" />
      <polygon points={poly(mirror(LAPEL_L))} fill={SUIT.lapel} stroke="#2b3550" strokeWidth="2" />
      {/* lapel mic, pocket square, button */}
      <rect x="301" y="458" width="9" height="18" rx="3" fill="#0a0a0a" />
      <rect x="303" y="452" width="5" height="8" fill="#3a3a3a" />
      <polygon points="392,508 444,500 440,514 396,520" fill={SUIT.gold} />
      <circle cx="275" cy="628" r="6" fill="#0d121c" stroke="#2b3550" strokeWidth="2" />
    </svg>
  )
}

function SuitFront() {
  return (
    <svg className="anchor-suit anchor-suit-front" viewBox="0 0 616 760" aria-hidden="true">
      {/* shirt collar wings and tie knot, in front of the neck */}
      <polygon points={poly(COLLAR_L)} fill={SUIT.shirt} stroke={SUIT.shirtShade} strokeWidth="2" />
      <polygon points={poly(mirror(COLLAR_L))} fill={SUIT.shirt} stroke={SUIT.shirtShade} strokeWidth="2" />
      <polygon points="262,392 288,392 284,418 266,418" fill={SUIT.tie} stroke={SUIT.tieDark} strokeWidth="2" />
    </svg>
  )
}

function PhotoAnchor({ src, speaking, onError }) {
  const elRef = useRef(null)

  useEffect(() => {
    const el = elRef.current
    if (!el) return undefined
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    let jaw = 0
    let energy = 0
    let syll = 0
    let syllTarget = 0
    let nextSyll = 0
    const t0 = performance.now()

    const frame = (now) => {
      const t = (now - t0) / 1000
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
      energy += ((voiceLevel.active ? 1 : 0) - energy) * 0.03
      if (reduce) {
        el.style.setProperty('--jaw', '0')
      } else {
        el.style.setProperty('--jaw', jaw.toFixed(3))
        // calm idle sway; livelier, with nods on loud syllables, while talking
        el.style.setProperty('--tilt', `${(Math.sin(t * 0.7) * 0.5 + Math.sin(t * 1.9) * 0.35 * energy).toFixed(3)}deg`)
        el.style.setProperty('--nod', `${(jaw * 0.6 * energy + Math.sin(t * 0.45) * 0.15).toFixed(3)}deg`)
        el.style.setProperty('--lift', `${(Math.sin(t * 1.1) * 0.25 + 0.25).toFixed(3)}%`)
        // body: breathing, and a small shoulder rise with emphasis while talking
        el.style.setProperty('--breath', (1 + Math.sin(t * 1.6) * 0.004 * (1 + energy)).toFixed(4))
        el.style.setProperty('--sway', `${(-jaw * 0.35 * energy).toFixed(3)}%`)
      }
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div ref={elRef} className={`anchor-photo ${speaking ? 'is-speaking' : ''}`}>
      <SuitBack />
      <div className="anchor-head">
        <img className="anchor-base" src={src} alt="TV24 news anchor" onError={onError} />
        <span className="anchor-mouth" aria-hidden="true" />
        <img className="anchor-jaw" src={src} alt="" aria-hidden="true" />
      </div>
      <SuitFront />
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
        <span className="bug-mark">TV24</span>
        <span className="bug-studio">STUDIO</span>
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
