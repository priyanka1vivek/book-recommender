/*
  SearchBar.jsx
  =============
  The hero search area: a big textarea, clickable vibe chips, a language
  filter, and the "Find My Books" submit button.

  WHY THIS COMPONENT EXISTS SEPARATELY FROM APP:
    App.jsx owns state; SearchBar owns presentation.
    Keeping them apart means we can redesign the search UI without touching
    any state logic, and vice versa. This is the "single responsibility"
    principle applied to React components.

  PROPS:
    query          — string currently typed in the textarea (controlled by App)
    onQueryChange  — called on every keystroke to update App's state
    onSearch       — called when the user wants to search (button or Enter)
    loading        — boolean: true while the API call is in-flight
    language       — currently selected language filter ('all'|'English'|'Hindi'|'Kannada')
    onLanguageChange — called when user clicks a language tab
*/

import { useRef }                                          from 'react'
import { Search, Loader2, CloudRain, TreePine, Rocket,
         Heart, Smile, Landmark, Sparkles, Zap, Globe }   from 'lucide-react'

// ---------------------------------------------------------------------------
// Vibe chip definitions
// Each chip has a Lucide icon component and a label string.
// WHY NOT EMOJI: emoji render differently across operating systems and fonts.
//   Lucide icons are SVG vectors -- they look identical everywhere, scale
//   perfectly at any size, and inherit the parent's CSS color.
// ---------------------------------------------------------------------------
const VIBE_CHIPS = [
  { Icon: CloudRain, label: 'dark detective mystery'        },
  { Icon: TreePine,  label: 'cozy fantasy with found family'},
  { Icon: Rocket,    label: 'epic sci-fi space opera'       },
  { Icon: Heart,     label: 'heartbreaking love story'      },
  { Icon: Smile,     label: 'funny irreverent adventure'    },
  { Icon: Landmark,  label: 'historical drama and intrigue' },
  { Icon: Sparkles,  label: 'magical realism and solitude'  },
  { Icon: Zap,       label: 'psychological suspense thriller'},
]

// ---------------------------------------------------------------------------
// Language filter tabs
// ---------------------------------------------------------------------------
const LANGUAGES = [
  { code: 'all',     label: 'All Languages'      },
  { code: 'English', label: 'English'             },
  { code: 'Hindi',   label: 'Hindi · हिन्दी'    }, // Hindi · हिंदी
  { code: 'Kannada', label: 'Kannada · ಕನ್ನಡ' }, // Kannada · ಕನ್ನಡ
]

const MAX_CHARS = 400

export default function SearchBar({
  query, onQueryChange, onSearch,
  loading, language, onLanguageChange,
}) {
  const inputRef = useRef(null)

  // Chip click: fill the textarea with the chip text, then immediately search.
  // WHY CALL onSearch WITH THE LABEL DIRECTLY instead of waiting for React
  // to re-render with the new query state?
  //   React state updates are asynchronous -- the parent's `query` state won't
  //   have updated yet when onSearch runs. Passing `label` directly avoids
  //   a one-render lag where the search fires with an empty query.
  function handleChipClick(label) {
    onQueryChange(label)
    onSearch(label)
  }

  // Enter submits; Shift+Enter inserts a newline (standard textarea behaviour).
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!loading && query.trim()) onSearch(query)
    }
  }

  const charsLeft   = MAX_CHARS - query.length
  const isOverLimit = charsLeft < 0

  return (
    <div className="search-card">

      {/* ---- Main textarea -------------------------------------------- */}
      <label className="search-label" htmlFor="vibe-input">
        Describe the vibe you're after
      </label>

      <textarea
        id="vibe-input"
        ref={inputRef}
        className="search-input"
        value={query}
        onChange={e => onQueryChange(e.target.value.slice(0, MAX_CHARS))}
        onKeyDown={handleKeyDown}
        placeholder='Try "dark rainy detective story" or "cozy autumn read with magic"...'
        rows={3}
        disabled={loading}
        aria-label="Describe the kind of book you want"
      />

      {/* ---- Language filter ------------------------------------------ */}
      {/*
        WHY LANGUAGE FILTER IS INSIDE THE SEARCH CARD:
          It directly modifies what the search will return, so it belongs
          visually adjacent to the search action -- not somewhere else on
          the page where users might miss it.
      */}
      <div className="lang-filter" role="group" aria-label="Filter by language">
        <Globe size={13} className="lang-icon" aria-hidden="true" />
        {LANGUAGES.map(({ code, label }) => (
          <button
            key={code}
            className={`lang-tab ${language === code ? 'active' : ''}`}
            onClick={() => onLanguageChange(code)}
            disabled={loading}
            aria-pressed={language === code}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ---- Suggestion chips ----------------------------------------- */}
      <div style={{ marginTop: 14 }}>
        <span className="chips-label">Quick vibes — click to try:</span>
        <div className="chips-row" role="list">
          {VIBE_CHIPS.map(({ Icon, label }) => (
            <button
              key={label}
              className={`chip ${query === label ? 'active' : ''}`}
              onClick={() => handleChipClick(label)}
              disabled={loading}
              aria-label={`Search for: ${label}`}
              role="listitem"
            >
              {/*
                Icon is a Lucide component stored as a variable.
                size=13 renders it as a 13×13 SVG. strokeWidth keeps
                it visually light so it doesn't overpower the text.
              */}
              <Icon size={13} strokeWidth={2} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ---- Footer: char count + submit ------------------------------ */}
      <div className="search-footer">
        <span
          className="char-count"
          style={{ color: isOverLimit ? '#dc2626' : undefined }}
        >
          {charsLeft} characters left
        </span>

        <button
          className="search-btn"
          onClick={() => onSearch(query)}
          disabled={loading || !query.trim() || isOverLimit}
          aria-label="Find book recommendations"
        >
          {loading
            ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Searching...</>
            : <><Search  size={15} aria-hidden="true" /> Find My Books</>
          }
          {/*
            WHY LOADER2 + SPIN CLASS:
              Loader2 is Lucide's circular spinner icon (a circle with a gap).
              The CSS animation rotates it continuously while loading=true.
              Using an icon means the spinner matches the button's font-size
              automatically -- no magic pixel values needed.
          */}
        </button>
      </div>

    </div>
  )
}
