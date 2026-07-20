// Real, verified TV24 Studio channel data.
// Channel: https://www.youtube.com/c/TV24Studio
// Same channel ID also powers: https://music.youtube.com/channel/UCIwnaDFVtjN5_HCKkh9ymWw

export const CHANNEL_ID = "UCIwnaDFVtjN5_HCKkh9ymWw";

// YouTube convention: an "uploads" playlist ID is the channel ID with
// the "UC" prefix swapped for "UU". Embedding it gives a live, always
// up-to-date playlist of the channel's real videos.
export const UPLOADS_PLAYLIST_ID = "UU" + CHANNEL_ID.slice(2);

export const CHANNEL_URLS = {
  main: "https://www.youtube.com/c/TV24Studio",
  channel: `https://www.youtube.com/channel/${CHANNEL_ID}`,
  music: `https://music.youtube.com/channel/${CHANNEL_ID}`,
  videosTab: "https://www.youtube.com/c/TV24Studio/videos",
};

export const SOCIAL_LINKS = {
  facebook: "https://www.facebook.com/TV24NewsTelugu",
  twitter: "https://twitter.com/TV24Studio",
  instagram: "https://www.instagram.com/tv24studio",
  telegramGroup: "https://t.me/TV24StudioGroup",
  telegramChannel: "https://t.me/TV24Studio",
  youtube: "https://www.youtube.com/c/TV24Studio",
};

export const CONTACT = {
  email: "tv24.studio@gmail.com",
  phone: "+91 96662 16699",
};

// Embed helper — build a YouTube iframe src for a single video.
export const embedUrl = (videoId, opts = {}) => {
  const params = new URLSearchParams({
    rel: "0",
    modestbranding: "1",
    ...opts,
  });
  return `https://www.youtube.com/embed/${videoId}?${params.toString()}`;
};

// Embed helper — build a YouTube iframe src for the channel's live uploads playlist.
export const embedPlaylistUrl = (opts = {}) => {
  const params = new URLSearchParams({
    listType: "playlist",
    list: UPLOADS_PLAYLIST_ID,
    rel: "0",
    modestbranding: "1",
    ...opts,
  });
  return `https://www.youtube.com/embed/videoseries?${params.toString()}`;
};

// A handful of specific, verified real videos from the TV24 Studio channel,
// used as featured / highlighted content across the site.
export const FEATURED_VIDEOS = [
  {
    id: "LJv6ZpDhjDs",
    title: "TV24 Studio Special Focus on Pitapuram Bus Stop | AP 2024 Elections",
    category: "AP Politics",
    url: "https://www.youtube.com/watch?v=LJv6ZpDhjDs",
  },
  {
    id: "HeG0z5veww4",
    title: "Harsha Guntupalli On Why He Started His YouTube Channel | Janasena | Pawan Kalyan",
    category: "Janasena / Political Talk",
    url: "https://www.youtube.com/watch?v=HeG0z5veww4",
  },
  {
    id: "5_pA0EepiXQ",
    title: "TV24 Studio Special Report",
    category: "AP Politics",
    url: "https://www.youtube.com/watch?v=5_pA0EepiXQ",
  },
];

// Content categories the channel covers (from the channel's own About section).
export const CATEGORIES = [
  {
    name: "AP Politics",
    description:
      "In-depth Andhra Pradesh political news, ground reports and analysis.",
  },
  {
    name: "Janasena & Pawan Kalyan",
    description: "Speeches, updates and public opinion around Janasena Party.",
  },
  {
    name: "YSRCP / TDP Coverage",
    description: "Coverage and reactions from YSRCP, TDP and allied parties.",
  },
  {
    name: "Political Surveys & Analysis",
    description: "Public opinion surveys and expert political analysis.",
  },
  {
    name: "Tollywood & Film News",
    description: "Latest Telugu film industry news and updates.",
  },
];

export const ABOUT_TEXT = `Welcome to TV24 Studio — a Telugu Political News Channel and your destination for in-depth Andhra Pradesh political news, insightful political analysis and political public opinion. We are dedicated to providing unbiased and comprehensive coverage of the political landscape, keeping our audience informed and empowered. We also cover the latest Telugu film news and Tollywood updates.`;
