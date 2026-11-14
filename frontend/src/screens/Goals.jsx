import { useEffect, useRef, useState } from 'react'
import { api, store } from '../api'
import { locale, pct, t } from '../i18n'
import { Icon, Lesson, eur } from '../ui'

const addMonths = n => { const d = new Date(); d.setMonth(d.getMonth() + n); return d.toLocaleString(locale(), { month: 'short', year: 'numeric' }) }

export default function Goals({ cid, lessons, preset, ask }) {
  const [g, setG] = useState(null)
  const [target, setTarget] = useState(preset?.target || null)
  const [rate, setRate] = useState(preset?.pct || 20)
  const [r, setR] = useState(null)
  const [name, setName] = useState(t('defaultGoal'))
  const [amount, setAmount] = useState(500)
  const [goals, setGoals] = useState(store.get(`oma.goals.${cid}`, []))
  const sim = useRef(null)

  useEffect(() => { api.goals(cid).then(x => { setG(x); setTarget(v => v || x.options[0]?.target) }) }, [cid])
  useEffect(() => { if (target) api.whatif(cid, target, rate, amount || undefined).then(setR) }, [cid, target, rate, amount])
  useEffect(() => { store.set(`oma.goals.${cid}`, goals) }, [goals, cid])
  useEffect(() => { if (preset && g) sim.current?.scrollIntoView({ block: 'start' }) }, [g])

  if (!g) return <div className="screen"><div className="skeleton" /><div className="skeleton" /></div>
  const sts = g.safe_to_save
  const save = () => {
    if (!r?.monthly_saving || !amount) return
    setGoals([{ id: Date.now(), name, amount: +amount, monthly: r.monthly_saving, how: `${r.target} −${pct(rate)}`, months: r.months_to_goal }, ...goals])
  }
  const fewer = Math.round(r?.fewer_purchases_per_month || 0)

  return (
    <div className="screen fade-in">
      <h1>{t('goalsTitle')}</h1>
      <p className="sub">{t('goalsSub')}</p>

      {g.advice.length > 0 && (
        <>
          <h2>{t('nextSteps')}</h2>
          <p className="small" style={{ marginTop: -4, marginBottom: 10 }}>{t('nextStepsSub')}</p>
          {g.advice.map((a, i) => (
            <div className="card insight" key={a.id}>
              <div className="ic num" style={{ fontWeight: 800 }}>{i + 1}</div>
              <div>
                <h3>{a.title}</h3>
                <p>{a.why}</p>
                <p style={{ color: 'var(--ink)', marginTop: 6 }}><Icon name="step" size={13} style={{ color: 'var(--forest)', verticalAlign: '-2px' }} /> {a.action}</p>
              </div>
            </div>
          ))}
        </>
      )}

      <div className="card" style={{ marginTop: 14 }}>
        <div className="row"><Icon name="shield" size={18} style={{ color: 'var(--forest)' }} /><h3>{t('safeToSave')}</h3></div>
        {sts.suggested_monthly_saving > 0 ? (
          <>
            <div className="result-big num" style={{ marginTop: 6 }}>{eur(sts.suggested_monthly_saving)}<span className="small" style={{ fontWeight: 600 }}> {t('perMonth')}</span></div>
            <p className="small">{t('saveOkBody')}{sts.already_saving_monthly > 0 ? t('alreadySaving', { v: eur(sts.already_saving_monthly) }) : ''}.</p>
          </>
        ) : <p className="small" style={{ marginTop: 6 }}>{t('saveNoneBody')}</p>}
      </div>

      <h2 ref={sim} style={{ scrollMarginTop: 8 }}>{t('whatIfTitle')}</h2>
      <div className="card">
        <div className="pills">
          {g.options.map(o => <button key={o.target} className={`pill ${target === o.target ? 'on' : ''}`} onClick={() => setTarget(o.target)}>{o.label}</button>)}
        </div>
        {r && (
          <>
            <div className="between" style={{ marginTop: 16 }}>
              <span className="small">{t('now')} <b className="num" style={{ color: 'var(--ink)' }}>{eur(r.current_monthly)}</b> {t('perMonth')}{r.purchases_per_month ? ` · ${t('purchasesN', { n: Math.round(r.purchases_per_month) })}` : ''}</span>
              <b className="num" style={{ fontSize: 18 }}>−{pct(rate)}</b>
            </div>
            <input type="range" min="5" max="100" step="5" value={rate} onChange={e => setRate(+e.target.value)} aria-label={pct(rate)} />
            <div className="kpis" style={{ marginTop: 6 }}>
              <div className="kpi"><div className="k">{t('saveMonthly')}</div><div className="v num" style={{ color: 'var(--forest)' }}>{eur(r.monthly_saving)}</div></div>
              <div className="kpi"><div className="k">{t('inAYear')}</div><div className="v num" style={{ color: 'var(--forest)' }}>{eur(r.yearly_saving)}</div></div>
            </div>
            <p className="small" style={{ marginTop: 10 }}>
              {fewer >= 1 ? t(fewer === 1 ? 'fewer1' : 'fewerN', { n: fewer, v: eur(r.avg_purchase) }) : ''}
              {t('over5', { v: eur(r.five_year_saving), n: r.baseline_months.length })}
            </p>

            <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
              <h3>{t('towardsGoal')}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 8, marginTop: 10 }}>
                <input className="field" value={name} onChange={e => setName(e.target.value)} aria-label={t('goalName')} />
                <input className="field num" type="number" min="0" value={amount} onChange={e => setAmount(e.target.value)} aria-label={t('goalAmount')} />
              </div>
              {r.months_to_goal && <p style={{ marginTop: 10, fontSize: 14 }}>{t('reachIn', { v: eur(+amount), n: r.months_to_goal, d: addMonths(r.months_to_goal) })}</p>}
              <button className="btn full" style={{ marginTop: 12 }} onClick={save} disabled={!r.months_to_goal}><Icon name="plus" size={18} /> {t('savePlan')}</button>
            </div>
          </>
        )}
      </div>

      {goals.length > 0 && (
        <>
          <h2>{t('myPlans')}</h2>
          {goals.map(x => (
            <div className="card" key={x.id}>
              <div className="between"><h3>{x.name}</h3><button onClick={() => setGoals(goals.filter(y => y.id !== x.id))} aria-label={t('remove')}><Icon name="close" size={16} /></button></div>
              <p className="small" style={{ marginTop: 4 }}>{t('planLine', { a: eur(x.amount), m: eur(x.monthly), how: x.how, d: addMonths(x.months) })}</p>
              <p className="small" style={{ marginTop: 6 }}>{t('planTip', { m: eur(x.monthly) })}</p>
            </div>
          ))}
        </>
      )}

      <div style={{ marginTop: 16 }}><Lesson lesson={lessons.savings_goals} /></div>
      <div style={{ marginTop: 10 }}><Lesson lesson={lessons.emergency_fund} /></div>
    </div>
  )
}
