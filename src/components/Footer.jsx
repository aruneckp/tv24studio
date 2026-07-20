import { Link } from 'react-router-dom'
import { CHANNEL_URLS, SOCIAL_LINKS, CONTACT } from '../data/videos.js'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div>
          <div className="brand">
            <span className="brand-mark">TV24</span>
            <span className="brand-studio">STUDIO</span>
          </div>
          <p className="footer-about">
            Telugu Political News Channel covering Andhra Pradesh politics,
            Janasena &amp; party updates, political analysis, and Tollywood news.
          </p>
        </div>

        <div>
          <h3>Explore</h3>
          <ul className="footer-links">
            <li><Link to="/videos">Latest Videos</Link></li>
            <li><Link to="/shows">Shows &amp; Categories</Link></li>
            <li><Link to="/music">Music</Link></li>
            <li><Link to="/about">About Us</Link></li>
            <li><Link to="/contact">Contact</Link></li>
          </ul>
        </div>

        <div>
          <h3>Watch Us On</h3>
          <ul className="footer-links">
            <li><a href={CHANNEL_URLS.main} target="_blank" rel="noreferrer">YouTube Channel</a></li>
            <li><a href={CHANNEL_URLS.music} target="_blank" rel="noreferrer">YouTube Music</a></li>
            <li><a href={SOCIAL_LINKS.facebook} target="_blank" rel="noreferrer">Facebook</a></li>
            <li><a href={SOCIAL_LINKS.twitter} target="_blank" rel="noreferrer">Twitter / X</a></li>
            <li><a href={SOCIAL_LINKS.instagram} target="_blank" rel="noreferrer">Instagram</a></li>
            <li><a href={SOCIAL_LINKS.telegramChannel} target="_blank" rel="noreferrer">Telegram</a></li>
          </ul>
        </div>

        <div>
          <h3>Contact</h3>
          <ul className="footer-links">
            <li><a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a></li>
            <li><a href={`tel:${CONTACT.phone.replace(/\s/g, '')}`}>{CONTACT.phone}</a></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <div className="container footer-bottom-inner">
          <span>&copy; {new Date().getFullYear()} TV24 Studio. All rights reserved.</span>
          <span className="footer-note">Fan-made / community site built around TV24 Studio's real channel branding.</span>
        </div>
      </div>
    </footer>
  )
}
