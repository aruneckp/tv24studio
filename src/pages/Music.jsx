import PlaylistPlayer from '../components/PlaylistPlayer.jsx'
import { CHANNEL_URLS } from '../data/videos.js'

export default function Music() {
  return (
    <div className="container section">
      <span className="eyebrow">Audio &amp; Music</span>
      <h1>TV24 Studio Music</h1>
      <p style={{ maxWidth: 640, marginBottom: 32 }}>
        TV24 Studio's audio content and music-related uploads are available
        directly through YouTube Music, powered by the same official channel.
      </p>

      <div className="section-title">
        <span className="bar" />
        <h2>Listen &amp; Watch</h2>
      </div>
      <PlaylistPlayer title="TV24 Studio — Music &amp; Audio" />

      <div className="grid grid-2" style={{ marginTop: 32 }}>
        <a className="card link-card" href={CHANNEL_URLS.music} target="_blank" rel="noreferrer">
          <h3>Open in YouTube Music &rarr;</h3>
          <p>Stream TV24 Studio content directly on music.youtube.com.</p>
        </a>
        <a className="card link-card" href={CHANNEL_URLS.main} target="_blank" rel="noreferrer">
          <h3>Open YouTube Channel &rarr;</h3>
          <p>See every upload, including music and audio segments, on YouTube.</p>
        </a>
      </div>
    </div>
  )
}
