import { Link } from 'react-router-dom'
import PlaylistPlayer from '../components/PlaylistPlayer.jsx'
import VideoCard from '../components/VideoCard.jsx'
import { FEATURED_VIDEOS, CATEGORIES, CHANNEL_URLS } from '../data/videos.js'
import './Home.css'

export default function Home() {
  return (
    <div>
      <section className="hero">
        <div className="container hero-inner">
          <div>
            <span className="badge">
              <span className="badge-dot" /> On Air
            </span>
            <h1 className="hero-title">
              Andhra Pradesh Politics.<br />
              Told Straight. <span className="hero-title-accent">TV24 Studio.</span>
            </h1>
            <p className="hero-sub">
              In-depth AP political news, Janasena &amp; party updates, ground
              reports, public opinion, and the latest from Tollywood — all in
              one place.
            </p>
            <div className="hero-actions">
              <Link to="/newsroom" className="btn btn-red">▶ AI News Bulletin</Link>
              <Link to="/videos" className="btn btn-outline">Watch Latest</Link>
              <a
                href={CHANNEL_URLS.main}
                target="_blank"
                rel="noreferrer"
                className="btn btn-outline"
              >
                Subscribe on YouTube
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="section container">
        <div className="section-title">
          <span className="bar" />
          <h2>Live From The Channel</h2>
        </div>
        <PlaylistPlayer />
      </section>

      <section className="section container">
        <div className="section-title">
          <span className="bar" />
          <h2>Featured Videos</h2>
        </div>
        <div className="grid grid-3">
          {FEATURED_VIDEOS.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      </section>

      <section className="section container">
        <div className="section-title">
          <span className="bar" />
          <h2>What We Cover</h2>
        </div>
        <div className="grid grid-3">
          {CATEGORIES.map((cat) => (
            <div className="card category-card" key={cat.name}>
              <h3>{cat.name}</h3>
              <p>{cat.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
