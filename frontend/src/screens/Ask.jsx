import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { BarList, Columns, CompareRows, StackBar, WeekBars } from '../charts'
import { pct, t } from '../i18n'
import { BASKET_COLORS, Icon, Lesson, RichText, eur } from '../ui'
import { PeerRows } from './Spending'

const SUGGEST = [
  ['grpUnderstand', ['q_restaurants', 'q_biggest', 'q_increase']],
  ['grpLearn', ['q_payday', 'q_profile', 'q_peers']],
  ['grpImprove', ['q_safe', 'q_whatif', 'q_afford', 'q_advice']],
]

export default function Ask({ cid, meta, question, history, setHistory, simulate }) {
  const [msgs, setMsgs] = useState(history)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { setHistory(msgs); end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  useEffect(() => {
    if (question?.q) send(question.q)
    else inputRef.current?.focus()
  }, [question?.t])

  async function send(text) {
    const q = (text ?? input).trim()
    if (!q || busy) return
    setInput('')
    const next = [...msgs, { role: 'user', content: q }]
    setMsgs(next)
    setBusy(true)
    try {
      const r = await api.ask(cid, next.map(m => ({ role: m.role, content: m.content })))
      setMsgs([...next, { role: 'assistant', content: r.text, res: r }])
    } catch {
      setMsgs([...next, { role: 'assistant', content: t('errReach'), res: { cards: [], followups: [] } }])
    }
    setBusy(false)
  }

  return (
    <>
      <div className="screen">
        {msgs.length === 0 && (
          <div className="fade-in">
            <div style={{ textAlign: 'center', padding: '18px 10px 6px' }}>
              <div className="brand-mark" style={{ width: 52, height: 52, borderRadius: 16, margin: '0 auto', fontSize: 14 }}>OMA</div>
              <h1 style={{ fontSize: 21, marginTop: 12 }}>{t('talkTitle')}</h1>
              <p className="sub" style={{ marginTop: 4 }}>{t('talkSub')}</p>
            </div>
            {SUGGEST.map(([title, qs]) => (
              <div key={title}>
                <h2 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--muted)', margin: '18px 0 8px' }}>{t(title)}</h2>
                <div className="stack">
                  {qs.map(q => <button key={q} className="ask-bar" style={{ color: 'var(--ink)', boxShadow: 'none' }} onClick={() => send(t(q))}>{t(q)}</button>)}
                </div>
              </div>
            ))}
            <p className="small" style={{ textAlign: 'center', marginTop: 16 }}>
              <Icon name="shield" size={13} /> {meta.ai === 'offline' ? t('offlineNote') : t('aiNote')} {t('safetyNote')}
            </p>
          </div>
        )}
        <div className="chat">
          {msgs.map((m, i) => m.role === 'user'
            ? <div key={i} className="msg-u">{m.content}</div>
            : <Answer key={i} m={m} last={i === msgs.length - 1} send={send} simulate={simulate} />)}
          {busy && <div className="bubble" style={{ alignSelf: 'flex-start' }}><span className="typing"><span /><span /><span /></span><span className="small"> {t('thinking')}</span></div>}
          <div ref={end} />
        </div>
      </div>
      <form className="composer" onSubmit={e => { e.preventDefault(); send() }}>
        <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} placeholder={t('placeholder')} aria-label={t('placeholder')} />
        <button className="send" disabled={!input.trim() || busy} aria-label={t('send')}><Icon name="send" /></button>
      </form>
    </>
  )
}

function Answer({ m, last, send, simulate }) {
  const [math, setMath] = useState(false)
  const r = m.res || {}
  const cards = dedupe(r.cards || [])
  const g = r.grounding
  const isGoal = f => ['Make this a savings goal', 'Tee tästä säästötavoite', 'Gör detta till ett sparmål'].includes(f)
  return (
    <div className="msg-a fade-in">
      <div className="bubble">
        {r.mode === 'guard' && <span className="chip" style={{ marginBottom: 8 }}><Icon name="shield" size={13} /> {t('vetted')}</span>}
        <RichText text={m.content} />
        {cards.map((c, i) => <ToolCard key={i} c={c} simulate={simulate} />)}
        <div className="between" style={{ marginTop: 4, flexWrap: 'wrap' }}>
          {g && g.checked > 0 && (
            <span className={`verify ${g.unverified.length ? 'warn' : ''}`}>
              <Icon name={g.unverified.length ? 'info' : 'check'} size={14} stroke={2.4} />
              {g.unverified.length ? t('partVerified', { a: g.verified, b: g.checked }) : g.checked === 1 ? t('verified1') : t('verifiedN', { n: g.checked })}
            </span>
          )}
          {r.cards?.length > 0 && <button className="link" style={{ fontSize: 12, marginTop: 8 }} onClick={() => setMath(x => !x)}>{math ? t('hideMath') : t('showMath')}</button>}
        </div>
        {math && (
          <div className="math">
            {r.cards.map((c, i) => (
              <div key={i} style={{ marginTop: i ? 8 : 0 }}>
                <b>{i + 1}. {t(`tool_${c.tool}`)}</b> <code>{c.tool}({Object.entries(c.input || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})</code>
                <div>{summary(c.output)}</div>
              </div>
            ))}
            <div style={{ marginTop: 8 }}>{r.mode === 'ai' ? t('mathAi', { model: r.model }) : r.mode === 'guard' ? t('mathGuard') : r.mode === 'safe' ? t('mathSafe') : t('mathOffline')}</div>
          </div>
        )}
      </div>
      {last && r.followups?.length > 0 && (
        <div className="pills" style={{ marginTop: 10, flexWrap: 'wrap' }}>
          {r.followups.map(f => <button key={f} className="pill" style={{ whiteSpace: 'normal', textAlign: 'left' }} onClick={() => isGoal(f) ? simulate(goalPreset(r.cards)) : send(f)}>{f}</button>)}
        </div>
      )}
    </div>
  )
}

function dedupe(cards) {
  const seen = new Map()
  cards.forEach(c => seen.set(c.tool, c))
  return [...seen.values()].filter(c => !['get_month_summary', 'get_lesson', 'get_benchmark', 'get_advice', 'get_help_resources'].includes(c.tool)).slice(-2)
}

function goalPreset(cards) {
  const w = [...(cards || [])].reverse().find(c => c.tool === 'simulate_what_if')
  return w ? { target: w.output.target_id, pct: w.output.reduce_pct } : null
}

function summary(o) {
  if (!o || typeof o !== 'object') return String(o)
  return Object.entries(o).filter(([, v]) => typeof v === 'number' || (typeof v === 'string' && v.length < 70)).slice(0, 7)
    .map(([k, v]) => `${k.replaceAll('_', ' ')}: ${v}`).join(' · ')
}

function ToolCard({ c, simulate }) {
  const o = c.output
  const wrap = (title, body) => <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)' }}>{title && <div className="small" style={{ fontWeight: 700, marginBottom: 8 }}>{title}</div>}{body}</div>
  switch (c.tool) {
    case 'get_spending':
      if (!o.rows?.length) return null
      return wrap(o.chart.title, o.chart.type === 'bars' ? <BarList rows={o.rows.slice(0, 6)} /> : <Columns rows={o.rows} />)
    case 'compare_periods':
      return wrap(null, <CompareRows rows={o.rows} a={o.period_a} b={o.period_b} />)
    case 'simulate_what_if':
      if (!o.current_monthly) return null
      return wrap(t('whatIfCard', { t: o.target, p: pct(o.reduce_pct) }), (
        <div>
          <div className="kpis">
            <div className="kpi"><div className="k">{t('perMonthK')}</div><div className="v num" style={{ color: 'var(--forest)' }}>+{eur(o.monthly_saving)}</div></div>
            <div className="kpi"><div className="k">{t('perYearK')}</div><div className="v num" style={{ color: 'var(--forest)' }}>+{eur(o.yearly_saving)}</div></div>
          </div>
          <button className="btn sm full" style={{ marginTop: 10 }} onClick={() => simulate({ target: o.target_id, pct: o.reduce_pct })}><Icon name="goal" size={16} /> {t('makeGoal')}</button>
        </div>))
    case 'get_payday_pattern':
      return o.available ? wrap(t('byWeekTitle'), <WeekBars shares={o.everyday_share_by_week} />) : null
    case 'get_safe_to_spend':
      return wrap(t('safeUntil', { d: o.next_payday }), (
        <div className="kpis">
          <div className="kpi"><div className="k">{t('untilPayday')}</div><div className="v num">{eur(Math.max(o.safe_to_spend, 0))}</div></div>
          <div className="kpi"><div className="k">{t('perDayK')}</div><div className="v num">{eur(o.per_day)}</div></div>
        </div>))
    case 'can_i_afford':
      return wrap(null, <StackBar segments={[{ id: 'buy', label: t('thisPurchase'), value: Math.min(o.amount, Math.max(o.safe_to_spend, 0)), color: 'var(--b-everyday)' }, { id: 'left', label: t('leftToPayday'), value: Math.max(o.left_after, 0), color: 'var(--b-fixed)' }]} />)
    case 'get_spender_profile':
      return wrap(t('yourPatterns'), <div className="stack">{o.traits.map(x => <div key={x.id}><b style={{ fontSize: 13.5 }}>{x.name}</b><div className="small">{x.evidence}</div></div>)}</div>)
    case 'get_baskets':
      return wrap(t('monthlyAverage'), <StackBar segments={o.baskets.filter(x => x.monthly_avg > 0).map(x => ({ id: x.id, label: x.name, value: x.monthly_avg, color: BASKET_COLORS[x.id] }))} />)
    case 'list_transactions':
      return wrap(t('txTitle', { n: o.count, p: o.period }), <div>{o.items.slice(0, 6).map((x, i) => <div key={i} className="between" style={{ fontSize: 13, padding: '4px 0' }}><span>{x.date} · {x.merchant}</span><b className="num">{eur(x.amount)}</b></div>)}</div>)
    case 'get_peer_benchmark':
      return o.available ? wrap(o.title, <PeerRows rows={o.rows.slice(0, 5)} />) : null
    case 'get_help_resources':
      return wrap(t('helpTitle'), <p className="small" style={{ color: 'var(--ink)' }}>{o.text}</p>)
    case 'get_lesson':
      return <div style={{ marginTop: 12 }}><Lesson lesson={o} /></div>
    default:
      return null
  }
}
