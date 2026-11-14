import { getLang, t } from './i18n'

export const BASKET_COLORS = { fixed: 'var(--b-fixed)', occasional: 'var(--b-occasional)', everyday: 'var(--b-everyday)', uncertain: 'var(--b-uncertain)' }

// €49.35 in English, 49,35 € in Finnish and Swedish; whole euros from 100 up
export const eur = (v, opts = {}) => {
  if (v == null || isNaN(v)) return '–'
  const a = Math.abs(v)
  const d = a >= 100 || opts.round || Number.isInteger(Math.round(a * 100) / 100) ? 0 : 2
  const loc = getLang() === 'en' ? 'en-GB' : getLang() === 'sv' ? 'sv-FI' : 'fi-FI'
  const s = new Intl.NumberFormat(loc, { minimumFractionDigits: d, maximumFractionDigits: d }).format(a)
  const sign = v < 0 ? '−' : ''
  return getLang() === 'en' ? `${sign}€${s}` : `${sign}${s} €`
}

const paths = {
  home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  baskets: 'M4 7h16l-1.5 12a2 2 0 0 1-2 1.8h-9a2 2 0 0 1-2-1.8zM8 7a4 4 0 0 1 8 0M9.5 11v6M14.5 11v6',
  goal: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01',
  spark: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
  send: 'M5 12h14M13 6l6 6-6 6',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 8h.01',
  chevron: 'M9 6l6 6-6 6',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  bulb: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z',
  trend: 'M3 17l6-6 4 4 8-8M15 7h6v6',
  coffee: 'M4 8h13v5a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6zM17 9h1.5a2.5 2.5 0 0 1 0 5H17M8 3v2M12 3v2',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  help: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17h.01',
  close: 'M6 6l12 12M18 6 6 18',
  plus: 'M12 5v14M5 12h14',
  shield: 'M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z',
  table: 'M4 5h16v14H4zM4 10h16M10 10v9',
  globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z',
  step: 'M5 12h14M12 5l7 7-7 7',
}
export function Icon({ name, size = 20, stroke = 1.8, ...p }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden {...p}>
      <path d={paths[name]} />
    </svg>
  )
}

export function Sheet({ title, onClose, children }) {
  return (
    <>
      <div className="sheet-bg" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label={title}>
        <div className="grab" />
        <div className="between" style={{ marginBottom: 10 }}>
          <h3 style={{ fontSize: 18 }}>{title}</h3>
          <button onClick={onClose} aria-label={t('close')}><Icon name="close" /></button>
        </div>
        {children}
      </div>
    </>
  )
}

export function Lesson({ lesson }) {
  if (!lesson) return null
  return (
    <div className="lesson">
      <div className="t"><Icon name="bulb" size={14} stroke={2.2} /> {t('moneyLesson')}</div>
      <p><b>{lesson.title}.</b> {lesson.body}</p>
    </div>
  )
}

// **bold** + newlines only: answers stay plain and safe to render
export function RichText({ text }) {
  return text.split('\n').filter(Boolean).map((line, i) => {
    const tip = line.startsWith('💡')
    const parts = line.replace(/^💡\s*/, '').split(/(\*\*[^*]+\*\*)/g).map((p, j) =>
      p.startsWith('**') ? <b key={j} className="num">{p.slice(2, -2)}</b> : p)
    return tip ? <div key={i} className="tip">💡 {parts}</div> : <p key={i} style={{ marginTop: i ? 8 : 0 }}>{parts}</p>
  })
}
