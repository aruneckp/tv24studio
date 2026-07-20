# TV24 Studio Website

A React (Vite) website for **TV24 Studio**, a Telugu political news & entertainment
YouTube channel (492K+ subscribers, 23K+ videos). Styled with TV24 Studio's own real
brand colours — red (`#e2231a`) and gold/orange (`#f7941d`) on black — taken directly
from the channel's actual YouTube logo and banner.

## What's inside
- Home, Videos, Shows, Music, About, Contact pages (React Router)
- Real, live YouTube embeds:
  - The channel's actual "uploads" playlist (`UUIwnaDFVtjN5_HCKkh9ymWw`), which
    always reflects the real, current videos on youtube.com/c/TV24Studio
  - 3 verified, real featured videos (real video IDs) linking out to actual
    YouTube watch pages
  - Real social links (YouTube, YouTube Music, Facebook, Twitter/X, Instagram,
    Telegram) and real contact info (tv24.studio@gmail.com)
- All video/channel/social data lives in `src/data/videos.js` — edit that file
  to add more featured videos or change links.

## Run it locally
```bash
npm install
npm run dev       # dev server
npm run build     # production build -> dist/
npm run preview   # preview the production build
```

## Notes / next steps
This is a first, professional-looking pass as requested. Good next steps:
- Swap the `Featured Videos` list in `src/data/videos.js` for a larger,
  curated set once you've picked which uploads to highlight.
- Add a real logo image instead of the text-based "TV24 STUDIO" wordmark.
- Wire up a live-stream page if/when the channel runs live broadcasts.
# tv24studio
