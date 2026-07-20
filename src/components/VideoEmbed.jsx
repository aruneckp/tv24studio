// Generic responsive 16:9 YouTube iframe wrapper.
export default function VideoEmbed({ src, title }) {
  return (
    <div className="video-frame-wrap">
      <iframe
        src={src}
        title={title}
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
      />
    </div>
  )
}
