/*
  BookCard.jsx
  ============
  Displays one recommended book: cover image, title, author, genre badge,
  description, and an animated match-score bar.

  WHY A SEPARATE COMPONENT:
    The same card structure is reused 6 times per search result. React's
    component model lets us define it once and render it N times by mapping
    over the results array. Any styling change here automatically applies to
    all cards -- no copy-pasting.

  PROPS:
    book  -- object from the API: { id, title, author, description, genre,
                                    language, year, cover_url, similarity_score }
    index -- 0-based position in the grid, used to stagger the fade-in animation
*/

import { useState }                from 'react'
import { BookOpen, CalendarDays }  from 'lucide-react'
import { useNavigate }             from 'react-router-dom'

// ---------------------------------------------------------------------------
// Genre colour mapping
// WHY NOT A SINGLE COLOUR FOR ALL GENRES:
//   Different genres evoke different feelings. Horror should feel darker
//   than romance; sci-fi should feel cooler than historical fiction.
//   A subtle bg/text pair per genre lets users visually parse results at
//   a glance without having to read the badge text.
// ---------------------------------------------------------------------------
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

// Language badge colours -- distinct from genre badges
const LANG_COLORS = {
  'Hindi':   { bg: '#fff7ed', color: '#c2410c' },
  'Kannada': { bg: '#eff6ff', color: '#1d4ed8' },
  'English': { bg: '#f0fdf4', color: '#166534' },
}

// Converts similarity score (0.0 to 1.0) into a human-readable quality label.
// WHY INCLUDE A LABEL AND NOT JUST A NUMBER:
//   "0.46" means nothing to most people. "Strong match" is immediately
//   understood. The number is still shown for those who want precision.
function scoreLabel(score) {
  if (score >= 0.65) return 'Excellent match'
  if (score >= 0.45) return 'Strong match'
  if (score >= 0.30) return 'Good match'
  return 'Possible match'
}

// Gradient placeholder shown when a book has no cover URL or when the
// cover image fails to load (404, network error, etc.)
// WHY FIRST LETTER + GRADIENT instead of a generic broken-image icon:
//   It's branded and unique per book. Users can still tell cards apart
//   even without covers.
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
      className="book-cover-placeholder"
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
      aria-hidden="true"
    >
      {/* BookOpen icon from Lucide -- more meaningful than a bare letter */}
      <BookOpen size={40} color="rgba(255,255,255,0.7)" strokeWidth={1.5} />
      <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'rgba(255,255,255,0.9)', marginTop: 6 }}>
        {title.charAt(0).toUpperCase()}
      </span>
    </div>
  )
}

export default function BookCard({ book, index }) {
  const navigate     = useNavigate()
  const [coverFailed, setCoverFailed] = useState(false)

  const pct        = Math.round((book.similarity_score ?? 0) * 100)
  const genreStyle = GENRE_COLORS[book.genre] ?? { bg: '#f3f4f6', color: '#374151' }
  const langStyle  = LANG_COLORS[book.language]
  const animationDelay = `${index * 80}ms`

  function openDetail() {
    navigate(`/book/${book.id}`, { state: { similarity_score: book.similarity_score } })
  }

  return (
    <article
      className="book-card"
      style={{ animationDelay, cursor: 'pointer' }}
      aria-label={`${book.title} by ${book.author} — click to view details`}
      onClick={openDetail}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') openDetail() }}
      tabIndex={0}
      role="button"
    >

      {/* ---- Cover image area ----------------------------------------- */}
      <div className="book-cover-wrap">
        {book.cover_url && !coverFailed ? (
          <img
            className="book-cover-img"
            src={book.cover_url}
            alt={`Cover of ${book.title}`}
            onError={() => setCoverFailed(true)}
          />
        ) : (
          <PlaceholderCover title={book.title} />
        )}

        {/* Genre badge -- absolute-positioned on top of the cover */}
        <span
          className="genre-badge"
          style={{ background: genreStyle.bg, color: genreStyle.color }}
        >
          {book.genre}
        </span>

        {/* Language badge (only shown for non-English books) */}
        {book.language && book.language !== 'English' && langStyle && (
          <span
            className="lang-badge"
            style={{ background: langStyle.bg, color: langStyle.color }}
          >
            {book.language}
          </span>
        )}
      </div>

      {/* ---- Text body ------------------------------------------------ */}
      <div className="book-body">
        <h2 className="book-title">{book.title}</h2>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span className="book-author">{book.author}</span>
          {book.year && (
            <span className="book-year" style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              {/* CalendarDays icon is more legible than a bare year number */}
              <CalendarDays size={11} aria-hidden="true" />
              {book.year}
            </span>
          )}
        </div>

        <p className="book-description">{book.description}</p>

        {/* ---- Match score bar ---------------------------------------- */}
        {/*
          WHY A PROGRESS BAR AND NOT JUST A NUMBER:
            Visual encoding (length) is processed ~10x faster by the human
            brain than a numeric value. Users can compare five cards in a
            single glance instead of reading five numbers individually.

          HOW THE ANIMATION WORKS:
            The bar starts at width 0 (from CSS animation), then CSS
            transitions it to the inline `width: pct%` value over 0.8s.
            The browser handles all the interpolation -- no JS timers needed.
        */}
        <div className="score-section">
          <div className="score-header">
            <span className="score-label">Match Score</span>
            <span className="score-value">
              {pct}%
              <span className="score-qualifier"> · {scoreLabel(book.similarity_score)}</span>
            </span>
          </div>
          <div
            className="score-track"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${pct}% match`}
          >
            <div className="score-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>

    </article>
  )
}
