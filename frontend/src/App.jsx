import { Routes, Route } from 'react-router-dom'
import Header from './components/Header.jsx'
import Home from './pages/Home.jsx'
import Browse from './pages/Browse.jsx'
import RepoPage from './pages/RepoPage.jsx'
import RepoForm from './pages/RepoForm.jsx'
import Profile from './pages/Profile.jsx'

export default function App() {
  return (
    <div className="app">
      <Header />
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/models" element={<Browse type="model" />} />
          <Route path="/datasets" element={<Browse type="dataset" />} />
          <Route path="/search" element={<Browse type={null} />} />
          <Route path="/new" element={<RepoForm mode="create" />} />
          <Route path="/:owner/:name/edit" element={<RepoForm mode="edit" />} />
          <Route path="/:owner/:name" element={<RepoPage />} />
          <Route path="/:owner" element={<Profile />} />
          <Route path="*" element={<div className="empty">Not found.</div>} />
        </Routes>
      </main>
      <footer className="footer">
        Local AI Hub — a self-hosted, offline model &amp; dataset catalog.
      </footer>
    </div>
  )
}
