import { CONTACT, SOCIAL_LINKS, CHANNEL_URLS } from '../data/videos.js'

export default function Contact() {
  return (
    <div className="container section">
      <span className="eyebrow">Get In Touch</span>
      <h1>Contact TV24 Studio</h1>
      <p style={{ maxWidth: 640, marginBottom: 32 }}>
        For advertising, sponsorships, story tips or general questions, reach
        the TV24 Studio team directly.
      </p>

      <div className="grid grid-2">
        <div className="card category-block">
          <h3>Email</h3>
          <p>
            <a href={`mailto:${CONTACT.email}`} style={{ color: 'var(--t24-red)', fontWeight: 700 }}>
              {CONTACT.email}
            </a>
          </p>
        </div>
        <div className="card category-block">
          <h3>Phone</h3>
          <p>
            <a href={`tel:${CONTACT.phone.replace(/\s/g, '')}`} style={{ color: 'var(--t24-red)', fontWeight: 700 }}>
              {CONTACT.phone}
            </a>
          </p>
        </div>
      </div>

      <div className="section-title" style={{ marginTop: 48 }}>
        <span className="bar" />
        <h2>Follow &amp; Subscribe</h2>
      </div>
      <div className="grid grid-4">
        <a className="card link-card" href={CHANNEL_URLS.main} target="_blank" rel="noreferrer"><h3>YouTube</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.facebook} target="_blank" rel="noreferrer"><h3>Facebook</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.twitter} target="_blank" rel="noreferrer"><h3>Twitter / X</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.instagram} target="_blank" rel="noreferrer"><h3>Instagram</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.telegramGroup} target="_blank" rel="noreferrer"><h3>Telegram Group</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.telegramChannel} target="_blank" rel="noreferrer"><h3>Telegram Channel</h3></a>
      </div>
    </div>
  )
}
