import { useCallback, useEffect, useRef, useState } from 'react'
import { api, signed } from './api'
import type { Analysis, Explanation, Job, RunSummary } from './api'
import { PriceChart, RotationChart } from './ResearchCharts'

function yesterday() {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const get = (type: string) => parts.find(p => p.type === type)!.value
  const d = new Date(`${get('year')}-${get('month')}-${get('day')}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() - 1)
  return d.toISOString().slice(0, 10)
}
function preference() { try { return localStorage.getItem('sectorpulse-mode') === 'demo' ? 'demo' : 'live' } catch { return 'live' } }
const active = (job: Job | null) => job !== null && ['queued', 'running'].includes(job.state)

export default function App() {
  const [mode, setMode] = useState(preference)
  const [date, setDate] = useState(yesterday)
  const [data, setData] = useState<Analysis | null>(null)
  const [selected, setSelected] = useState('XLK')
  const [measure, setMeasure] = useState('indexed')
  const [history, setHistory] = useState<RunSummary[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [explanation, setExplanation] = useState<Explanation | null>(null)
  const [replay, setReplay] = useState('')
  const loadSequence = useRef(0)

  const loadRun = useCallback(async (id: string) => {
    const seq = ++loadSequence.current
    setLoading(true); setReplay('')
    try {
      const [record, prose] = await Promise.all([api<Analysis>(`/runs/${id}`), api<Explanation>(`/runs/${id}/explanation`)])
      if (seq !== loadSequence.current) return
      setData(record); setExplanation(prose)
      setSelected(current => record.ranking.some(r => r.ticker === current) ? current : record.ranking[0]?.ticker || '')
    } catch (e) { if (seq === loadSequence.current) setError((e as Error).message) }
    finally { if (seq === loadSequence.current) setLoading(false) }
  }, [])

  const loadHistory = useCallback(async () => {
    const [runs, taskList] = await Promise.all([api<RunSummary[]>(`/runs?mode=${mode}`), api<Job[]>('/jobs')])
    setHistory(runs); setJobs(taskList)
    return taskList
  }, [mode])

  useEffect(() => {
    let cancelled = false
    ++loadSequence.current
    setLoading(true); setError(''); setData(null); setExplanation(null); setJob(null)
    try { localStorage.setItem('sectorpulse-mode', mode) } catch { /* Private storage may be disabled. */ }
    Promise.all([api<RunSummary[]>(`/runs?mode=${mode}`), api<Job[]>('/jobs')]).then(async ([rows, tasks]) => {
      if (cancelled) return
      setHistory(rows); setJobs(tasks)
      const relevant = tasks.filter(t => (t.kind === 'analysis' && t.params.mode === mode) || (t.kind === 'explanation' && rows.some(r => r.id === t.params.run_id)))
      setJob(relevant.find(t => active(t)) || relevant[0] || null)
      if (rows[0]) await loadRun(rows[0].id)
      else setLoading(false)
    }).catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true; ++loadSequence.current }
  }, [mode, loadRun])

  useEffect(() => {
    if (!job || !active(job)) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const current = await api<Job>(`/jobs/${job.id}`)
        if (stopped) return
        setJob(current)
        if (!active(current)) {
          await loadHistory()
          if (current.state === 'succeeded' && current.run_id) { setError(''); await loadRun(current.run_id) }
          else setError(current.error_message || `Task ${current.state}. Previous saved results are unchanged.`)
          return
        }
      } catch (e) { if (!stopped) setError(`Connection interrupted; task may still be running. ${(e as Error).message}`) }
      if (!stopped) timer = setTimeout(poll, 1500)
    }
    timer = setTimeout(poll, 600)
    return () => { stopped = true; clearTimeout(timer) }
  }, [job?.id, job?.state, loadHistory, loadRun])

  async function refresh() {
    setSubmitting(true); setError('')
    try { const result = await api<{job: Job}>('/runs', { mode, as_of_date: date }); setJob(result.job) }
    catch (e) { setError((e as Error).message) }
    finally { setSubmitting(false) }
  }
  async function requestExplanation() {
    if (!data) return
    setSubmitting(true); setError('')
    try { const result = await api<{job?: Job; cached?: boolean}>(`/runs/${data.id}/explanation`, {}); if (result.job) setJob(result.job); else await loadRun(data.id) }
    catch (e) { setError((e as Error).message) }
    finally { setSubmitting(false) }
  }
  async function verifyReplay() {
    if (!data) return
    const seq = loadSequence.current
    setReplay('Replaying saved inputs…')
    try {
      const result = await api<{snapshot_sha256: string; matches_saved: boolean; result: Analysis}>(`/runs/${data.id}/replay`)
      if (seq !== loadSequence.current) return
      const match = result.matches_saved
      setReplay(`${match ? 'Verified: saved ranking and holdout replay reproduced.' : 'Mismatch: saved result differs from current replay.'} Snapshot SHA-256: ${result.snapshot_sha256}`)
    } catch (e) { if (seq === loadSequence.current) setReplay((e as Error).message) }
  }
  const sector = data?.ranking.find(row => row.ticker === selected)
  const busy = submitting || active(job)
  const stale = data && (Date.now() - Date.parse(data.updated_at)) > 86400000

  return <main>
    <header><div className="brand"><span className="brand-icon">S</span><div>SectorPulse<small>SECTOR ROTATION RESEARCH</small></div></div><span className="pill">Auditable research · v0.3</span></header>
    <section className="intro"><div><div className="eyebrow">EVIDENCE BEFORE EXPLANATION</div><h1>See what’s leading.<br/><span>Keep the context.</span></h1><p>Relative strength, risk and macro evidence — independently measured.</p></div><div className="controls"><label>Data source<select value={mode} onChange={e => setMode(e.target.value)} disabled={busy}><option value="live">Live providers</option><option value="demo">Synthetic demo</option></select></label><label>As of (New York completed day)<input type="date" min="1999-01-01" max={yesterday()} value={date} onChange={e => setDate(e.target.value)} disabled={busy}/></label><button className="primary" disabled={busy || !date} onClick={refresh}>{busy ? 'Task in progress…' : '↻ Refresh analysis'}</button></div></section>
    <div className="notice">Educational research only. Not investment advice or a forecast. Ranking measures past relative performance, not the probability of future gains.</div>
    {loading && <div className="state" role="status">Loading saved research…</div>}
    {job && <div className={`state ${['failed','timed_out','interrupted'].includes(job.state) ? 'error' : ''}`} role="status"><strong>{job.kind === 'analysis' ? 'Analysis' : 'AI explanation'} · {job.state}</strong> — {job.stage}. {active(job) ? 'You can leave this page; the task continues on the server. Prior results remain available.' : `Updated ${new Date(job.updated_at).toLocaleString()}`}</div>}
    {error && <div className="state error" role="alert">{error} {data && 'The saved report below has not been replaced.'}</div>}
    {!data && !loading && <section className="state"><strong>No saved report selected.</strong> Refresh analysis to fetch and save a new snapshot, or select a past run. Demo mode works without provider keys.</section>}
    <section className="panel history"><div className="panel-head"><div className="eyebrow">RESEARCH JOURNAL</div><h2>Saved runs & task history</h2><p>Successful and partial reports are immutable. Failed tasks never replace them.</p></div><div className="history-controls"><label>Saved {mode} analysis<select value={data?.mode === mode ? data.id : ''} onChange={e => { if (e.target.value) { setError(''); void loadRun(e.target.value) } }}><option value="">Select a saved run</option>{history.map(row => <option key={row.id} value={row.id}>{row.as_of_date} · {row.status} · {new Date(row.created_at).toLocaleString()}</option>)}</select></label>{history.length > 0 && <button onClick={async () => { try { const more = await api<RunSummary[]>(`/runs?mode=${mode}&offset=${history.length}`); setHistory([...history,...more]); if (!more.length) setReplay('All saved reports loaded.') } catch(e) { setError((e as Error).message) } }}>Load older runs</button>}</div><details className="task-list"><summary>Recent tasks ({jobs.length})</summary>{jobs.length === 0 ? <p>No tasks yet.</p> : jobs.slice(0,10).map(item => <p key={item.id}><strong>{item.kind} · {item.state}</strong> · {item.params.mode || 'AI'} · {item.params.as_of_date || ''} · {new Date(item.created_at).toLocaleString()} {item.error_message || ''}</p>)}</details></section>
    {data && <>
      {data.mode === 'demo' && <div className="state demo"><strong>SYNTHETIC DATA</strong> · Prices, macro inputs and validation results demonstrate mechanics only. They are not market evidence.</div>}
      {(data.as_of_date !== date || data.mode !== mode) && <div className="state">Viewing saved {data.mode} research as of {data.as_of_date}. Refresh uses the controls above; it does not edit this report.</div>}
      {stale && <div className="state">This report was fetched over 24 hours ago. It is a saved historical snapshot, not a fresh market view.</div>}
      <div className="meta"><span>{data.source} · {data.method_version}</span><span>Last successful save {new Date(data.updated_at).toLocaleString()} · Prices through {data.price_date}</span></div>
      <div className="audit-actions"><a href={`/api/runs/${data.id}/snapshot`} target="_blank" rel="noreferrer">View input snapshot JSON ↗</a><button onClick={verifyReplay}>Verify reproducibility</button><span>{replay}</span></div>
      <section className="summary"><article><div className="eyebrow">COMPARABLE COVERAGE</div><h2>{data.coverage.available}<span className="muted"> / {data.coverage.expected}</span></h2><p>{data.ranking_status === 'ranked' ? 'At least 80% of eligible sectors have the same 61 benchmark sessions.' : 'Coverage below 80%. Ordinal ranks and the leader label are withheld.'}</p></article><article><div className="eyebrow">RELATIVE LEADERSHIP</div><h2>{data.ranking_status === 'ranked' ? data.ranking[0]?.ticker : 'Unavailable'}</h2><p>40% short-window excess return + 60% longer-window excess return. No macro bonus.</p></article><article><div className="eyebrow">INDEPENDENT RISK VIEW</div><h2>Context, not points</h2><p>Absolute return, volatility and drawdown are displayed separately. Relative leaders can still lose money.</p></article></section>
      <section className="workspace"><article className="panel ranking"><div className="panel-head"><div className="eyebrow">01 / RELATIVE STRENGTH</div><h2>Comparable sector performance</h2><p>Select a sector. Returns vs SPY are percentage-point differences.</p></div><div className="table-wrap"><table><thead><tr><th>Sector</th><th>Strength</th><th>20D vs SPY</th><th>60D vs SPY</th></tr></thead><tbody>{data.ranking.map(row => <tr key={row.ticker} className={row.ticker === selected ? 'selected' : ''}><td><button className="sector-button" aria-pressed={selected === row.ticker} onClick={() => setSelected(row.ticker)}><span className="rank">{row.rank ?? '—'}</span><span><strong>{row.ticker}</strong><small>{row.name}</small></span></button></td><td>{signed(row.score)}</td><td className={row.relative_20d >= 0 ? 'positive' : 'negative'}>{signed(row.relative_20d)} pp</td><td className={row.relative_60d >= 0 ? 'positive' : 'negative'}>{signed(row.relative_60d)} pp</td></tr>)}</tbody></table></div></article>
      <article className="panel detail"><div className="panel-head"><div className="eyebrow">02 / DETAIL & RISK</div><h2>{sector?.ticker} · {sector?.name}</h2></div>{sector && <><div className="score-parts"><div><small>60D absolute return</small><strong>{signed(sector.absolute_60d)}%</strong></div><div><small>Annualized volatility</small><strong>{sector.volatility_60d.toFixed(2)}%</strong></div><div><small>60D max drawdown</small><strong>{sector.drawdown_60d.toFixed(2)}%</strong></div></div><p className="rationale">{sector.rank ? `Rank #${sector.rank}` : 'Ordinal rank withheld'}: strength {signed(sector.score)} = 40% × {signed(sector.relative_20d)} pp + 60% × {signed(sector.relative_60d)} pp. Absolute 20-session return: {signed(sector.absolute_20d)}%. Macro conditions and AI text do not alter the score.</p><div className="chart-header"><h3>Sector vs SPY</h3><select aria-label="Chart measure" value={measure} onChange={e => setMeasure(e.target.value)}><option value="indexed">Indexed to 100</option><option value="price">Adjusted close ($)</option></select></div><PriceChart data={data} ticker={selected} measure={measure}/><p className="chart-note">{data.window_start} → {data.price_date}. {measure === 'indexed' ? 'Both begin at 100 to compare growth.' : 'Different dollar starting prices are not directly comparable.'}</p></>}</article></section>
      {Object.keys(data.excluded).length > 0 && <div className="state"><strong>Partial price coverage</strong>{Object.entries(data.excluded).map(([ticker,reason]) => <p key={ticker}>{ticker}: {reason}</p>)}</div>}
      <section className="panel macro"><div className="panel-head"><div className="eyebrow">03 / MACRO EVIDENCE</div><h2>Separate context, no forced cycle label</h2><p>{data.macro.reason}. These observations do not add points to sectors.</p></div><div className="context-grid">{data.context.map(item => <article key={item.name}><small>{item.name}</small><h3>{item.state}</h3><p>{item.evidence}</p></article>)}</div><details className="task-list"><summary>All macro observations · {data.macro.status}</summary><div className="macro-grid">{data.macro.indicators.map(item => <article key={item.name}><small>{item.name.replaceAll('_',' ')}</small><strong>{item.value === null ? 'Unavailable' : item.value.toLocaleString(undefined,{maximumFractionDigits:2})}</strong><span>{item.unit} · {item.series_id} · {item.status}</span><small>{item.observation_date ? `${item.observation_date} · ${item.age_days}d old` : 'No usable observation'}</small></article>)}</div></details></section>
      <section className="panel macro"><div className="panel-head"><div className="eyebrow">04 / RELATIVE STRENGTH MAP</div><h2>Leadership & change in momentum</h2><p>{data.rotation_method}</p></div><RotationChart data={data} selected={selected}/><p className="chart-note">Upper right: leading / accelerating · Lower right: leading / slowing · Upper left: lagging / improving · Lower left: lagging / weakening. Labels mark latest points. {selected}: {data.rotation[selected]?.quadrant}.</p></section>
      <section className="panel macro"><div className="panel-head"><div className="eyebrow">05 / TEMPORAL HOLDOUT</div><h2>Fixed-rule validation <span className="pill">{data.validation.status}</span></h2><p>{data.validation.kind} · {data.validation.reason}</p></div><div className="validation-summary"><p>First 60% reserved; last 40% evaluated. Signal at close → next observed close entry → 20-session holding period. Top three equally weighted, 20 bps round-trip cost per period on both basket and SPY.</p>{data.validation.summary && <p>{data.validation.summary.periods} evaluated periods · {data.validation.summary.skipped} skipped. {data.validation.summary.mean_excess_pp !== null && `Mean excess per evaluated period: ${signed(data.validation.summary.mean_excess_pp)} pp; outperformance frequency: ${((data.validation.summary.outperformance_fraction || 0) * 100).toFixed(1)}%.`}</p>}{data.validation.limitations.map(note => <p key={note}>{note}</p>)}</div><details className="task-list"><summary>Inspect evaluated periods ({data.validation.folds.length})</summary><div className="table-wrap"><table><thead><tr><th>Signal → entry → exit</th><th>Selected</th><th>Basket</th><th>SPY</th><th>Excess</th></tr></thead><tbody>{data.validation.folds.map(f => <tr key={f.signal_date}><td>{f.signal_date} → {f.entry_date} → {f.exit_date}</td><td>{f.selected.join(', ')}</td><td>{signed(f.basket_return_pct)}%</td><td>{signed(f.benchmark_return_pct)}%</td><td>{signed(f.excess_return_pp)} pp</td></tr>)}</tbody></table></div></details></section>
      <section className="panel macro"><div className="panel-head"><div className="eyebrow">06 / OPTIONAL AI EXPLANATION</div><h2>Explain the saved evidence</h2><p>Only allowlisted sector measurements are sent to Anthropic when you click below. No calendar dates, raw history, credentials or free-form provider text are included. AI prose is unverified and cannot change the report.</p><button className="primary" disabled={busy || !explanation?.enabled || !!explanation?.explanation} onClick={requestExplanation}>{explanation?.explanation ? 'Explanation saved' : explanation?.enabled ? 'Generate AI explanation' : 'AI unavailable — server key not configured'}</button></div>{explanation?.explanation && <div className="validation-summary"><small>{explanation.explanation.model} · AI-generated, verify against the measurements</small><p>{explanation.explanation.payload.summary}</p>{explanation.explanation.payload.observations.map((text,i) => <p key={i}>{text}</p>)}{explanation.explanation.payload.limitations.map((text,i) => <p key={i}>{text}</p>)}</div>}</section>
      <details className="panel methodology"><summary>Methodology & limitations</summary><p>{data.methodology}</p>{data.limitations.map(note => <p key={note}>{note}</p>)}</details>
    </>}
    <footer>SectorPulse · Saved evidence. Independent judgment.</footer>
  </main>
}
