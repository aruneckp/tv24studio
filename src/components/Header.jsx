import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { CHANNEL_URLS } from '../data/videos.js'
import './Header.css'

const NAV_LINKS = [
  { to: '/', label: 'Home' },
  { to: '/videos', label: 'Videos' },
  { to: '/shows', label: 'Shows' },
  { to: '/music', label: 'Music' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
]

export default function Header() {
  const [open, setOpen] = useState(false)

  return (
    <header className="site-header">
      <div className="header-topbar">
        <div className="container topbar-inner">
          <span className="topbar-item">
            <span className="badge">
              <span className="badge-dot" /> Live
            </span>
          </span>
          <span className="topbar-item topbar-tagline">
            Telugu Political News &amp; Andhra Pradesh Updates
          </span>
          <a
            className="topbar-item topbar-link"
            href={CHANNEL_URLS.main}
            target="_blank"
            rel="noreferrer"
          >
            Subscribe on YouTube
          </a>
        </div>
      </div>

      <div className="container header-main">
        <NavLink to="/" className="brand">
          <span className="brand-mark">TV24</span>
          <span className="brand-studio">STUDIO</span>
        </NavLink>

        <nav className={`main-nav ${open ? 'is-open' : ''}`}>
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? 'nav-link is-active' : 'nav-link')}
              onClick={() => setOpen(false)}
              end={link.to === '/'}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <button
          className="nav-toggle"
          aria-label="Toggle navigation"
          onClick={() => setOpen((o) => !o)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>
    </header>
  )
}
