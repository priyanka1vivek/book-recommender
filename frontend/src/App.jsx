/*
  App.jsx
  =======
  The root component. Owns every piece of shared state and passes it down
  as props to child components.

  WHY STATE LIVES HERE AND NOT IN EACH COMPONENT:
    SearchBar writes the query; ResultsGrid reads the results. They are
    siblings -- neither is a parent of the other. The only place both can
    share data is their common ancestor: App. This is React's "lift state up"
    pattern. It keeps data in one place and prevents the two components from
    getting out of sync.

  WHY useCallback FOR handleSearch:
    Without useCallback, React creates a brand-new function object on every
    render. That means SearchBar's props change every render even if the search
    logic hasn't changed, causing unnecessary re-renders. useCallback memoises
    the function and only recreates it when `language` changes (the dependency).
*/

import { useState, useCallback } from 'react'
import { BookOpen }              from 'lucide-react'
import SearchBar                 from './components/SearchBar'
import ResultsGrid               from './components/ResultsGrid'
import DiscoverMore              from './components/DiscoverMore'
import { fetchRecommendations }  from './api/client'

export default function App() {
  const [query,       setQuery]       = useState('')
  const [results,     setResults]     = useState([])
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [currentVibe, setCurrentVibe] = useState('')
  // 'all' means no language filter; 'Hindi' / 'Kannada' / 'English' = filtered
  const [language,    setLanguage]    = useState('all')

  const handleSearch = useCallback(async (searchQuery) => {
    const trimmed = (searchQuery || '').trim()
    if (!trimmed) return

    setLoading(true)
    setError(null)
    setHasSearched(true)
    setCurrentVibe(trimmed)
    window.scrollTo({ top: 340, behavior: 'smooth' })

    try {
      // Pass language to the API; 'all' becomes null (no filter in backend)
      const data = await fetchRecommendations(trimmed, 6, language === 'all' ? null : language)
      setResults(data)
    } catch (err) {
      setError(err.message)
      setResults([])
    } finally {
      setLoading(false)
    }
  // language is a dependency: if the user changes the language filter and then
  // searches, handleSearch must capture the latest language value.
  }, [language])

  return (
    <div className="app">

      {/* ── HERO ─────────────────────────────────────────────────── */}
      <header className="hero">

        <div className="hero-badge" aria-label="AI powered semantic search">
          {/* BookOpen icon makes the badge feel literary rather than generic-tech */}
          <BookOpen size={13} strokeWidth={2} aria-hidden="true" />
          AI-Powered · Semantic Search
        </div>

        <h1 className="hero-title">
          Find your next read<br />
          by <em>how it makes you feel</em>
        </h1>

        <p className="hero-subtitle">
          Describe a mood, an atmosphere, a feeling — our AI matches
          the meaning of your words to thousands of book descriptions.
        </p>

        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          loading={loading}
          language={language}
          onLanguageChange={setLanguage}
        />

      </header>

      {/* ── RESULTS ─────────────────────────────────────────────── */}
      <main className="results-section" aria-live="polite">

        {error && !loading && (
          <div className="error-banner" role="alert">
            <span aria-hidden="true">⚠</span>
            <div>
              <strong>Something went wrong.</strong><br />
              {error}<br />
              <small style={{ marginTop: 4, display: 'block' }}>
                Make sure the backend is running:{' '}
                <code>cd backend &amp;&amp; uvicorn app.main:app --port 8000</code>
              </small>
            </div>
          </div>
        )}

        {hasSearched && (loading || results.length > 0) && (
          <>
            {!loading && results.length > 0 && (
              <div className="results-header">
                <p className="results-count">
                  <strong>{results.length}</strong> books matching{' '}
                  <span className="vibe-quote">"{currentVibe}"</span>
                  {language !== 'all' && (
                    <span className="results-lang-tag"> · {language}</span>
                  )}
                </p>
                <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
                  Sorted by semantic similarity
                </span>
              </div>
            )}

            <ResultsGrid results={results} loading={loading} />

            {!loading && results.length > 0 && (
              <DiscoverMore currentVibe={currentVibe} onSearch={handleSearch} />
            )}
          </>
        )}

        {hasSearched && !loading && !error && results.length === 0 && (
          <div className="empty-state">
            <BookOpen
              size={52}
              strokeWidth={1}
              color="var(--pink-300)"
              aria-hidden="true"
              style={{ display: 'block', margin: '0 auto 16px' }}
            />
            <h2 className="empty-state-title">No matches found</h2>
            <p className="empty-state-text">
              Try rephrasing your vibe, or adjust the language filter.
              You can also use the Discover section below to import any
              specific book by title or author.
            </p>
          </div>
        )}

        {!hasSearched && (
          <div className="empty-state">
            <BookOpen
              size={52}
              strokeWidth={1}
              color="var(--pink-300)"
              aria-hidden="true"
              style={{ display: 'block', margin: '0 auto 16px', animation: 'float 4s ease-in-out infinite' }}
            />
            <h2 className="empty-state-title">Your recommendations will appear here</h2>
            <p className="empty-state-text">
              Type a vibe in the search box above, or click a suggestion
              chip to get started instantly.
            </p>
          </div>
        )}

      </main>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      {/*
        WHY NOT SHOW THE TECH STACK IN THE FOOTER:
          "Built with FastAPI · PyTorch..." reads like a project README,
          not a product. A real product footer shows brand and utility
          (link to API docs for developers) without advertising its internals.
          If someone asks how it's built, that's what the DEVELOPMENT_LOG is for.
      */}
      <footer className="footer">
        <div className="footer-inner">
          <span className="footer-brand">Book Vibe</span>
          <span className="footer-sep" aria-hidden="true">·</span>
          <span className="footer-tagline">Find your next read, one feeling at a time</span>
          <span className="footer-sep" aria-hidden="true">·</span>
          <span className="footer-tagline">open library powered</span>
        </div>
      </footer>

    </div>
  )
}
