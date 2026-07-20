import VideoEmbed from './VideoEmbed.jsx'
import { embedPlaylistUrl, CHANNEL_URLS } from '../data/videos.js'

// Live-updating embed of the channel's real "uploads" playlist. Because it
// pulls straight from YouTube, the sidebar always reflects the channel's
// actual, current videos — no hardcoded/fake links required.
export default function PlaylistPlayer({ title = 'Latest from TV24 Studio' }) {
  return (
    <div className="card">
      <VideoEmbed src={embedPlaylistUrl()} title={title} />
      <div style={{ padding: '14px 18px' }}>
        <p style={{ margin: 0, fontSize: 13 }}>
          Live playlist pulled directly from the official channel. Click the
          playlist icon in the player to browse every video, or{' '}
          <a
            href={CHANNEL_URLS.main}
            target="_blank"
            rel="noreferrer"
            style={{ color: 'var(--t24-red)', fontWeight: 700 }}
          >
            open the full channel on YouTube
          </a>
          .
        </p>
      </div>
    </div>
  )
}
