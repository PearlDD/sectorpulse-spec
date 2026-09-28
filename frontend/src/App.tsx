import { useEffect, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Rank = { rank: number; ticker: string; name: string; score: number; relative_20d: number; relative_60d: number; momentum_score: number; cycle_bonus: number; last_price: number }
type Indicator = { name: string; series_id: string; unit: string; value: number | null; observation_date: string | null; age_days: number | null; status: string }
type Analysis = { ranking: Rank[]; excluded: Record<string, string>; cycle: { phase: string; reason: string }; mode: string; source: string; as_of_date: string; updated_at: string; price_date: string; window_start: string; methodology: string; prices: Record<string, { date: string; close: number }[]>; macro: { status: string; reason: string; indicators: Indicator[] }; limitations: string[] }
const yesterday = () => { const d = new Date(); d.setDate(d.getDate() - 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
const signed = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}`
function preference(name: string, fallback: string) { try { return localStorage.getItem(name) || fallback } catch { return fallback } }

function App() {
  const [mode, setMode] = useState(preference('sectorpulse-mode', 'live'))
  const [date, setDate] = useState(yesterday())
  const [data, setData] = useState<Analysis | null>(null)
  const [selected, setSelected] = useState('XLK')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [chartMode, setChartMode] = useState('indexed')
  const [request, setRequest] = useState(0)
  const [query, setQuery] = useState({ mode, date })

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    fetch(`/api/analysis?mode=${query.mode}&as_of_date=${query.date}`, { signal: controller.signal })
      .then(async response => {
        const body = await response.json()
        if (!response.ok) throw new Error(typeof body.detail?.message === 'string' ? body.detail.message : 'The API could not process this request.')
        return body as Analysis
      })
      .then(body => { setData(body); setSelected(current => body.ranking.some(row => row.ticker === current) ? current : (body.ranking[0]?.ticker || '')) })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || 'Cannot reach the API. Check the backend and retry.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, request])

  function refresh() {
    try { localStorage.setItem('sectorpulse-mode', mode) } catch { /* Storage may be disabled. */ }
    setQuery({ mode, date }); setRequest(value => value + 1)
  }
  const sector = data?.ranking.find(row => row.ticker === selected)
  const spy = new Map(data?.prices.SPY?.map(point => [point.date, point.close]) || [])
  const common = (data?.prices[selected] || []).filter(point => spy.has(point.date) && point.date >= (data?.window_start || ''))
  const first = common[0]
  const chart = common.map(point => ({ date: point.date, sector: chartMode === 'indexed' ? 100 * point.close / first.close : point.close, SPY: chartMode === 'indexed' ? 100 * spy.get(point.date)! / spy.get(first.date)! : spy.get(point.date) }))
  const pending = data && (mode !== data.mode || date !== data.as_of_date)

  return <main>
    <header><div className="brand"><span className="brand-icon">S</span><div>SectorPulse<small>SECTOR ROTATION RESEARCH</small></div></div><span className="pill">Deterministic baseline · v0.2</span></header>
    <section className="intro"><div><div className="eyebrow">MARKET CONTEXT, MADE VISIBLE</div><h1>See what’s leading.<br /><span>Understand why.</span></h1><p>Compare the 11 SPDR sectors with the S&P 500 benchmark.</p></div><div className="controls"><label>Data source<select value={mode} onChange={event => setMode(event.target.value)}><option value="live">Live providers</option><option value="demo">Synthetic demo</option></select></label><label>As of (completed day)<input type="date" min="1999-01-01" max={yesterday()} value={date} onChange={event => setDate(event.target.value)} /></label><button className="primary" disabled={loading || !date} onClick={refresh}>{loading ? 'Fetching analysis…' : '↻ Refresh analysis'}</button></div></section>
    <div className="notice">Educational research only. Not investment advice, a forecast, or a guarantee of future performance.</div>
    {loading && <div className="state" role="status">Loading prices and macro inputs. Provider retries can take a few minutes.</div>}
    {error && <div className="state error" role="alert"><strong>Analysis unavailable.</strong> {error} Select synthetic demo or retry. {data && 'The previous successful result remains below.'}</div>}
    {pending && <div className="state">Controls changed. Refresh to apply; results below still show {data.mode} data as of {data.as_of_date}.</div>}
    {data && <>
      {data.mode === 'demo' && <div className="state demo"><strong>SYNTHETIC DEMO</strong> · Generated prices and macro inputs demonstrate the interface. These are not market observations.</div>}
      <div className="meta"><span>{data.source}</span><span>Last updated {new Date(data.updated_at).toLocaleString()} · Prices through {data.price_date}</span></div>
      <section className="summary"><article><div className="eyebrow">CYCLE CONTEXT</div><h2 className="capitalize">{data.cycle.phase}</h2><p>{data.cycle.reason}</p></article><article><div className="eyebrow">SECTOR COVERAGE</div><h2>{data.ranking.length}<span className="muted"> / 11</span></h2><p>Ranked with a shared 60-session window. New or incomplete sectors are excluded.</p></article><article><div className="eyebrow">LEADING BASELINE SCORE</div><h2>{data.ranking[0]?.ticker || 'Unavailable'} <span className="accent">{data.ranking[0] ? signed(data.ranking[0].score) : ''}</span></h2><p>Relative strength plus cycle mapping. A descriptive score, not a buy signal.</p></article></section>
      <section className="workspace"><article className="panel ranking"><div className="panel-head"><div className="eyebrow">01 / SECTOR RANKING</div><h2>Relative leadership</h2><p>Select a sector to inspect its score and price history.</p></div>{data.ranking.length === 0 ? <div className="state">No sectors have sufficient aligned price history to rank.</div> : <div className="table-wrap"><table><thead><tr><th>Sector</th><th>Score</th><th>20D vs SPY</th><th>60D vs SPY</th></tr></thead><tbody>{data.ranking.map(row => <tr key={row.ticker} className={selected === row.ticker ? 'selected' : ''}><td><button className="sector-button" onClick={() => setSelected(row.ticker)} aria-pressed={selected === row.ticker}><span className="rank">{String(row.rank).padStart(2, '0')}</span><span><strong>{row.ticker}</strong><small>{row.name}</small></span></button></td><td><strong>{signed(row.score)}</strong></td><td className={row.relative_20d >= 0 ? 'positive' : 'negative'}>{signed(row.relative_20d)} pp</td><td className={row.relative_60d >= 0 ? 'positive' : 'negative'}>{signed(row.relative_60d)} pp</td></tr>)}</tbody></table></div>}</article>
      <article className="panel detail"><div className="panel-head"><div className="eyebrow">02 / SECTOR DETAIL</div><h2>{sector ? `${sector.ticker} · ${sector.name}` : 'Select a sector'}</h2></div>{sector && <><div className="score-parts"><div><small>Momentum</small><strong>{signed(sector.momentum_score)}</strong></div><div><small>Cycle bonus</small><strong>+{sector.cycle_bonus.toFixed(2)}</strong></div><div><small>Total score</small><strong>{signed(sector.score)}</strong></div></div><p className="rationale">Ranked #{sector.rank}: 40% of its {signed(sector.relative_20d)} pp 20-session excess return plus 60% of its {signed(sector.relative_60d)} pp 60-session excess return. {sector.cycle_bonus ? `The ${data.cycle.phase} mapping includes ${sector.ticker}, adding 2 points.` : data.cycle.phase === 'unknown' ? 'Cycle context is unavailable, so no bonus is applied.' : `The ${data.cycle.phase} mapping does not include ${sector.ticker}, so no bonus is applied.`}</p><div className="chart-header"><h3>Price comparison</h3><select aria-label="Chart measure" value={chartMode} onChange={event => setChartMode(event.target.value)}><option value="indexed">Indexed to 100</option><option value="price">Adjusted close ($)</option></select></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}><CartesianGrid stroke="#253344" strokeDasharray="3 3" /><XAxis dataKey="date" tickFormatter={value => value.slice(5)} minTickGap={35} stroke="#9aaabc" fontSize={11} /><YAxis domain={['auto', 'auto']} tickFormatter={value => Number(value).toFixed(0)} width={45} stroke="#9aaabc" fontSize={11} /><Tooltip contentStyle={{ background: '#142030', border: '1px solid #33465c', borderRadius: 8 }} formatter={value => Number(value).toFixed(2)} /><Legend /><Line type="linear" dataKey="sector" name={sector.ticker} stroke="#5be0ba" dot={false} strokeWidth={2} isAnimationActive={false} /><Line type="linear" dataKey="SPY" stroke="#9b9bff" dot={false} strokeWidth={2} isAnimationActive={false} /></LineChart></ResponsiveContainer></div><p className="chart-note">{data.window_start} → {data.price_date}. {chartMode === 'indexed' ? 'Both start at 100; this chart compares relative growth.' : 'Dollar prices have different starting levels; use indexed mode to compare growth.'}</p></>}</article></section>
      {Object.keys(data.excluded).length > 0 && <section className="state"><strong>Partial price coverage</strong>{Object.entries(data.excluded).map(([ticker, reason]) => <p key={ticker}>{ticker}: {reason}</p>)}</section>}
      <section className="panel macro"><div className="panel-head"><div className="eyebrow">03 / MACRO INPUTS</div><h2>Economic backdrop <span className="pill">{data.macro.status}</span></h2><p>{data.macro.reason}. Observation dates below may precede the selected analysis date.</p></div><div className="macro-grid">{data.macro.indicators.map(item => <article key={item.name}><small>{item.name.replaceAll('_', ' ')}</small><strong>{item.value === null ? 'Unavailable' : item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong><span>{item.unit} · {item.series_id}</span><small>{item.observation_date ? `Observed ${item.observation_date} · ${item.age_days}d old` : 'No usable observation'}</small></article>)}</div></section>
      <details className="panel methodology"><summary>How scores work & data limitations</summary><p>{data.methodology}</p>{data.limitations.map(note => <p key={note}>{note}</p>)}<p>AI analysis is disabled. No dates or data are sent to an LLM. FRED uses the requested historical vintage, while Yahoo adjusted prices can still be revised later.</p></details>
    </>}
    {!data && !loading && !error && <div className="state">Choose a data source and refresh to begin.</div>}
    <footer>SectorPulse · Research with context. Make decisions independently.</footer>
  </main>
}
export default App
