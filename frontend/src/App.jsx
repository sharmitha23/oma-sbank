import { useEffect, useState } from 'react'
import { api, store } from './api'
import { LANGS, setLang, t } from './i18n'
import { Icon } from './ui'
import Home from './screens/Home'
import Spending from './screens/Spending'
import Ask from './screens/Ask'
import Goals from './screens/Goals'

const TABS = [
  { id: 'home', label: 'navHome', icon: 'home' },
  { id: 'spending', label: 'navSpending', icon: 'baskets' },
  { id: 'ask', label: 'navAsk', icon: 'spark' },
  { id: 'goals', label: 'navGoals', icon: 'goal' },
]

const initialLang = store.get('oma.lang', 'fi') // Finnish by default
setLang(initialLang)

export default function App() {
  const [lang, setLangState] = useState(initialLang)
  const [meta, setMeta] = useState(null)
  const [lessons, setLessons] = useState({})
  const urlCustomer = new URLSearchParams(window.location.search).get('customer')
  const [cid, setCid] = useState(urlCustomer || store.get('oma.cid', null))
  const [tab, setTab] = useState('home')
  const [question, setQuestion] = useState(null)   // question sent from another screen to Ask OMA
  const [whatIf, setWhatIf] = useState(null)       // simulator preset from Ask OMA / Spending
  const [version, setVersion] = useState(0)        // bump to refetch after reclassifying
  const [chats, setChats] = useState({})           // chat history per customer
  const [err, setErr] = useState(null)

  useEffect(() => {
    setLang(lang)
    store.set('oma.lang', lang)
    document.documentElement.lang = lang
    api.meta().then(m => {
      setMeta(m)
      setCid(c => m.customers.some(x => x.id === c) || (c && c === urlCustomer) ? c : m.customers[0]?.id)
    }).catch(e => setErr(e.message))
    api.lessons().then(setLessons).catch(() => {})
  }, [lang])
  useEffect(() => { if (cid) store.set('oma.cid', cid) }, [cid])

  const ask = q => { setQuestion({ q, t: Date.now() }); setTab('ask') }
  const simulate = preset => { setWhatIf(preset); setTab('goals') }
  const me = meta?.customers.find(c => c.id === cid)
  const props = { cid, meta, lessons, ask, simulate, go: setTab, bump: () => setVersion(v => v + 1) }
  const k = `${cid}-${version}-${lang}`

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">OMA</div>
          <div>
            <div className="brand-name">OMA</div>
            <div className="brand-sub">{t('inApp')}</div>
          </div>
        </div>
        <div className="row" style={{ gap: 6 }}>
          <div className="langseg" role="group" aria-label={t('language')}>
            {LANGS.map(l => <button key={l.id} className={lang === l.id ? 'on' : ''} onClick={() => { setLang(l.id); setLangState(l.id) }} title={l.label} aria-pressed={lang === l.id}>{l.short}</button>)}
          </div>
          {meta && (
            <label className="persona" title={me?.about}>
              <span className="avatar">{me?.age ?? me?.name?.[0] ?? '?'}</span>
              <select value={cid ?? ''} onChange={e => setCid(e.target.value)} aria-label={t('customer')}>
                {!me && cid && <option value={cid}>{cid}</option>}
                {meta.customers.map(c => <option key={c.id} value={c.id}>{c.featured ? '★ ' : ''}{c.name}{c.about ? ` · ${c.about}` : ''}</option>)}
              </select>
            </label>
          )}
        </div>
      </header>
      {err && <div className="screen"><div className="card"><h3>{t('serverDown')}</h3><p className="small">{t('serverDownBody', { e: err })}</p></div></div>}
      {!err && cid && meta && (
        <>
          {tab === 'home' && <Home key={k} {...props} me={me} />}
          {tab === 'spending' && <Spending key={k} {...props} />}
          {tab === 'ask' && <Ask key={cid} {...props} question={question} history={chats[cid] || []} setHistory={h => setChats(c => ({ ...c, [cid]: h }))} />}
          {tab === 'goals' && <Goals key={k} {...props} preset={whatIf} />}
        </>
      )}
      <nav className="nav">
        {TABS.map(x => (
          <button key={x.id} className={tab === x.id ? 'on' : ''} onClick={() => setTab(x.id)} aria-current={tab === x.id}>
            <span className="nav-ic"><Icon name={x.icon} size={21} /></span>{t(x.label)}
          </button>
        ))}
      </nav>
    </div>
  )
}
