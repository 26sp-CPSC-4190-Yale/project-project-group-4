export const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export const SWIPE_THRESHOLD = 80

export const FALLBACK_IMAGE = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="530" fill="#161616">' +
  '<rect width="400" height="530"/>' +
  '<text x="50%" y="50%" text-anchor="middle" fill="#444" font-size="16" dy=".3em">' +
  'Image not available</text></svg>'
)
