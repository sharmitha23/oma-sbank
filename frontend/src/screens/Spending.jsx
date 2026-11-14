import { useEffect, useState } from 'react'
import { api } from '../api'
import { BarList, Columns, Spark, StackBar, WeekBars } from '../charts'
import { pct, t } from '../i18n'
import { BASKET_COLORS, Icon, Lesson, eur } from '../ui'

export default function Spending({ cid, lessons, ask, simulate, bump }) {
  const [d, setD] = useState(null)
  const [open, setOpen] = useState('everyday')
  useEffect(() => { api.spending(cid).then(setD) }, [cid])
  if (!d) return <div className="screen"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>

  const b = d.baskets
  const sort = async (merchant, basket) => { await api.classify(cid, merchant, basket); bump() }

  return (
    <div className="screen fade-in">
      <h1>{t('mySpending')}</h1>
      <p className="sub">{t('spendingSub', { n: b.months.length })}</p>

      <div className="card" style={{ marginTop: 14 }}>
        <StackBar segments={b.baskets.filter(x => x.monthly_avg > 0).map(x => ({ id: x.id, label: x.name, value: x.monthly_avg, color: BASKET_COLORS[x.id] }))} />
      </div>

      <div style={{ marginTop: 12 }}>
        {b.baskets.filter(x => x.id !== 'uncertain').map(x => (
          <div key={x.id} className="card basket" style={{ '--c': BASKET_COLORS[x.id] }}>
            <button className="basket-head" onClick={() => setOpen(open === x.id ? null : x.id)} aria-expanded={open === x.id}>
              <div>
                <div className="tag">{x.short}</div>
                <h3 style={{ marginTop: 2 }}>{x.name}</h3>
                <div className="amt num" style={{ marginTop: 6 }}>{eur(x.monthly_avg)}<span className="small" style={{ fontWeight: 600 }}> {t('perMonth')}{x.share_of_income != null ? ` · ${t('ofIncome', { p: pct(x.share_of_income) })}` : ''}</span></div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Spark values={x.trend_6m} color={BASKET_COLORS[x.id]} labels={b.months_labels} />
                <div className="small">{t('months6')}</div>
              </div>
            </button>
            {open === x.id && (
              <div className="fade-in" style={{ marginTop: 12 }}>
                <p className="small" style={{ color: 'var(--ink-2)', marginBottom: 10 }}>{x.explain}</p>
                {x.groups.length ? <BarList rows={x.groups.map(g => ({ label: g.label, amount: g.monthly_avg }))} color={BASKET_COLORS[x.id]} /> : <p className="small">{t('nothingHere')}</p>}
                <div className="row" style={{ marginTop: 14, flexWrap: 'wrap' }}>
                  {x.id === 'everyday' && x.groups[0] && <button className="btn sm" onClick={() => simulate({ target: x.groups[0].id, pct: 20 })}>{t('simulateCut')}</button>}
                  {x.id === 'occasional' && <button className="btn sm ghost" onClick={() => ask(t('whyPlanQ'))}>{t('whyPlan')}</button>}
                  <button className="btn sm ghost" onClick={() => ask(t('basketQ', { name: x.name }))}>{t('askOma')}</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {d.uncertain.length > 0 && (
        <>
          <h2>{t('needsCall')}</h2>
          <div className="card">
            <p className="small" style={{ marginBottom: 12 }}>{t('needsCallBody')}</p>
            {d.uncertain.slice(0, 5).map(u => (
              <div key={u.merchant} style={{ padding: '10px 0', borderTop: '1px solid var(--line)' }}>
                <div className="between"><b>{u.label || u.merchant}</b><span className="num" style={{ fontWeight: 700 }}>{eur(u.total)}</span></div>
                <div className="small">{t('txCount', { n: u.count })} · {u.reason}</div>
                <div className="row" style={{ marginTop: 8, gap: 6 }}>
                  {['fixed', 'occasional', 'everyday'].map(k => (
                    <button key={k} className="pill" style={{ fontSize: 12, padding: '6px 10px', borderColor: BASKET_COLORS[k] }} onClick={() => sort(u.merchant, k)}>{t(`btn_${k}`)}</button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <Explorer cid={cid} ask={ask} />

      {d.payday.available && (
        <>
          <h2>{t('payCycle')}</h2>
          <div className="card">
            <p className="small" style={{ marginBottom: 14 }}>{t('payCycleSub', { d: d.payday.payday.day })}</p>
            <WeekBars shares={d.payday.everyday_share_by_week} />
            <button className="link" style={{ marginTop: 12 }} onClick={() => ask(t('q_payday'))}>{t('whyMatters')} <Icon name="chevron" size={14} /></button>
          </div>
        </>
      )}

      {d.peers?.available && (
        <>
          <h2>{t('peersTitle')}</h2>
          <div className="card">
            <p className="small" style={{ marginBottom: 12 }}>{d.peers.title}. {d.peers.note}</p>
            <PeerRows rows={d.peers.rows} />
            <button className="link" style={{ marginTop: 12 }} onClick={() => ask(t('q_peers'))}>{t('askOma')} <Icon name="chevron" size={14} /></button>
          </div>
        </>
      )}

      <h2>{t('youVsFinland')}</h2>
      <div className="card">
        {d.benchmark.rows.map(r => (
          <div key={r.label} style={{ marginBottom: 14 }}>
            <div className="between" style={{ fontSize: 13.5 }}><b>{r.label}</b><span className="small">{t('shareOfSpending')}</span></div>
            <BarList max={60} fmt={pct} rows={[
              { label: t('you'), amount: r.you, color: 'var(--forest)' },
              { label: t('lowIncome'), amount: r.low_income_households, color: 'var(--sage)' },
              ...(r.high_income_households ? [{ label: t('highIncome'), amount: r.high_income_households, color: '#B7C8BB' }] : []),
            ]} />
          </div>
        ))}
        <p className="small">{t('source')}: <a href={d.benchmark.url} target="_blank" rel="noreferrer" style={{ color: 'var(--forest)' }}>{d.benchmark.source}</a>. {d.benchmark.caveat}</p>
      </div>

      <div style={{ marginTop: 16 }}><Lesson lesson={lessons.three_baskets} /></div>
    </div>
  )
}

// MyData spirit: the customer slices their own data instead of seeing fixed bank charts
function Explorer({ cid, ask }) {
  const [q, setQ] = useState({ group_by: 'category', period: 'last_month', basket: '' })
  const [r, setR] = useState(null)
  const [table, setTable] = useState(false)
  useEffect(() => { api.explore(cid, q).then(setR) }, [cid, q])
  const set = (k, v) => setQ(o => ({ ...o, [k]: v, ...(k === 'group_by' && v === 'month' ? { period: 'last_12_months' } : {}) }))
  const g = r?.group_by === 'group' ? 'category' : r?.group_by
  return (
    <>
      <h2>{t('explore')}</h2>
      <div className="card">
        <div className="seg">
          {['category', 'merchant', 'weekday', 'month'].map(k => <button key={k} className={q.group_by === k ? 'on' : ''} onClick={() => set('group_by', k)}>{t(`by_${k}`)}</button>)}
        </div>
        <div className="pills" style={{ marginTop: 10 }}>
          {['this_month', 'last_month', 'last_3_months', 'last_12_months'].map(k => <button key={k} className={`pill ${q.period === k ? 'on' : ''}`} onClick={() => set('period', k)}>{t(`p_${k}`)}</button>)}
          <select className="pill" value={q.basket} onChange={e => set('basket', e.target.value)} aria-label={t('allBaskets')}>
            <option value="">{t('allBaskets')}</option>
            {['fixed', 'occasional', 'everyday'].map(k => <option key={k} value={k}>{t(`btn_${k}`)}</option>)}
          </select>
        </div>
        {r && (
          <div style={{ marginTop: 14 }}>
            <div className="between">
              <span className="small">{r.period} · {t('txCount', { n: r.transactions })}</span>
              <b className="num">{eur(r.total)}</b>
            </div>
            <div style={{ marginTop: 8 }}>
              {table ? (
                <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
                  <tbody>{r.rows.map(x => <tr key={x.key} style={{ borderTop: '1px solid var(--line)' }}><td style={{ padding: '6px 0' }}>{x.label}</td><td className="small">{x.count}×</td><td className="num" style={{ textAlign: 'right', fontWeight: 700 }}>{eur(x.amount)}</td></tr>)}</tbody>
                </table>
              ) : r.chart.type === 'bars' ? <BarList rows={r.rows} /> : <Columns rows={r.rows} />}
            </div>
            <div className="between" style={{ marginTop: 12 }}>
              <button className="link" onClick={() => setTable(x => !x)}><Icon name="table" size={14} /> {table ? t('chart') : t('table')}</button>
              <button className="link" onClick={() => ask(t('exploreQ', { g: t(`g_${g}`), period: r.period }))}>{t('askAbout')} <Icon name="chevron" size={14} /></button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

export function PeerRows({ rows }) {
  const fmt = r => v => v == null ? '–' : r.unit === '%' ? pct(v) : eur(v)
  return (
    <div className="stack">
      <div className="legend" style={{ marginTop: 0 }}>
        <span><i className="dot" style={{ background: 'var(--forest)' }} />{t('youShort')}</span>
        <span><i className="dot" style={{ background: '#B7C8BB' }} />{t('peersShort')}</span>
      </div>
      {rows.map(r => {
        const max = Math.max(r.you || 0, r.peers || 0, 1)
        return (
          <div key={r.id}>
            <div className="between" style={{ fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{r.label}</span>
              <span className="num"><b>{fmt(r)(r.you)}</b> <span className="small">/ {fmt(r)(r.peers)}</span></span>
            </div>
            <div style={{ display: 'grid', gap: 2, marginTop: 4 }}>
              <div style={{ height: 5, width: `${Math.max((r.you || 0) / max * 100, 1)}%`, background: 'var(--forest)', borderRadius: 3 }} />
              <div style={{ height: 5, width: `${Math.max((r.peers || 0) / max * 100, 1)}%`, background: '#B7C8BB', borderRadius: 3 }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
