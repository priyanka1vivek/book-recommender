/*
  api/client.js
  =============
  Every HTTP call to the FastAPI backend is defined here and nowhere else.

  WHY A DEDICATED API MODULE:
    If the backend URL, endpoint path, or request format ever changes, we
    fix it in one file. Components never construct URLs or touch fetch()
    directly -- they just call these functions and receive data.
    This is the "service layer" pattern used in large production codebases.

  WHY /api PREFIX (VITE PROXY) INSTEAD OF http://localhost:8000 DIRECTLY:
    Browsers enforce the Same-Origin Policy: a page served from port 5174
    cannot call a server on port 8000 without that server returning the right
    CORS headers. While we do have CORS configured on the backend, the proxy
    approach is more robust: it works even if CORS headers are misconfigured,
    and it mimics production where the frontend and API share one domain.
    Vite rewrites "/api/..." to "http://localhost:8000/..." at the server level
    (vite.config.js) where the Same-Origin restriction does not apply.
*/

const API_BASE = '/api'

// ---------------------------------------------------------------------------
// fetchRecommendations
// POST /recommend/vibe
// Converts a mood query into a BERT embedding server-side, finds the k
// closest book embeddings by cosine similarity, and returns them ranked.
// ---------------------------------------------------------------------------
export async function fetchRecommendations(query, k = 6, language = null) {
  /*
    WHY POST INSTEAD OF GET:
      The query string can be up to 400 chars. While GET requests can carry
      query strings, it is unusual and not well-supported for long arbitrary
      text. POST with a JSON body is the conventional choice for "send data,
      receive computed result" operations.
  */
  const body = { query, k }
  // Only include `language` in the payload when it's set; the backend
  // treats null/absent as "no filter" and a string as a language match.
  if (language) body.language = language

  const response = await fetch(`${API_BASE}/recommend/vibe`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  })

  if (!response.ok) {
    // response.json() parses the FastAPI error detail object
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${response.status}`)
  }

  return response.json()
}

// ---------------------------------------------------------------------------
// fetchBooks
// GET /books
// Returns the full local catalog (used for browsing, not vibe search).
// ---------------------------------------------------------------------------
export async function fetchBooks(limit = 100) {
  const response = await fetch(`${API_BASE}/books/?limit=${limit}`)
  if (!response.ok) throw new Error(`Server error ${response.status}`)
  return response.json()
}

// ---------------------------------------------------------------------------
// discoverBooks
// GET /books/discover?q=...
// Searches Open Library, embeds any new books found, and saves them
// permanently to the local database so future vibe searches can find them.
// ---------------------------------------------------------------------------
export async function discoverBooks(query, limit = 8) {
  /*
    URLSearchParams encodes the query string safely -- spaces become %20,
    ampersands are escaped, etc. Never concatenate user input directly into
    a URL string: it can break the request or (in web apps) cause injection.
  */
  const params   = new URLSearchParams({ q: query, limit })
  const response = await fetch(`${API_BASE}/books/discover?${params}`)

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${response.status}`)
  }

  return response.json()
}
