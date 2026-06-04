/*
  DiscoverMore.jsx
  ================
  "Don't see the right book?" banner at the bottom of the results page.
  Lets users pull any book from Open Library (20M+ catalog), embed it
  with the same BERT model, and store it permanently in the local database.

  WHY THIS IS A SEPARATE COMPONENT:
    It has its own isolated state (searchTerm, status, statusMsg) that is
    completely unrelated to the main search results. Mixing it into App.jsx
    would clutter the top-level state and make the code harder to reason about.

  PROPS:
    currentVibe  -- the vibe query that produced the current results,
                    so we can re-run it automatically after importing new books
    onSearch     -- App's handleSearch callback, called after a successful import
*/

import { useState }           from 'react'
import { Library, Search }    from 'lucide-react'
import { discoverBooks }      from '../api/client'

export default function DiscoverMore({ currentVibe, onSearch }) {
  const [searchTerm, setSearchTerm] = useState('')
  // 'idle' | 'loading' | 'success' | 'error'
  const [status,     setStatus]     = useState('idle')
  const [statusMsg,  setStatusMsg]  = useState('')

  async function handleDiscover() {
    if (!searchTerm.trim()) return

    setStatus('loading')
    setStatusMsg('')

    try {
      /*
        discoverBooks calls GET /api/books/discover?q=...
        The backend hits the Open Library REST API, parses the JSON,
        generates BERT embeddings for any new books, saves them to SQLite,
        and returns the full list of matching Book objects.
      */
      const newBooks = await discoverBooks(searchTerm, 8)

      setStatus('success')
      setStatusMsg(
        `Added ${newBooks.length} book${newBooks.length !== 1 ? 's' : ''} to the library. Re-running your vibe search...`
      )

      // Small delay so the user reads the success message, then re-search.
      // WHY setTimeout INSTEAD OF AWAITING THE RE-SEARCH:
      //   We want the status message to be visible for a moment before the
      //   page scrolls and results update. setTimeout gives that breathing room.
      setTimeout(() => {
        if (currentVibe) onSearch(currentVibe)
        setSearchTerm('')
        setStatus('idle')
      }, 1800)

    } catch (err) {
      setStatus('error')
      setStatusMsg(err.message || 'Could not reach Open Library. Check your connection.')
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleDiscover()
  }

  return (
    <div className="discover-banner">
      {/* Library is a Lucide icon that looks like bookshelves -- thematically appropriate */}
      <div className="discover-heading">
        <Library size={20} strokeWidth={1.5} aria-hidden="true" />
        <h3>Don't see the right book?</h3>
      </div>

      <p>
        Search our 20 million+ book catalog. Type an author name or title -- we'll
        import it, embed it with the AI model, and re-run your vibe search.
      </p>

      <div className="discover-row">
        <input
          className="discover-input"
          type="text"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='e.g. "Cormac McCarthy" or "Pachinko"'
          disabled={status === 'loading'}
          aria-label="Search Open Library catalog"
        />
        <button
          className="discover-btn"
          onClick={handleDiscover}
          disabled={!searchTerm.trim() || status === 'loading'}
        >
          <Search size={14} aria-hidden="true" />
          {status === 'loading' ? 'Importing...' : 'Import & Search'}
        </button>
      </div>

      {statusMsg && (
        <p
          className={`discover-status ${status}`}
          role="status"
          aria-live="polite"
        >
          {statusMsg}
        </p>
      )}
    </div>
  )
}
