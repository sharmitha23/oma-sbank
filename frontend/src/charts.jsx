import { useState } from 'react'
import { locale, pct, t } from './i18n'
import { eur } from './ui'

// 100% stacked bar with 2px gaps; legend always shown (identity never by colour alone)
export function StackBar({ segments, height = 14 }) {
  const total = segments.reduce((s, x) => s + Math.max(x.value, 0), 0) || 1
  const [hi, setHi] = useState(null)
  return (
    <div>
      <div style={{ display: 'flex', gap: 2, height, borderRadius: 4, overflow: 'hidden' }}>
        {segments.filter(s => s.value > 0).map(s => (
          <div key={s.id} title={`${s.label}: ${eur(s.value)} (${pct(Math.round(s.value / total * 100))})`}
            onMouseEnter={() => setHi(s.id)} onMouseLeave={() => setHi(null)}
            style={{ flex: s.value, background: s.color, opacity: hi && hi !== s.id ? .45 : 1, transition: 'opacity .15s', minWidth: 3 }} />
        ))}
      </div>
      <div className="legend">
        {segments.map(s => (
          <span key={s.id} style={{ opacity: hi && hi !== s.id ? .5 : 1 }}>
            <i className="dot" style={{ background: s.color }} />{s.label} <b className="num" style={{ color: 'var(--ink)' }}>{pct(Math.round(Math.max(s.value, 0) / total * 100))}</b>
          </span>
        ))}
      </div>
    </div>
  )
}

// Horizontal bars: best form for ranked categories on a narrow screen
export function BarList({ rows, color = 'var(--forest)', valueKey = 'amount', max, fmt = eur }) {
  const m = max ?? Math.max(...rows.map(r => r[valueKey]), 1)
  return (
    <div className="stack" style={{ marginTop: 4 }}>
      {rows.map(r => (
        <div key={r.label} title={`${r.label}: ${fmt(r[valueKey])}`}>
          <div className="between" style={{ fontSize: 13.5 }}>
            <span style={{ fontWeight: 600 }}>{r.label}</span>
            <span className="num" style={{ fontWeight: 700 }}>{fmt(r[valueKey])}</span>
          </div>
          <div style={{ height: 6, background: '#F0F3F0', borderRadius: 3, marginTop: 5 }}>
            <div style={{ width: `${Math.max(r[valueKey] / m * 100, 1.5)}%`, height: '100%', background: r.color || color, borderRadius: 3, transition: 'width .4s' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

// Share of everyday spending by week after payday, with the "even pace" reference line
export function WeekBars({ shares, even = 25 }) {
  const H = 110, max = Math.max(...shares, even) * 1.15
  return (
    <div>
      <div style={{ position: 'relative', height: H, display: 'flex', alignItems: 'flex-end', gap: 14, padding: '0 6px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: even / max * H, borderTop: '1.5px dashed var(--ink-2)', opacity: .5 }} />
        {shares.map((s, i) => {
          const hot = i === 0 && s > even + 8
          return (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%' }}>
              <span className="num" style={{ fontSize: 12.5, fontWeight: 800, marginBottom: 4, color: hot ? 'var(--b-everyday)' : 'var(--ink-2)' }}>{pct(s)}</span>
              <div style={{ width: '100%', maxWidth: 46, height: s / max * H, background: hot ? 'var(--b-everyday)' : 'var(--sage)', borderRadius: '4px 4px 0 0' }} />
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 14, padding: '6px 6px 0' }}>
        {shares.map((_, i) => <span key={i} className="small" style={{ flex: 1, textAlign: 'center', fontWeight: 600 }}>{i === 0 ? t('paydayWeek') : t('weekN', { n: i + 1 })}</span>)}
      </div>
      <div className="small" style={{ marginTop: 6 }}>
        <span style={{ display: 'inline-block', width: 16, borderTop: '1.5px dashed var(--ink-2)', opacity: .6, verticalAlign: 'middle', marginRight: 6 }} />{t('evenPace', { p: pct(even) })}
      </div>
    </div>
  )
}

export function Spark({ values, color = 'var(--sage)', w = 84, h = 28, labels }) {
  if (!values?.length) return null
  const max = Math.max(...values, 1), min = Math.min(...values, 0)
  const x = i => 3 + i * (w - 6) / Math.max(values.length - 1, 1)
  const y = v => h - 3 - (v - min) / (max - min || 1) * (h - 6)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ')
  return (
    <svg width={w} height={h} role="img" aria-label={t('months6')}>
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {values.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={i === values.length - 1 ? 3.5 : 6} fill={i === values.length - 1 ? color : 'transparent'}><title>{labels?.[i] ? `${labels[i]}: ` : ''}{eur(v)}</title></circle>)}
    </svg>
  )
}

// Columns over time (month trend / weekday)
export function Columns({ rows, color = 'var(--forest)' }) {
  const H = 120, max = Math.max(...rows.map(r => r.amount), 1)
  const [hi, setHi] = useState(null)
  const fmt = l => /^\d{4}-\d{2}$/.test(l) ? new Date(l + '-01').toLocaleString(locale(), { month: 'short' }) : l
  return (
    <div>
      <div className="small num" style={{ height: 18, fontWeight: 700, color: 'var(--ink)' }}>{hi != null ? `${fmt(rows[hi].label)}: ${eur(rows[hi].amount)}` : `max ${eur(max)}`}</div>
      <div style={{ height: H, display: 'flex', alignItems: 'flex-end', gap: 3, borderBottom: '1px solid var(--line)' }}>
        {rows.map((r, i) => (
          <div key={r.label} onMouseEnter={() => setHi(i)} onClick={() => setHi(i)} onMouseLeave={() => setHi(null)}
            style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end', cursor: 'pointer' }}>
            <div style={{ width: '100%', height: `${Math.max(r.amount / max * 100, 1)}%`, background: color, opacity: hi == null || hi === i ? 1 : .45, borderRadius: '4px 4px 0 0' }} />
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 3, marginTop: 4 }}>
        {rows.map((r, i) => <span key={r.label} className="small" style={{ flex: 1, textAlign: 'center', fontSize: 10.5 }}>{rows.length > 8 && i % 2 ? '' : fmt(r.label)}</span>)}
      </div>
    </div>
  )
}

export function CompareRows({ rows, a, b }) {
  const max = Math.max(...rows.flatMap(r => [r.a, r.b]), 1)
  return (
    <div className="stack">
      <div className="legend" style={{ marginTop: 0 }}>
        <span><i className="dot" style={{ background: '#C9D6CC' }} />{a}</span>
        <span><i className="dot" style={{ background: 'var(--forest)' }} />{b}</span>
      </div>
      {rows.slice(0, 5).map(r => (
        <div key={r.label}>
          <div className="between" style={{ fontSize: 13 }}>
            <span style={{ fontWeight: 600 }}>{r.label}</span>
            <span className="num" style={{ fontWeight: 700, color: r.change > 0 ? 'var(--b-everyday)' : 'var(--good)' }}>
              {r.change > 0 ? '▲' : '▼'} {eur(Math.abs(r.change))}{r.change_pct != null ? ` (${r.change_pct > 0 ? '+' : ''}${pct(r.change_pct)})` : ''}
            </span>
          </div>
          <div style={{ display: 'grid', gap: 2, marginTop: 4 }}>
            <div title={`${a}: ${eur(r.a)}`} style={{ height: 5, width: `${Math.max(r.a / max * 100, 1)}%`, background: '#C9D6CC', borderRadius: 3 }} />
            <div title={`${b}: ${eur(r.b)}`} style={{ height: 5, width: `${Math.max(r.b / max * 100, 1)}%`, background: 'var(--forest)', borderRadius: 3 }} />
          </div>
        </div>
      ))}
    </div>
  )
}
