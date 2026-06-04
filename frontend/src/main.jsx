// main.jsx — the entry point of the React application.
// React needs one "root" element in the HTML to attach itself to.
// We find the <div id="root"> in index.html and mount the whole app inside it.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'   // global styles loaded once here
import App from './App.jsx'

// StrictMode is a development helper — it highlights potential problems
// by intentionally rendering components twice. Has zero effect in production.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
