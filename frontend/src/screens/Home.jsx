import { useEffect, useState } from 'react'
import { api } from '../api'
import { StackBar } from '../charts'
import { pct, t } from '../i18n'
import { BASKET_COLORS, Icon, Lesson, Sheet, eur } from '../ui'

const TONE_ICON = { learn: 'coffee', pattern: 'calendar', change: 'trend', action: 'help' }

export default function Home({ cid, meta, me, lessons, ask, go }) {
  const [d, setD] = useState(null)
  const [how, setHow] = useState(false)
  useEffect(() => { api.home(cid).then(setD) }, [cid])
  if (!d) return <div className="screen"><div className="skeleton" style={{ height: 190 }} /><div className="skeleton" /><div className="skeleton" /></div>

  const s = d.safe_to_spend
  const tm = d.this_month
  const b = d.baskets
  const segs = b.baskets.filter(x => x.monthly_avg > 0).map(x => ({ id: x.id, label: x.name, value: x.monthly_avg, color: BASKET_COLORS[x.id] }))
  const left = b.avg_monthly_income - b.baskets.reduce((a, x) => a + x.monthly_avg, 0)
  if (left > 0) segs.push({ id: 'left', label: t('leftOver'), value: left, color: '#DCE5DD' })
  const name = meta.dataset.sbank ? '' : me?.name || ''

  return (
    <div className="screen fade-in">
      <div className="between" style={{ marginTop: 4, gap: 8 }}>
        <h1>{name ? t('hei', { name }) : t('heiNoName')}</h1>
        <span className={`chip ${meta.dataset.demo ? 'demo' : ''}`}>{meta.dataset.demo ? t('demoData') : meta.dataset.sbank ? t('sbankData') : ''}{t('upTo', { date: s.as_of })}</span>
      </div>
      <p className="sub" style={{ marginBottom: 14 }}>{t('homeSub')}</p>

      <div className="hero">
        <div className="between" style={{ alignItems: 'flex-start' }}>
          <span className="label">{t('safeTitle')}</span>
          <span className={`status ${s.status}`}>{t(`st_${s.status}`)}</span>
        </div>
        <div className="big num">{eur(s.status === 'over' ? 0 : s.safe_to_spend)}</div>
        <div className="meta">
          <span className="num">{t('perDayV', { v: eur(s.per_day) })}</span>
          <span>{t('daysTo', { n: s.days_left, date: s.next_payday })}</span>
        </div>
        {s.status === 'over' && <p style={{ marginTop: 10, fontSize: 13.5, opacity: .9 }}>{t('overBody', { v: eur(-s.safe_to_spend) })}</p>}
        <button className="how" onClick={() => setHow(true)}><Icon name="info" size={16} /> {t('howCalc')}</button>
      </div>

      <button className="ask-bar" style={{ marginTop: 12 }} onClick={() => ask(null)}>
        <Icon name="spark" className="spark" /> {t('askBar')}
      </button>

      <h2 style={{ textTransform: 'none' }}>{tm.period.charAt(0).toUpperCase() + tm.period.slice(1)}</h2>
      <div className="kpis">
        <div className="kpi"><div className="k">{t('moneyIn')}</div><div className="v num">{eur(tm.income)}</div></div>
        <div className="kpi"><div className="k">{t('moneyOut')}</div><div className="v num">{eur(tm.spending)}</div></div>
      </div>

      <div className="card" style={{ marginTop: 10 }}>
        <div className="between">
          <h3>{t('whereIncome')}</h3>
          <button className="link" onClick={() => go('spending')}>{t('basketsLink')} <Icon name="chevron" size={14} /></button>
        </div>
        <p className="small" style={{ margin: '2px 0 12px' }}>{t('monthlyAvg', { n: b.months.length, v: eur(b.avg_monthly_income) })}</p>
        <StackBar segments={segs} />
      </div>

      <h2>{t('forYou')}</h2>
      {d.insights.map(i => (
        <div className="card insight" key={i.id}>
          <div className="ic"><Icon name={TONE_ICON[i.tone] || 'bulb'} size={18} /></div>
          <div>
            <h3>{i.title}</h3>
            <p>{i.body}</p>
            {i.ask && <button className="link" style={{ marginTop: 8 }} onClick={() => ask(i.ask)}>{t('askWhy')} <Icon name="chevron" size={14} /></button>}
            {i.goto && <button className="link" style={{ marginTop: 8 }} onClick={() => go(i.goto)}>{t('sortNow')} <Icon name="chevron" size={14} /></button>}
          </div>
        </div>
      ))}

      <h2>{t('personality')}</h2>
      <div className="card">
        <span className="chip">{d.profile.primary.name}</span>
        <p style={{ marginTop: 10, fontSize: 14 }}>{d.profile.primary.evidence}</p>
        <p className="small" style={{ marginTop: 8 }}>💡 {d.profile.primary.tip}</p>
        <button className="btn ghost sm" style={{ marginTop: 12 }} onClick={() => ask(t('q_profile'))}>{t('whatMeans')}</button>
      </div>

      {how && (
        <Sheet title={t('howTitle')} onClose={() => { setHow(false); api.home(cid).then(setD) }}>
          <HowCalculated cid={cid} initial={s} lesson={lessons.safe_to_spend} />
        </Sheet>
      )}
    </div>
  )
}

function HowCalculated({ cid, initial, lesson }) {
  const [s, setS] = useState(initial)
  const [rate, setRate] = useState(Math.round(initial.savings_rate * 100))
  const update = v => { setRate(v); api.settings(cid, v / 100).then(setS) }
  return (
    <div>
      <p className="small" style={{ marginBottom: 8 }}>{s.method}</p>
      {s.steps.map(st => (
        <div className="wf-row" key={st.label}>
          <div>
            <div style={{ fontWeight: 600 }}>{st.label}</div>
            {st.detail?.length > 0 && <div className="small">{st.detail.map(x => `${x.name} ${eur(x.amount)} (${x.date})`).join(' · ')}</div>}
            {st.detail_text && <div className="small">{st.detail_text}</div>}
          </div>
          <div className="amount num" style={{ color: st.amount > 0 ? 'var(--good)' : 'var(--ink)' }}>{st.amount > 0 ? '+' : ''}{eur(st.amount)}</div>
        </div>
      ))}
      <div className="wf-total"><span>{t('safeTotal')}</span><span className="num">{eur(s.safe_to_spend)}</span></div>
      <p className="small">{t('daysUntil', { n: s.days_left, date: s.next_payday, v: eur(s.per_day) })}</p>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="between"><h3>{t('savingsTarget')}</h3><b className="num">{t('ofIncome', { p: pct(rate) })}</b></div>
        <input type="range" min="0" max="30" step="5" value={rate} onChange={e => update(+e.target.value)} aria-label={t('savingsTarget')} />
        <p className="small">{t('inControl')}</p>
      </div>
      <div style={{ marginTop: 12 }}><Lesson lesson={lesson} /></div>
      <p className="small" style={{ marginTop: 12 }}><Icon name="shield" size={13} /> {s.limits.join(' ')}</p>
    </div>
  )
}
