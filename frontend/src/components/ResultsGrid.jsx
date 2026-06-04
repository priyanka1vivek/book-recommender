// ResultsGrid.jsx — renders the grid of BookCards, or skeleton placeholders
// while results are loading.
//
// Props:
//   results — array of book objects from the API
//   loading — boolean; when true, shows skeleton cards instead of real cards

import BookCard from './BookCard'

// A single skeleton card — a grey placeholder that pulses while data is loading.
// The shapes mimic the structure of a real BookCard so the layout doesn't jump.
function SkeletonCard({ index }) {
  return (
    <div className="skeleton-card" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="skeleton-cover" />
      <div className="skeleton-body">
        <div className="skeleton-line medium" />
        <div className="skeleton-line short" />
        <div className="skeleton-line long" style={{ marginTop: 8 }} />
        <div className="skeleton-line full" />
        <div className="skeleton-line medium" />
        <div className="skeleton-line short" style={{ marginTop: 12 }} />
      </div>
    </div>
  )
}

export default function ResultsGrid({ results, loading }) {
  // Show 6 skeleton cards while the API call is in-flight.
  if (loading) {
    return (
      <div className="books-grid" aria-label="Loading results" aria-busy="true">
        {Array.from({ length: 6 }, (_, i) => (
          <SkeletonCard key={i} index={i} />
        ))}
      </div>
    )
  }

  // If we have real results, render BookCards.
  // The index prop drives the staggered fade-up animation in BookCard.
  return (
    <div className="books-grid" aria-label={`${results.length} book recommendations`}>
      {results.map((book, i) => (
        <BookCard key={book.id} book={book} index={i} />
      ))}
    </div>
  )
}
