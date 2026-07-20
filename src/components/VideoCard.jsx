import VideoEmbed from './VideoEmbed.jsx'
import { embedUrl } from '../data/videos.js'
import './VideoCard.css'

export default function VideoCard({ video }) {
  return (
    <div className="card video-card">
      <VideoEmbed src={embedUrl(video.id)} title={video.title} />
      <div className="video-card-body">
        {video.category && <span className="eyebrow">{video.category}</span>}
        <h3 className="video-card-title">{video.title}</h3>
        <a
          className="video-card-link"
          href={video.url}
          target="_blank"
          rel="noreferrer"
        >
          Watch on YouTube &rarr;
        </a>
      </div>
    </div>
  )
}
