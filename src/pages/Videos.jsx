import PlaylistPlayer from '../components/PlaylistPlayer.jsx'
import VideoCard from '../components/VideoCard.jsx'
import { FEATURED_VIDEOS, CHANNEL_URLS } from '../data/videos.js'

export default function Videos() {
  return (
    <div className="container section">
      <span className="eyebrow">Video Library</span>
      <h1>All Videos</h1>
      <p style={{ maxWidth: 640, marginBottom: 32 }}>
        Browse real, up-to-date uploads straight from the TV24 Studio YouTube
        channel, plus a set of featured reports below.
      </p>

      <div className="section-title">
        <span className="bar" />
        <h2>Live Uploads Playlist</h2>
      </div>
      <PlaylistPlayer title="TV24 Studio — All Uploads" />

      <div className="section-title" style={{ marginTop: 48 }}>
        <span className="bar" />
        <h2>Featured Videos</h2>
      </div>
      <div className="grid grid-3">
        {FEATURED_VIDEOS.map((video) => (
          <VideoCard key={video.id} video={video} />
        ))}
      </div>

      <div className="section-title" style={{ marginTop: 48 }}>
        <span className="bar" />
        <h2>More Ways To Watch</h2>
      </div>
      <div className="grid grid-2">
        <a className="card link-card" href={CHANNEL_URLS.main} target="_blank" rel="noreferrer">
          <h3>Full Channel &rarr;</h3>
          <p>Visit TV24 Studio on YouTube for every upload, live streams and shorts.</p>
        </a>
        <a className="card link-card" href={CHANNEL_URLS.videosTab} target="_blank" rel="noreferrer">
          <h3>Videos Tab &rarr;</h3>
          <p>Jump straight to the channel's videos listing, sorted by upload date.</p>
        </a>
      </div>
    </div>
  )
}
