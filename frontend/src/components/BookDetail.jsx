import { useState, useEffect }                          from 'react'
import { useParams, useNavigate, useLocation }           from 'react-router-dom'
import { ArrowLeft, BookOpen, User, CalendarDays,
         ExternalLink, Star, Globe }                     from 'lucide-react'
import { fetchBookById }                                 from '../api/client'

const GENRE_COLORS = {
  'Literary Fiction':       { bg: '#fce7f3', color: '#9d174d' },
  'Dystopian Fiction':      { bg: '#ede9fe', color: '#5b21b6' },
  'Magical Realism':        { bg: '#fef9c3', color: '#78350f' },
  'Contemporary Fiction':   { bg: '#e0f2fe', color: '#0c4a6e' },
  'Psychological Thriller': { bg: '#fee2e2', color: '#991b1b' },
  'Crime Thriller':         { bg: '#fef3c7', color: '#92400e' },
  'Domestic Thriller':      { bg: '#fff1f2', color: '#be123c' },
  'Mystery':                { bg: '#dbeafe', color: '#1e40af' },
  'Epic Fantasy':           { bg: '#d1fae5', color: '#065f46' },
  'Fantasy':                { bg: '#dcfce7', color: '#166534' },
  'Science Fiction':        { bg: '#cffafe', color: '#164e63' },
  'Comic Science Fiction':  { bg: '#fef9c3', color: '#713f12' },
  'Horror':                 { bg: '#f1f5f9', color: '#0f172a' },
  'Romance':                { bg: '#fce7f3', color: '#831843' },
  'Historical Romance':     { bg: '#fef3c7', color: '#92400e' },
  'Historical Fiction':     { bg: '#fef3c7', color: '#78350f' },
  'Non-Fiction':            { bg: '#ecfdf5', color: '#065f46' },
  'Self-Help':              { bg: '#eff6ff', color: '#1e3a8a' },
  'Inspirational Fiction':  { bg: '#fff7ed', color: '#9a3412' },
  'Satirical Fiction':      { bg: '#fef9c3', color: '#713f12' },
  'Social Fiction':         { bg: '#fdf4ff', color: '#7e22ce' },
  'Poetry':                 { bg: '#fce7f3', color: '#9d174d' },
  'Adventure':              { bg: '#ecfdf5', color: '#047857' },
}

const LANG_COLORS = {
  'Hindi':   { bg: '#fff7ed', color: '#c2410c' },
  'Kannada': { bg: '#eff6ff', color: '#1d4ed8' },
  'English': { bg: '#f0fdf4', color: '#166534' },
}

function scoreLabel(score) {
  if (score >= 0.65) return 'Excellent match'
  if (score >= 0.45) return 'Strong match'
  if (score >= 0.30) return 'Good match'
  return 'Possible match'
}

function PlaceholderCover({ title }) {
  const palettes = [
    ['#f9a8d4', '#ec4899'],
    ['#fda4af', '#f43f5e'],
    ['#fdba74', '#f97316'],
    ['#86efac', '#22c55e'],
    ['#93c5fd', '#3b82f6'],
  ]
  const [from, to] = palettes[title.length % palettes.length]
  return (
    <div
      className="detail-cover-placeholder"
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
      aria-hidden="true"
    >
      <BookOpen size={64} color="rgba(255,255,255,0.7)" strokeWidth={1.5} />
      <span>{title.charAt(0).toUpperCase()}</span>
    </div>
  )
}

export default function BookDetail() {
  const { id }       = useParams()
  const navigate     = useNavigate()
  const location     = useLocation()
  const passedScore  = location.state?.similarity_score

  const [book,        setBook]        = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [coverFailed, setCoverFailed] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchBookById(id)
      .then(setBook)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="detail-page">
        <div className="detail-container">
          <div className="detail-skeleton">
            <div className="detail-skeleton-cover" />
            <div className="detail-skeleton-body">
              <div className="skeleton-line long"  style={{ height: 14, marginBottom: 10 }} />
              <div className="skeleton-line medium" style={{ height: 32, marginBottom: 8 }} />
              <div className="skeleton-line short"  style={{ height: 14, marginBottom: 24 }} />
              <div className="skeleton-line full"   style={{ height: 12 }} />
              <div className="skeleton-line full"   style={{ height: 12, marginTop: 8 }} />
              <div className="skeleton-line medium" style={{ height: 12, marginTop: 8 }} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !book) {
    return (
      <div className="detail-page">
        <div className="detail-container">
          <button className="detail-back" onClick={() => navigate(-1)}>
            <ArrowLeft size={15} /> Back
          </button>
          <div className="detail-error">Could not load book details.</div>
        </div>
      </div>
    )
  }

  const genreStyle = GENRE_COLORS[book.genre] ?? { bg: '#f3f4f6', color: '#374151' }
  const langStyle  = LANG_COLORS[book.language]

  const goodreadsUrl = `https://www.goodreads.com/search?q=${encodeURIComponent(book.title + ' ' + book.author)}`
  const olUrl = book.ol_key
    ? `https://openlibrary.org/works/${book.ol_key}`
    : `https://openlibrary.org/search?q=${encodeURIComponent(book.title + ' ' + book.author)}`

  return (
    <div className="detail-page">
      <div className="detail-container">

        <button className="detail-back" onClick={() => navigate(-1)}>
          <ArrowLeft size={15} /> Back to results
        </button>

        <div className="detail-layout">

          {/* ── Cover ─────────────────────────────────────────── */}
          <div className="detail-cover-col">
            {book.cover_url && !coverFailed ? (
              <img
                className="detail-cover-img"
                src={book.cover_url}
                alt={`Cover of ${book.title}`}
                onError={() => setCoverFailed(true)}
              />
            ) : (
              <PlaceholderCover title={book.title} />
            )}
          </div>

          {/* ── Info ──────────────────────────────────────────── */}
          <div className="detail-info-col">

            {/* Badges row */}
            <div className="detail-badges">
              <span
                className="detail-badge"
                style={{ background: genreStyle.bg, color: genreStyle.color }}
              >
                {book.genre}
              </span>
              {book.language && langStyle && (
                <span
                  className="detail-badge"
                  style={{ background: langStyle.bg, color: langStyle.color }}
                >
                  <Globe size={11} style={{ marginRight: 3 }} />
                  {book.language}
                </span>
              )}
            </div>

            <h1 className="detail-title">{book.title}</h1>

            {/* Author + year */}
            <div className="detail-meta">
              <span className="detail-author">
                <User size={13} aria-hidden="true" />
                {book.author}
              </span>
              {book.year && (
                <span className="detail-year">
                  <CalendarDays size={13} aria-hidden="true" />
                  {book.year}
                </span>
              )}
            </div>

            {/* Match score — only shown when arriving from search results */}
            {passedScore != null && (
              <div className="detail-score-pill">
                <Star size={13} aria-hidden="true" />
                {Math.round(passedScore * 100)}% match
                <span className="detail-score-label">· {scoreLabel(passedScore)}</span>
              </div>
            )}

            {/* Full description */}
            <p className="detail-description">{book.description}</p>

            {/* External links */}
            <div className="detail-links">
              <a
                className="detail-link-btn detail-link-goodreads"
                href={goodreadsUrl}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={14} aria-hidden="true" />
                Goodreads reviews
              </a>
              {olUrl && (
                <a
                  className="detail-link-btn detail-link-ol"
                  href={olUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink size={14} aria-hidden="true" />
                  Open Library
                </a>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}
