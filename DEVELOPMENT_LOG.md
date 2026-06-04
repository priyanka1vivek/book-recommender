# Book Recommender — Development Log

> **Purpose of this file:** A living record of every major architectural decision made during this project — what we chose, what we rejected, and exactly why. Written so anyone (including you in an interview) can explain every line of the stack with confidence.

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Tech Stack Decisions](#2-tech-stack-decisions)
3. [Project Structure](#3-project-structure)
4. [The AI/ML Pipeline Explained](#4-the-aiml-pipeline-explained)
5. [Why This Stack Is Resume-Worthy](#5-why-this-stack-is-resume-worthy)
6. [Development Phases](#6-development-phases)

---

## 1. Project Vision

A full-stack application that recommends books to users in two distinct ways:

| Feature | Description |
|---|---|
| **Classic Recommendations** | Filter/sort by genre, rating, publication year — standard catalog browsing. |
| **"Vibe Check" Semantic Search** | User types a free-form feeling ("books that feel like a rainy afternoon in a bookshop") and the system finds books whose *meaning* matches, not just their keywords. |

The Vibe Check feature is the distinguishing ML component. It uses real sentence embeddings and vector similarity search — the same foundational technology behind ChatGPT's retrieval and Spotify's "recommended for you" systems.

---

## 2. Tech Stack Decisions

### Backend — Python + FastAPI

**Chosen:** `FastAPI 0.111`
**Rejected:** Flask, Django, Node.js/Express

| Criterion | FastAPI | Flask | Django | Express |
|---|---|---|---|---|
| Auto-generated API docs (Swagger UI) | Yes | No | No | No |
| Async/await native | Yes | No (workaround) | No (ASGI addon) | Yes |
| Type safety via Pydantic | Built-in | Manual | Manual | Manual |
| ML ecosystem (Python) | Native | Native | Native | None |
| Learning curve | Low | Low | High | Medium |

**Why FastAPI wins:** The ML libraries (`sentence-transformers`, `chromadb`) are Python-only. FastAPI is the modern Python API framework — it is what major tech companies (Uber, Netflix microservices, Doordash) use. It auto-generates interactive Swagger docs at `/docs`, meaning anyone can test the API without writing a single line of client code. Flask is too barebones; Django is MVC-oriented and brings an ORM, admin panel, and template engine we do not need.

---

### Relational Database — SQLite via SQLAlchemy ORM

**Chosen:** `SQLite` (file-based) + `SQLAlchemy 2.0` ORM
**Rejected:** PostgreSQL, MySQL, MongoDB

SQLite writes to a single `.db` file — zero installation, zero configuration, runs on any machine. For a local-first portfolio project this is the correct choice. The SQLAlchemy ORM layer means the code is **identical** to what would run against PostgreSQL in production; swapping databases requires changing exactly one line (`DATABASE_URL`). This is worth knowing in an interview: "I used SQLite locally but abstracted it through SQLAlchemy so it is production-portable."

MongoDB was rejected because our data (books, genres, ratings) is naturally relational — relationships between tables are exactly what a relational database is designed for.

---

### Vector Database — ChromaDB

**Chosen:** `ChromaDB 0.5` (embedded mode, file-based)
**Rejected:** Pinecone, Qdrant, pgvector, FAISS

ChromaDB is the only vector store that:
- Runs **embedded** (no separate server process, just a folder on disk)
- Persists data between restarts automatically
- Has a clean Python API with no account or API key required
- Is production-ready (also offers a hosted cloud version)

FAISS (Meta's library) is faster but does not persist to disk without manual serialization code. Pinecone and Qdrant require running separate server processes or cloud accounts. ChromaDB is the right local-first choice.

**What a vector database actually does:** Instead of storing text, it stores lists of ~384 floating-point numbers (vectors) that encode the *meaning* of text. Searching is done by finding vectors that are geometrically close in that 384-dimensional space — which corresponds to semantic similarity.

---

### Embedding Model — Sentence-Transformers (all-MiniLM-L6-v2)

**Chosen:** `sentence-transformers` library, model `all-MiniLM-L6-v2`
**Rejected:** OpenAI `text-embedding-ada-002`, Cohere Embed, custom fine-tuned model

`all-MiniLM-L6-v2` is a distilled transformer model (based on the same BERT architecture as early GPT) that produces 384-dimensional sentence embeddings. It:
- Runs **100% locally** — no API key, no latency, no cost per query
- Downloads once (~90 MB) and caches on disk
- Achieves near-state-of-the-art semantic similarity performance for its size
- Is the most-downloaded sentence embedding model on HuggingFace (100M+ downloads)

OpenAI embeddings are more accurate but cost money per call and require an internet connection. For a demo portfolio project, local inference is strictly better.

**How it fits into the Vibe Check feature:** Each book's title + description is passed through the model once at seed time, producing a vector that is stored in ChromaDB. At query time, the user's input phrase is embedded the same way, and ChromaDB returns the `k` nearest book vectors — the semantic matches.

---

### Frontend — React 18 + Vite

**Chosen:** React 18 with Vite build tool
**Rejected:** Vanilla HTML/JS/CSS, Next.js, Vue, Angular

| Option | Verdict | Reason |
|---|---|---|
| Vanilla JS | Too simple for a resume | No component model, no state management — fine for scripts, not for apps |
| Next.js | Overkill | SSR/SSG is for deployed production sites; adds build complexity we do not need locally |
| Vue | Good alternative | Smaller ecosystem, harder to discuss in interviews vs React |
| Angular | Overkill | Enterprise framework; steep learning curve; too verbose for this scope |
| **React + Vite** | **Chosen** | Industry-standard component model, huge ecosystem, Vite's dev server is instant |

React is the most-used frontend framework in job postings. Vite replaces the old Create React App toolchain — it is dramatically faster (cold start in <1 second vs 10+ seconds). The combination is the current industry default for new projects.

---

## 3. Project Structure

```
book-recommender/
│
├── backend/                        # Python FastAPI application
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point, mounts all routers
│   │   ├── database.py             # SQLAlchemy engine + session factory
│   │   ├── models/
│   │   │   └── book.py             # SQLAlchemy ORM models (Book, Genre, Rating)
│   │   ├── routers/
│   │   │   ├── books.py            # CRUD endpoints: GET /books, GET /books/{id}
│   │   │   └── recommendations.py  # POST /recommend/vibe  (semantic search)
│   │   └── services/
│   │       ├── embeddings.py       # Loads the sentence-transformer model, encodes text
│   │       └── recommender.py      # ChromaDB query logic, result ranking
│   │
│   ├── data/
│   │   └── books.db                # SQLite database file (git-ignored)
│   ├── chroma_db/                  # ChromaDB vector index (git-ignored)
│   ├── seed.py                     # One-time script: populates DB + builds vector index
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                       # React + Vite application
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js           # Axios/fetch wrappers for each backend endpoint
│   │   ├── components/
│   │   │   ├── BookCard.jsx        # Single book display card
│   │   │   ├── SearchBar.jsx       # Vibe Check input field
│   │   │   └── RecommendationList.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx            # Landing page + featured books
│   │   │   └── Discover.jsx        # Vibe Check search page
│   │   ├── hooks/
│   │   │   └── useBooks.js         # Custom React hook for data fetching
│   │   ├── App.jsx                 # Root component, router setup
│   │   └── main.jsx                # React DOM entry point
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── DEVELOPMENT_LOG.md              # This file
├── .gitignore
└── README.md
```

### Separation of concerns

The `services/` layer is deliberate. The router files only handle HTTP concerns (request parsing, response shaping). All business logic — querying ChromaDB, ranking results, running the embedding model — lives in `services/`. This mirrors real-world production code and is a pattern you can discuss in interviews.

---

## 4. The AI/ML Pipeline Explained

This is the part that makes this project stand out. Here is the exact flow for a Vibe Check search query, from frontend to response:

```
User types: "books that feel like a quiet Sunday morning"
        │
        ▼
[React frontend]
  POST /recommend/vibe
  body: { "query": "books that feel like a quiet Sunday morning", "k": 5 }
        │
        ▼
[FastAPI router — recommendations.py]
  Receives request, validates schema with Pydantic
        │
        ▼
[services/embeddings.py]
  sentence-transformers model encodes the query string
  → produces a float[384] vector, e.g. [0.021, -0.134, ..., 0.087]
        │
        ▼
[services/recommender.py]
  ChromaDB collection.query(query_embeddings=[vector], n_results=5)
  ChromaDB computes cosine similarity between query vector
  and every book vector in the index
  → returns the 5 closest matches with similarity scores
        │
        ▼
[FastAPI router]
  Fetches full book details from SQLite for each returned ID
  Returns JSON: list of books with title, author, cover, score
        │
        ▼
[React frontend]
  Renders <RecommendationList /> with results
```

**Cosine similarity** is the distance metric: it measures the angle between two vectors in the 384-dimensional space. An angle of 0° means identical meaning; 90° means unrelated. Semantically similar sentences cluster close together because the transformer was trained on millions of sentence pairs.

---

## 5. Why This Stack Is Resume-Worthy

When a recruiter or interviewer asks "walk me through your project," you can say:

> "I built a full-stack book recommender with a semantic search feature I called Vibe Check. The backend is Python FastAPI — I chose it over Flask because it has native async support and generates Swagger docs automatically. For the recommendation engine, I used a locally-running sentence transformer model to encode book descriptions into 384-dimensional embedding vectors, which I stored in ChromaDB, an embedded vector database. When a user types a free-form query, the system embeds their phrase using the same model and finds the geometrically nearest book vectors using cosine similarity. It's the same core idea behind how Spotify's 'Discover Weekly' and semantic search features in large language models work. The frontend is React with Vite — I kept it decoupled from the backend so either side can be swapped independently."

That answer demonstrates:
- Understanding of the full HTTP request lifecycle
- Knowledge of transformer-based embeddings (genuine ML, not a wrapper API)
- Understanding of vector similarity search
- Architectural reasoning (why FastAPI over Flask, why SQLite over Postgres locally)
- Awareness of real-world systems that use the same techniques

---

## 6. Development Phases

| Phase | Status | Description |
|---|---|---|
| 1. Foundation | **Complete** | Folder structure, stack decisions, this log |
| 2. Backend Core | **Complete** | FastAPI app, models, DB, embeddings, seed, live API |
| 3. Frontend | **Complete** | React + Vite, Lucide icons, language filter, all verified |
| 4. Polish | **Complete** | Icons, footer, Hindi/Kannada support, full docs |

---

## Phase 2 — Backend Core (Complete)

### What was built

| File | What it does |
|---|---|
| [`backend/app/database.py`](backend/app/database.py) | SQLAlchemy engine + session factory for SQLite |
| [`backend/app/models/book.py`](backend/app/models/book.py) | Book table: title, author, description, genre, embedding |
| [`backend/app/services/embeddings.py`](backend/app/services/embeddings.py) | Loads BERT model, converts text → 384-float vectors |
| [`backend/app/services/recommender.py`](backend/app/services/recommender.py) | numpy cosine similarity search over all stored embeddings |
| [`backend/app/services/openlibrary.py`](backend/app/services/openlibrary.py) | Queries openlibrary.org, embeds + imports any book found |
| [`backend/app/routers/books.py`](backend/app/routers/books.py) | `GET /books`, `GET /books/{id}`, `GET /books/discover` |
| [`backend/app/routers/recommendations.py`](backend/app/routers/recommendations.py) | `POST /recommend/vibe` — the AI search endpoint |
| [`backend/app/main.py`](backend/app/main.py) | FastAPI app, CORS, router registration |
| [`backend/seed.py`](backend/seed.py) | One-time script: inserts 30 books and builds the vector index |

---

### How the AI matching works (plain English)

Imagine you had to describe 30,000 books to a very smart librarian, and then ask them to find which books *feel like* a query you typed. The librarian would have to read every description and judge: *how close in spirit is this book to what you asked for?*

That is exactly what this system does — automatically, in milliseconds.

#### Step 1 — Teaching books to "speak numbers"

When you run `seed.py`, every book's title, author, genre, and description is fed into a neural network called `all-MiniLM-L6-v2` (a small version of the same BERT model that powers Google Search). The network has been trained on over 1 billion sentences from the internet and knows the *meaning* of words — not just the letters.

The network turns each piece of text into a list of **384 numbers**. These 384 numbers are not random — they encode meaning in a mathematical space where similar ideas are close together. For example, the numbers for "mystery detective rainy night" will be very similar to the numbers for "In the Woods" (a rainy Dublin detective novel).

This list of 384 numbers is called an **embedding**. It is the book's mathematical fingerprint and is stored in the SQLite database.

#### Step 2 — Turning a query into the same language

When you call `POST /recommend/vibe` with `"dark rainy detective story"`, the **exact same neural network** converts your query into a 384-number embedding. Because it is the same model, things that mean similar things produce similar numbers.

#### Step 3 — Finding the closest books

The system loads all 30 book embeddings into a 30×384 grid of numbers (a matrix). It then multiplies this matrix by your query vector in a single numpy operation:

```
similarity_scores = book_matrix  @  query_vector
```

Each result is a number between 0 and 1 — the **cosine similarity**. A score of 0.46 means "these meanings are in the same direction in the 384-dimensional space." The top 5 highest scores are your recommendations.

This is a shortcut that works because all embeddings are **L2-normalized** (scaled to length 1.0). When two unit vectors are multiplied together, the result directly equals their cosine similarity. One matrix multiply → all similarities at once.

#### Why it works for any language, not just keywords

Traditional search (like a library catalog) looks for exact words. If you search "melancholy", it only finds books containing the word "melancholy." If the description says "heartbreaking", it misses.

Embedding-based search understands that "melancholy", "heartbreaking", "sad", "grief", and "loss" all mean related things. A query about "dark atmospheric Scandinavian crime" finds *In the Woods* (set in Dublin, not Scandinavia) because the emotional tone and genre match — not because the words match.

#### Live proof (from actual test run)

| Query | #1 Result | Why it's correct |
|---|---|---|
| "dark rainy detective story" | In the Woods | Dublin detective novel, Irish rain and dread, unsolved childhood trauma |
| "funny space adventure sarcastic humor" | Hitchhiker's Guide to the Galaxy | Literally the funniest space comedy ever written |
| "heartbreaking love story that makes you cry" | The Notebook | Devotion, memory, dementia, tears — exact match |

---

### Libraries used

| Library | Version | Role |
|---|---|---|
| `fastapi` | 0.125.0 | HTTP API framework — routes, validation, auto Swagger docs |
| `pydantic` | 2.13.4 | Request/response schemas and data validation |
| `uvicorn` | latest | ASGI server that runs the FastAPI app |
| `sqlalchemy` | 2.x | ORM — translates Python classes to SQL tables |
| `torch` | 2.12.0+cpu | PyTorch neural network runtime (CPU-only build) |
| `transformers` | 4.x | HuggingFace library to load and run BERT models |
| `numpy` | 2.4.6 | Matrix math for cosine similarity search |
| `httpx` | 0.27.x | HTTP client for Open Library API calls |
| `python-dotenv` | 1.x | Reads `.env` config file |

> **Note on Python 3.14 compatibility:** This project was built on Python 3.14 (released Oct 2025). Two originally planned libraries had no pre-built wheels yet: `sentence-transformers` (scikit-learn DLL blocked by Windows Application Control) and `chroma-hnswlib` (no cp314 wheel). The solutions:
> - Replaced `sentence-transformers` with `transformers` + manual mean-pooling — produces **identical embeddings**, just more explicit code
> - Replaced `ChromaDB` with `numpy` matrix math — same algorithm (cosine similarity), stores embeddings in SQLite instead

---

### Key code annotated

#### The embedding function (services/embeddings.py)

```python
def _mean_pool(token_embeddings, attention_mask):
    # The model produces one embedding per TOKEN (word piece).
    # We want one embedding per SENTENCE — so we average all token embeddings,
    # using the attention mask to ignore padding tokens.
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask

def embed_text(text):
    encoded = tokenizer([text], padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():              # turn off gradient tracking — saves memory
        output = model(**encoded)
    embedding = _mean_pool(output.last_hidden_state, encoded["attention_mask"])
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)  # L2 normalize
    return embedding[0].numpy().tolist()   # return as plain Python list
```

#### The similarity search (services/recommender.py)

```python
def query_similar_books(query_embedding, db, k=5):
    books = db.query(Book).filter(Book.embedding_json.isnot(None)).all()
    matrix = np.array([json.loads(b.embedding_json) for b in books])  # shape (N, 384)
    query_vec = np.array(query_embedding)                               # shape (384,)

    # Because embeddings are L2-normalized:
    #   cosine_similarity(a, b) = dot_product(a, b)
    # One matrix multiply gives all N similarity scores simultaneously.
    similarities = matrix @ query_vec                                   # shape (N,)

    top_indices = np.argsort(similarities)[::-1][:min(k, len(books))]
    return [{"book_id": books[i].id, "similarity_score": float(similarities[i])} for i in top_indices]
```

#### The API endpoint (routers/recommendations.py)

```python
@router.post("/vibe", response_model=list[BookRecommendation])
def vibe_check(request: VibeRequest, db: Session = Depends(get_db)):
    query_embedding = embed_text(request.query)          # query → 384-float vector
    similar = query_similar_books(query_embedding, db=db, k=request.k)  # find top k
    results = []
    for match in similar:
        book = db.query(Book).filter(Book.id == match["book_id"]).first()
        if book:
            results.append(BookRecommendation(**book.__dict__, similarity_score=match["similarity_score"]))
    return results
```

---

*Last updated: Phase 2 — Backend Core complete. Server tested live, all endpoints verified.*

---

## Phase 3 — Frontend (Complete)

### What was built

| File | What it does |
|---|---|
| [`frontend/src/App.jsx`](frontend/src/App.jsx) | Root component — owns all state, passes props down, handles search |
| [`frontend/src/api/client.js`](frontend/src/api/client.js) | All API calls in one place — `fetchRecommendations`, `discoverBooks` |
| [`frontend/src/components/SearchBar.jsx`](frontend/src/components/SearchBar.jsx) | Textarea, suggestion chips, character count, submit button |
| [`frontend/src/components/BookCard.jsx`](frontend/src/components/BookCard.jsx) | One card: cover image, title, author, genre badge, match score bar |
| [`frontend/src/components/ResultsGrid.jsx`](frontend/src/components/ResultsGrid.jsx) | CSS Grid wrapper — shows skeleton shimmer while loading, real cards when done |
| [`frontend/src/components/DiscoverMore.jsx`](frontend/src/components/DiscoverMore.jsx) | "Don't see it?" banner — imports books from Open Library, re-searches |
| [`frontend/src/index.css`](frontend/src/index.css) | Full design system: CSS variables, Playfair Display, pink palette, animations |
| [`frontend/vite.config.js`](frontend/vite.config.js) | Vite proxy — rewrites `/api/*` to `http://localhost:8000/*`, no CORS issues |

---

### Design choices

**Colour palette:** Everything derives from a single set of CSS custom properties in `index.css`. Changing four lines recolours the entire app.

```css
--pink-50:  #fdf2f8;  /* page background */
--pink-300: #f9a8d4;  /* score bars, decorative accents */
--pink-500: #ec4899;  /* primary button, links, italic headline */
--pink-600: #db2777;  /* button active, genre badge text */
```

**Typography:** Two Google Fonts loaded once in `index.html`:
- `Playfair Display` — elegant serif used for all headings and the italic hero phrase. Gives the app a literary, book-shop feel.
- `Inter` — clean modern sans-serif for body text, labels, and UI. Maximum readability at small sizes.

**Extra features added:**
- **Suggestion chips** — 8 pre-made vibes that fill the textarea and search immediately on click
- **Active chip highlight** — the selected chip turns solid pink so users know which vibe is active
- **Staggered card animation** — each card fades in 80 ms after the previous, creating a "rolling in" effect with zero animation libraries
- **Skeleton loading** — 6 pulsing placeholder cards appear instantly while waiting for the API, preventing layout shift
- **Genre color coding** — each genre has its own soft background/text color pair (19 genres mapped)
- **Match quality label** — score shown as both `46%` and `· Strong match` so it reads at a glance
- **Cover fallback** — books with broken or missing cover images show a gradient placeholder with the book's first letter
- **Discover More banner** — searches Open Library's 20M-book catalog, embeds new books, re-runs the vibe search automatically
- **Keyboard shortcut** — pressing Enter (without Shift) inside the textarea submits the search

---

### How the UI talks to the backend (plain English)

#### The whole journey of one search

```
You type: "heartbreaking love story"  →  press Enter or click "Find My Books"
          │
          ▼
[SearchBar.jsx  onSearch("heartbreaking love story")]
  The React component calls the handler function App gave it as a prop.
          │
          ▼
[App.jsx  handleSearch("heartbreaking love story")]
  Sets loading=true → skeleton cards appear instantly.
  Calls fetchRecommendations("heartbreaking love story", 6).
          │
          ▼
[api/client.js  fetchRecommendations()]
  Sends HTTP POST to /api/recommend/vibe with body:
    { "query": "heartbreaking love story", "k": 6 }
          │
          ▼ (Vite proxy: /api → http://localhost:8000)
          │
[FastAPI backend  POST /recommend/vibe]
  Embeds the query string → 384-float vector.
  numpy matrix multiply → top 6 cosine similarities.
  Looks up book details from SQLite.
  Returns JSON array of 6 book objects.
          │
          ▼
[api/client.js  response.json()]
  Parses the JSON. Returns the array to App.jsx.
          │
          ▼
[App.jsx  setResults(data)]
  React re-renders. loading=false → skeleton cards disappear.
  The real BookCards animate in with staggered fadeUp.
          │
          ▼
[ResultsGrid.jsx  → BookCard.jsx × 6]
  Each card renders: cover image, title, author, genre badge,
  description, and an animated pink score bar.
```

#### Why Vite's proxy matters

Without the proxy, the browser's security rules (Same-Origin Policy) would block the React app on port 5174 from calling the API on port 8000. This is called a CORS error.

The proxy sidesteps this entirely: from the browser's perspective, it's calling the same origin (`localhost:5174/api/...`). Vite silently rewrites these requests to `localhost:8000/...` at the server level, where CORS rules don't apply.

In production (a real deployed site), the frontend and backend would typically be served from the same domain, so the proxy isn't needed — but configuring it during development is the professional, production-like approach.

---

### Key code annotated

#### State management in App.jsx

```jsx
// React's useState hook creates a piece of memory that persists across renders.
// When you call the setter (setResults, setLoading), React re-renders the component
// with the new value — the UI updates automatically.

const [query,       setQuery]       = useState('')     // what's typed in the textarea
const [results,     setResults]     = useState([])     // array of book objects from API
const [loading,     setLoading]     = useState(false)  // true while API call is in-flight
const [hasSearched, setHasSearched] = useState(false)  // have we searched at least once?
const [currentVibe, setCurrentVibe] = useState('')     // the vibe that produced current results
```

#### Controlled textarea (SearchBar.jsx)

```jsx
// A "controlled" input in React means React owns the value — the textarea
// doesn't manage its own state. Every keystroke:
//   1. Fires onChange
//   2. Calls onQueryChange (which is App's setQuery)
//   3. React re-renders with the new value
// This is why query.length always equals what's in the box — they're the same thing.

<textarea
  value={query}                          // React controls the displayed value
  onChange={(e) => onQueryChange(e.target.value.slice(0, MAX_CHARS))}
  onKeyDown={handleKeyDown}             // Enter key = submit
/>
```

#### Staggered animation (BookCard.jsx)

```jsx
// No animation library needed. We just delay each card's CSS animation
// by 80ms × its position. The browser handles the rest.
// Card 0 appears at 0ms, card 1 at 80ms, card 2 at 160ms, etc.

const animationDelay = `${index * 80}ms`

<article className="book-card" style={{ animationDelay }}>
```

```css
/* The animation itself — defined once in CSS */
.book-card {
  animation: fadeUp 0.4s ease both;  /* 'both' = apply start/end state */
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

#### The score bar fill (BookCard.jsx + index.css)

```jsx
// similarity_score is 0.0–1.0 from the API.
// We multiply by 100 and round for the percentage display.
// The bar width is set inline — CSS then transitions it smoothly on mount.

const pct = Math.round((book.similarity_score ?? 0) * 100)

<div className="score-track">
  <div className="score-fill" style={{ width: `${pct}%` }} />
</div>
```

```css
/* The transition makes the bar "grow" from 0 to its final width over 0.8s */
.score-fill {
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(90deg, var(--pink-300) 0%, var(--pink-500) 100%);
}
```

---

### Live test results (verified in browser)

| Query | #1 Book | Score |
|---|---|---|
| "dark rainy detective story" | In the Woods | 46% Strong match |
| "dark detective mystery" | In the Woods | 46% Strong match |
| "heartbreaking love story" | The Notebook | 49% Strong match |
| "funny space adventure" | Hitchhiker's Guide | 49% Strong match |

---

### To run the full stack

```
# Terminal 1 — backend
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
# → http://localhost:5174
```

---

*Last updated: Phase 3 — Frontend complete. Full stack running and verified in browser.*

---

## Phase 4 — Polish & Full Documentation

### Changes in this phase

| What changed | Why |
|---|---|
| Replaced all emoji with Lucide React icons | Emoji render differently per OS; SVG icons are identical everywhere |
| Redesigned footer as branded "Book Vibe" footer | Tech-stack credits read like a README, not a product |
| Added Hindi and Kannada book support | 10 curated books (5 Hindi, 5 Kannada) across major Indian literary genres |
| Added language filter tabs to the search card | Users can narrow vibe searches to a specific language pool |
| Added `language` column to the SQLite schema | Enables language filtering at the database query level |
| Added language badges on book covers | Immediately tells users a book is Hindi or Kannada without reading the card |
| Full code documentation throughout all files | Every decision explained with the reasoning, not just the what |

---

### Why Lucide React, and not the alternatives

When picking an icon library, there are three common choices. Here is why each was evaluated:

| Library | Why rejected / chosen |
|---|---|
| **Font Awesome** | Ships as a font file + CSS. Icons are characters, not SVGs. They blur at non-standard sizes and cannot be styled with CSS `color` alone — you need specific FA class names. Requires a separate CDN link or npm package that adds \~150 KB to the bundle. |
| **Material Icons (Google)** | Designed for Material Design (Google's design system). They have a very specific visual language — rounded, filled blobs — that clashes with the light, delicate aesthetic of this app. They also require a separate Google Fonts import. |
| **Heroicons (Tailwind team)** | Excellent alternative. Would have worked fine. Rejected because the icon set is smaller (\~300 icons vs Lucide's 1400+) and the stroke weights are heavier, making them harder to pair with the thin Playfair Display typeface. |
| **Lucide React** | **Chosen.** Pure SVG components — each icon is one React component that accepts `size`, `strokeWidth`, and `color` as props. They are tree-shaken at build time (only the icons you import are included). The design is clean and consistent at every size. They inherit CSS `color` naturally so they match the pink palette without any extra work. |

```jsx
// How Lucide icons work in React:
import { CloudRain } from 'lucide-react'

// Renders a 13×13 SVG with stroke color inherited from CSS
<CloudRain size={13} strokeWidth={2} aria-hidden="true" />
```

---

### Why CSS Custom Properties, not Tailwind CSS

Tailwind CSS is a utility-class framework. It is popular and excellent for rapid prototyping. It was evaluated and rejected for this project for specific reasons:

**Why Tailwind was rejected:**
- Tailwind requires a PostCSS build step. Adding PostCSS to Vite for a project that has a Python ML backend and specific Python version constraints introduces an additional failure point in the setup.
- Tailwind class names like `bg-pink-50 hover:bg-pink-100 border border-pink-200 rounded-full text-pink-600 text-xs font-semibold px-3 py-1.5` on a single `<button>` are harder to read and explain to a non-coder than a class name like `chip`.
- Tailwind makes it difficult to use dynamic values (e.g. `animationDelay: index * 80 + 'ms'`). You need either JIT mode configuration or inline styles anyway for dynamic values.

**Why CSS Custom Properties were chosen:**
- Zero dependencies. No build step change.
- The entire colour palette is defined in one block in `:root {}`. To change the primary colour of the whole app, you change one line: `--pink-500: #ec4899`.
- Class names describe *what the element is* (`chip`, `genre-badge`, `score-fill`) rather than *what it looks like* (`rounded-full bg-pink-50 text-pink-600`). This is more readable and more maintainable.
- Custom properties cascade and inherit like any CSS property, so a parent's `color` variable automatically applies to child icons without extra work.

```css
/* The whole design system in one block -- change here, changes everywhere */
:root {
  --pink-500: #ec4899;   /* primary button, badge text, italic headline */
  --pink-50:  #fdf2f8;   /* page background */
  --font-heading: 'Playfair Display', serif;
}

/* Icons inherit the CSS color of their parent automatically */
.hero-badge { color: var(--pink-600); }
/* BookOpen icon inside hero-badge renders in --pink-600 with no extra CSS */
```

---

### Why "controlled" inputs in React

There are two ways to handle form inputs in React: controlled and uncontrolled.

**Uncontrolled** means the browser manages the input's value. You read it via `ref.current.value` when you need it. This is how plain HTML forms work.

**Controlled** means React manages the value. Every keystroke fires `onChange`, which calls `setQuery(e.target.value)`, which causes a re-render, which sets the textarea's `value` prop to the new string.

This project uses controlled inputs. Here is why:

```jsx
// Controlled textarea
<textarea
  value={query}                              // React owns the value
  onChange={e => onQueryChange(e.target.value)}  // every keystroke updates state
/>
```

Benefits in this project specifically:
- **Character count is always accurate**: `charsLeft = MAX_CHARS - query.length` is computed from the same state React renders. There is no way for it to get out of sync.
- **The "active chip" highlight works**: `className={chip === query ? 'active' : ''}` only works if `query` is in React state. With an uncontrolled input, we wouldn't have the current value without reading the DOM.
- **Clearing the textarea after a discover import**: `setSearchTerm('')` sets it to empty in one line. With an uncontrolled input, we would need `inputRef.current.value = ''` which is imperative DOM manipulation.

---

### Why the components are split the way they are

React's component model is a tool for managing complexity. The rule used throughout this project: **a component should own state only if it is the only one that needs it**.

| Component | State it owns | Why here, not in App |
|---|---|---|
| `App.jsx` | `query, results, loading, error, hasSearched, currentVibe, language` | All other components either read or write these values. They are siblings, so the parent (App) is the only shared ancestor. |
| `BookCard.jsx` | `coverFailed` | Only BookCard needs to know if its own image failed. App has no use for this information. Putting it in App would mean 6 separate `coverFailed_1, coverFailed_2...` booleans for no reason. |
| `DiscoverMore.jsx` | `searchTerm, status, statusMsg` | These control the discover input field and its feedback message. App only needs the result (new books were added), which it gets via the `onSearch` callback. |
| `SearchBar.jsx` | None (fully controlled) | SearchBar renders the query state passed from App. The textarea value is entirely dictated by the `query` prop. This makes SearchBar a "dumb" component -- easy to test, easy to replace. |

---

### Why useCallback for handleSearch

```jsx
// WITHOUT useCallback:
// Every time App re-renders (e.g. when loading=true is set),
// handleSearch is a brand-new function object.
// React sees SearchBar's `onSearch` prop changed → re-renders SearchBar.
// That's wasted work.

// WITH useCallback:
const handleSearch = useCallback(async (searchQuery) => {
  ...
}, [language])  // only recreate when language changes
```

`useCallback` memoises the function — it returns the same function reference across renders unless `language` changes. This prevents SearchBar from re-rendering when only `loading` or `results` change, since its `onSearch` prop remains the same object.

The `language` dependency is critical: if a user selects "Hindi" and then searches, `handleSearch` must use the *current* language value. Without the dependency, it would close over the stale `language = 'all'` from when it was first created.

---

### Hindi and Kannada book support — how it works end to end

**The key insight:** The BERT embedding model (`all-MiniLM-L6-v2`) was trained primarily on English. For best semantic matching, we write book descriptions in English even for Hindi and Kannada books. The `language` field is metadata — it labels which language the *book itself* is written in, not the description.

This means a search for "rural poverty India" in English will correctly find Premchand's Godan (a Hindi novel) because Godan's *description* is in English and semantically matches.

**End-to-end flow for a Hindi-filtered search:**

```
User selects Hindi tab → language state = 'Hindi'
User types "rural poverty India" → onSearch("rural poverty India")
        │
        ▼
App.jsx handleSearch('rural poverty India', language='Hindi')
  fetchRecommendations('rural poverty India', 6, 'Hindi')
        │
        ▼
POST /api/recommend/vibe  body: { query: ..., k: 6, language: "Hindi" }
        │
        ▼  (Vite proxy → FastAPI)
        │
routers/recommendations.py  vibe_check(request)
  embed_text(request.query)  → 384-float vector
  query_similar_books(vec, db, k=6, language="Hindi")
        │
        ▼
services/recommender.py  query_similar_books()
  db.query(Book).filter(Book.language.ilike("Hindi"))  → 5 Hindi books only
  matrix = np.array([json.loads(b.embedding_json) for b in books])  # (5, 384)
  similarities = matrix @ query_vec                                   # (5,)
  top_3 = argsort(similarities)[::-1][:5]                           # best 5
        │
        ▼
FastAPI returns list of BookRecommendation objects
        │
        ▼
React renders ResultsGrid with 5 Hindi book cards
Each card shows a "Hindi" badge on the cover image
```

**The 10 Indian language books seeded:**

| Title | Author | Language | Genre | Year |
|---|---|---|---|---|
| Godan | Munshi Premchand | Hindi | Literary Fiction | 1936 |
| Raag Darbari | Shrilal Shukla | Hindi | Satirical Fiction | 1968 |
| Tamas | Bhisham Sahni | Hindi | Historical Fiction | 1974 |
| Nirmala | Munshi Premchand | Hindi | Social Fiction | 1925 |
| Madhushala | Harivansh Rai Bachchan | Hindi | Poetry | 1935 |
| Samskara | U.R. Ananthamurthy | Kannada | Literary Fiction | 1965 |
| Parva | S.L. Bhyrappa | Kannada | Historical Fiction | 1979 |
| Mookajjiya Kanasugalu | K. Shivaram Karanth | Kannada | Literary Fiction | 1968 |
| Karvalo | Poornachandra Tejaswi | Kannada | Adventure | 1980 |
| Aavarana | S.L. Bhyrappa | Kannada | Historical Fiction | 2007 |

---

### Footer design decision

The original footer read:
```
Built with FastAPI · PyTorch · HuggingFace Transformers · React · API Docs ↗
```

This was replaced with:
```
Book Vibe  ·  Find your next read, one feeling at a time  ·  API Explorer
```

**Why:**
A tech-stack footer signals that this is a demo or a school project, not a product. Real products — Spotify, Goodreads, The Guardian — do not list their backend frameworks in the footer. The DEVELOPMENT_LOG.md is the right place for that information. The footer's job is brand reinforcement and utility (the API Explorer link is genuinely useful to a developer looking at the project). "Book Vibe" in Playfair Display gives the footer a literary signature that matches the headline typography.

---

### Live test verification (all scenarios)

| Scenario | Expected | Verified |
|---|---|---|
| Hero loads with Lucide icons (no emoji) | BookOpen badge, chip icons, Search button | Yes |
| Language tabs render Hindi/Kannada script | हिन्दी and ಕನ್ನಡ visible | Yes |
| Hindi filter + search returns only Hindi books | Godan, Nirmala etc. | Yes, 47% Godan #1 |
| Kannada filter + search returns only Kannada books | Samskara, Parva etc. | Yes |
| "All Languages" filter returns mixed results | English + Indian language books | Yes |
| Language badge shows on Hindi/Kannada cards | "Hindi" badge on cover | Yes |
| English-only books have no language badge | No redundant badge | Yes |
| Footer shows "Book Vibe" brand, not tech stack | Book Vibe · tagline · API Explorer | Yes |
| PlaceholderCover shows BookOpen icon + letter | Gradient + icon + initial | Yes |

---

*Last updated: Phase 4 — All polish complete. 40 books (English, Hindi, Kannada) embedded and searchable. Full stack verified.*
