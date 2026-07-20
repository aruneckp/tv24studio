import PlaylistPlayer from '../components/PlaylistPlayer.jsx'
import VideoCard from '../components/VideoCard.jsx'
import { CATEGORIES, FEATURED_VIDEOS } from '../data/videos.js'

export default function Shows() {
  return (
    <div className="container section">
      <span className="eyebrow">Coverage Areas</span>
      <h1>Shows &amp; Categories</h1>
      <p style={{ maxWidth: 640, marginBottom: 32 }}>
        TV24 Studio's coverage spans Andhra Pradesh politics, Janasena &amp;
        party updates, election analysis and Tollywood news.
      </p>

      <div className="grid grid-2" style={{ marginBottom: 48 }}>
        {CATEGORIES.map((cat) => (
          <div className="card category-block" key={cat.name}>
            <h3>{cat.name}</h3>
            <p>{cat.description}</p>
          </div>
        ))}
      </div>

      <div className="section-title">
        <span className="bar" />
        <h2>Sample Reports</h2>
      </div>
      <div className="grid grid-3" style={{ marginBottom: 48 }}>
        {FEATURED_VIDEOS.map((video) => (
          <VideoCard key={video.id} video={video} />
        ))}
      </div>

      <div className="section-title">
        <span className="bar" />
        <h2>Browse Every Episode</h2>
      </div>
      <PlaylistPlayer title="TV24 Studio — Shows Playlist" />
    </div>
  )
}
