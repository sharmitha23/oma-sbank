import { getLang } from './i18n'

const BASE = import.meta.env.VITE_API || ''

async function req(path, opts) {
  const sep = path.includes('?') ? '&' : '?'
  const r = await fetch(`${BASE}${path}${sep}lang=${getLang()}`, opts)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}
const post = (path, body) => req(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  meta: () => req('/api/meta'),
  lessons: () => req('/api/lessons'),
  home: cid => req(`/api/${cid}/home`),
  spending: cid => req(`/api/${cid}/spending`),
  goals: cid => req(`/api/${cid}/goals`),
  explore: (cid, q) => req(`/api/${cid}/explore?` + new URLSearchParams(Object.entries(q).filter(([, v]) => v))),
  whatif: (cid, target, pct, goal) => req(`/api/${cid}/whatif?` + new URLSearchParams({ target, pct, ...(goal ? { goal } : {}) })),
  classify: (cid, merchant, basket) => post(`/api/${cid}/classify`, { merchant, basket }),
  settings: (cid, savings_rate) => post(`/api/${cid}/settings`, { savings_rate }),
  ask: (cid, messages) => post(`/api/${cid}/ask`, { messages, lang: getLang() }),
}

// prototype: goals and preferences live on the device; in S-mobiili they'd be stored server-side
export const store = {
  get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } },
  set(key, v) { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode */ } },
}
