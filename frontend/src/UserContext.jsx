import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api.js'

const UserContext = createContext(null)
const STORAGE_KEY = 'localhub.user'

export function UserProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null
    } catch {
      return null
    }
  })

  useEffect(() => {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else localStorage.removeItem(STORAGE_KEY)
  }, [user])

  // Lightweight identity for a local, zero-trust tool: no passwords — picking a
  // username creates it (if new) and remembers it in this browser.
  async function signIn(username, fullName = '') {
    const u = await api.createUser({ username, full_name: fullName })
    setUser(u)
    return u
  }

  function signOut() {
    setUser(null)
  }

  return (
    <UserContext.Provider value={{ user, signIn, signOut }}>{children}</UserContext.Provider>
  )
}

export function useUser() {
  return useContext(UserContext)
}
