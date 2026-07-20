import { CHANNEL_URLS, SOCIAL_LINKS, CONTACT, ABOUT_TEXT } from '../data/videos.js'

export default function About() {
  return (
    <div className="container section">
      <span className="eyebrow">Who We Are</span>
      <h1>About TV24 Studio</h1>
      <p style={{ maxWidth: 680, fontSize: 16 }}>{ABOUT_TEXT}</p>

      <div className="grid grid-2" style={{ marginTop: 40 }}>
        <div className="card category-block">
          <h3>Our Focus</h3>
          <p>
            Andhra Pradesh political news, Janasena and party updates,
            ground-level reporting, public opinion surveys, election analysis,
            and Tollywood film news.
          </p>
        </div>
        <div className="card category-block">
          <h3>Reach Us</h3>
          <p>
            Email:{' '}
            <a href={`mailto:${CONTACT.email}`} style={{ color: 'var(--t24-red)' }}>
              {CONTACT.email}
            </a>
            <br />
            Phone: {CONTACT.phone}
          </p>
        </div>
      </div>

      <div className="section-title" style={{ marginTop: 48 }}>
        <span className="bar" />
        <h2>Find Us Online</h2>
      </div>
      <div className="grid grid-4">
        <a className="card link-card" href={CHANNEL_URLS.main} target="_blank" rel="noreferrer"><h3>YouTube</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.facebook} target="_blank" rel="noreferrer"><h3>Facebook</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.twitter} target="_blank" rel="noreferrer"><h3>Twitter / X</h3></a>
        <a className="card link-card" href={SOCIAL_LINKS.instagram} target="_blank" rel="noreferrer"><h3>Instagram</h3></a>
      </div>

      <p style={{ marginTop: 40, fontSize: 12.5, color: 'var(--t24-gray-dark)' }}>
        TV24 Studio is an independent Telugu political news &amp; entertainment
        YouTube channel (492K+ subscribers, 23K+ videos). This site is a
        community/fan project built around the channel's real branding — the
        red &amp; gold colour palette above is taken directly from TV24
        Studio's own logo and channel banner.
      </p>
    </div>
  )
}
