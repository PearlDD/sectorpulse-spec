import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import LegacyResearch from './LegacyResearch'
import './desk.css'
import {LanguageContext, Localized, useLanguage} from './i18n'
import type {Language} from './i18n'
import SectorBoard from './SectorBoard'
import type {Watch} from './SectorBoard'

type Evidence = { name: string; value: number; unit: string; observation_date: string; url: string }
type Indicator = Evidence & { id: string; group: string; status: string; fetched_at: string }
type News = { id: string; title: string; url: string; source: string; published_at: string; topics: string[]; transmission: string; evidence_level: string; verification: string }
type Event = { id: string; title: string; category: string; importance: string; starts_at: string; time_confirmed: boolean; source: string; url: string; watch: string; source_stale?: boolean; status: string }

type Source = { name: string; status: string; last_success: string | null }
type Desk = { refreshing: boolean; last_success: string | null; schedule: string; last_report_id: number | null; method_version: string; sector_method: string; limitations: string[]; indicators: Indicator[]; news: News[]; events: Event[]; watchlist: Watch[]; sources: Source[]; cycle: { label: string; alternative: string; confidence: string; coverage: number; expected: number; missing: string[]; contradictions: string[]; method: string; drivers: {name: string; state: string; evidence: string; interpretation: string; url: string}[]; growth: { id: string; name: string; change_3m: number; acceleration_pp: number; url: string; observation_date: string }[]; inflation: {name: string; annualized_3m: number; previous_3m: number; yoy: number; url: string}[] } }
const formatStamp = (value: string | null, time = true, language: Language = 'zh') => value ? new Date(value).toLocaleString(language==='en'?'en-US':'zh-CN', { timeZone: 'America/New_York', month: '2-digit', day: '2-digit', ...(time ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}) }) : '尚未成功采集'
const nyDay = (value: string) => new Intl.DateTimeFormat('en-CA', {timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value))
const num = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 3 })
const signed = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(2)}`
const states: Record<string,string> = { available: '正常', stale: '已过期', error: '采集失败', pending: '等待采集' }
const topics = ['全部', '地缘政治', '贸易政策', '货币政策', '财政与选举', '通胀与能源', '增长与就业']
function NewsCard({item}: {item: News}) {
  const language=useLanguage()
  const stamp=(value:string|null,time=true)=>formatStamp(value,time,language)
  return <Localized><article className="news-card"><div className="item-meta">{item.source} · {stamp(item.published_at)} ET · {item.evidence_level}</div><a className="headline" href={item.url} target="_blank" rel="noreferrer">{item.title} ↗</a><div className="tags">{item.topics.map(t=><span key={t}>{t}</span>)}</div><div className="transmission"><b>可能的传导路径 · 条件假设</b><p>{item.transmission}</p></div><small>{item.verification}</small></article></Localized>
}
export default function App() {
  const [language,setLanguage]=useState<Language>(()=>{try{return localStorage.getItem('sectorpulse-language')==='en'?'en':'zh'}catch{return 'zh'}})
  const stamp=(value:string|null,time=true)=>formatStamp(value,time,language)
  useEffect(()=>{document.documentElement.lang=language==='en'?'en':'zh-CN';document.title=language==='en'?'SectorPulse · US Macro & Sector Research':'SectorPulse · 美国宏观与周期研究';try{localStorage.setItem('sectorpulse-language',language)}catch{/* Storage can be disabled. */}},[language])
  const [tab,setTab] = useState('desk')
  const [data,setData] = useState<Desk | null>(null)
  const [error,setError] = useState('')
  const [submitting,setSubmitting] = useState(false)
  const [topic,setTopic] = useState('全部')
  const [newsDays,setNewsDays] = useState(7)
  const [days,setDays] = useState(90)
  const [eventType,setEventType] = useState('重点事件')
  const load = useCallback(async () => {
    try {setData(await api<Desk>('/research'));setError('')}
    catch(e) {setError((e as Error).message)}
  },[])
  useEffect(()=>{void load();const timer=setInterval(()=>{void load()},10000);return ()=>clearInterval(timer)},[load])
  async function refresh() {
    setSubmitting(true)
    try {await api('/research/refresh',{});await load()}
    catch(e) {setError((e as Error).message)}
    finally {setSubmitting(false)}
  }
  const now = new Date(), today = nyDay(now.toISOString())
  const news = data?.news.filter(n=>n.published_at >= new Date(now.getTime()-newsDays*86400000).toISOString() && (topic==='全部'||n.topics.includes(topic))) || []
  const events = data?.events.filter(e=>{
    const day=e.starts_at.slice(0,10)
    return (days===-7 ? day<today && day>=nyDay(new Date(now.getTime()-7*86400000).toISOString()) : day>=today && day<=nyDay(new Date(now.getTime()+days*86400000).toISOString())) && (eventType==='全部'||(eventType==='重点事件'&&e.importance==='高')||e.category===eventType)
  }) || []
  const upcoming = data?.events.filter(e=>e.starts_at.slice(0,10)>=today && e.importance==='高').slice(0,4) || []
  const failures = data?.sources.filter(s=>s.status!=='available').length || 0
  const stale = !data?.last_success || Date.now()-Date.parse(data.last_success)>30*3600000
  return <LanguageContext.Provider value={language}><Localized><div className="desk-shell" lang={language==='en'?'en':'zh-CN'}>
    <header className="desk-header"><a href="#" className="desk-brand" onClick={e=>{e.preventDefault();setTab('desk')}}><span className="desk-logo">S↗</span><span>SectorPulse<small>美国宏观 · 周期 · 行业机会</small></span></a><div className="desk-header-actions"><button className="language-toggle" aria-label="切换中英文" onClick={()=>setLanguage(language==='zh'?'en':'zh')}>{language==='zh'?'English':'中文'}</button><span className="desk-local">● 本地研究工作台 <span>v0.5</span></span></div></header>
    <nav className="desk-nav" aria-label="研究导航">{[['desk','宏观工作台'],['news','新闻雷达'],['calendar','事件日历'],['prices','价格辅助']].map(([key,label])=><button key={key} className={tab===key?'current':''} onClick={()=>setTab(key)}>{label}</button>)}<span>研究窗口 6–18 个月</span></nav>
    {tab==='prices' ? <div className="legacy-wrap"><div className="desk-note">价格研究仅作辅助。相对强弱不能确认基本面筑底，演示数据不参与宏观判断。</div><LegacyResearch/></div> : <main className="desk-main">
      <section className="desk-intro"><div><div className="desk-eyebrow">US MACRO RESEARCH / 美国经济研究</div><h1>{tab==='news'?'从事件追踪到经济传导':tab==='calendar'?'把重要的时间点放在前面':'先理解周期，再寻找转折。'}</h1><p>增长、通胀、就业与信用交叉验证。把观测事实、条件假设和未确认的机会分开。</p></div><button className="desk-refresh" disabled={submitting||data?.refreshing} onClick={()=>void refresh()}>{submitting||data?.refreshing?'正在采集…':'↻ 更新研究资料'}</button></section>
      <div className="desk-status" role="status"><b>{data?.refreshing?'● 正在获取公开数据':stale?'◌ 等待新鲜资料':'● 已保存研究资料'}</b><span>最近完成 {stamp(data?.last_success||null)} ET</span><span>{data?.schedule||'美东每天 08:00 / 17:00 更新'}</span></div>
      {error && <div className="desk-alert" role="alert">连接失败：{error}。下方可能仍是旧内容，请勿视为实时状态。<button onClick={()=>void load()}>重试连接</button></div>}
      {!data ? <div className="desk-empty">正在读取本地研究档案…</div> : <>
        {failures>0 && <div className="desk-note">{failures}/{data.sources.length} 个来源尚未就绪或更新失败。旧资料标注时间，过期宏观数据不参与判断。<a href="#source-status">查看来源状态 ↓</a></div>}
        {tab==='desk' && <>
          <section className="cycle-layout"><article className="cycle-card"><div className="desk-eyebrow">01 / 周期判断</div><h2>{data.cycle.label}</h2><span className="confidence">判断信心：{data.cycle.confidence}</span><p>基于当前数据的倾向判断，不是对市场底部或未来收益的预测。</p><div className="cycle-alternative"><small>备选情景</small><p>{data.cycle.alternative}</p></div><div className="coverage-bar"><span style={{width:`${100*data.cycle.coverage/data.cycle.expected}%`}}/></div><small>有效宏观覆盖 {data.cycle.coverage}/{data.cycle.expected} · {data.method_version}</small></article>
          <article className="desk-panel"><div className="section-top"><div><div className="desk-eyebrow">支持证据</div><h2>增长与通胀，分别看</h2></div><span className="light-label">规则可检查</span></div><div className="evidence-grid">{data.cycle.growth.map(g=><a href={g.url} target="_blank" rel="noreferrer" key={g.id}><span>{g.name}</span><strong>{signed(g.change_3m)}<small>% / 3 个月</small></strong><p>较前 3 个月加速度 {signed(g.acceleration_pp)} 个百分点</p><small>观测期 {g.observation_date} ↗</small></a>)}{data.cycle.inflation.map(i=><a href={i.url} target="_blank" rel="noreferrer" key={i.name}><span>{i.name}</span><strong>{i.annualized_3m.toFixed(2)}<small>% / 3 个月年化</small></strong><p>前 3 个月 {i.previous_3m.toFixed(2)}% · 同比 {i.yoy.toFixed(2)}%</p></a>)}</div>{data.cycle.growth.length===0 && <div className="desk-empty">等待增长数据，不填入周期结论。</div>}<details className="desk-details"><summary>计算方法与反证</summary><p>{data.cycle.method}</p>{data.cycle.contradictions.map(x=><p key={x}>· {x}</p>)}{data.cycle.missing.length>0&&<p>缺失／过期：{data.cycle.missing.join('、')}</p>}</details></article></section>
          <section className="desk-panel macro-section"><div className="section-top"><div><div className="desk-eyebrow">02 / 宏观证据板</div><h2>把结论落到数据上</h2><p>当前可见修订值，观测期不是发布日期；低频数据不会每天变化。</p></div><span className="light-label">FRED</span></div><div className="indicator-grid">{data.indicators.map(i=><article className={`indicator ${i.status!=='available'?'stale':''}`} key={i.id}><div><span>{i.name}</span><small>{i.group}</small></div><strong>{num(i.value)}<small>{i.unit}</small></strong><p>观测期 {i.observation_date}<br/>抓取 {stamp(i.fetched_at)} ET</p><a href={i.url} target="_blank" rel="noreferrer">{i.status==='available'?'原始序列':'已过期 · 不参与判断'} ↗</a></article>)}</div>{data.indicators.length===0&&<div className="desk-empty">暂无宏观资料，不使用模拟值补齐。</div>}</section>
          <section className="driver-grid">{data.cycle.drivers.map(d=><article className="driver-card" key={d.name}><div className="desk-eyebrow">{d.name}</div><h3>{d.state}</h3><a href={d.url} target="_blank" rel="noreferrer">{d.evidence} ↗</a><p>{d.interpretation}</p></article>)}</section>
          <section className="desk-two-col"><article className="desk-panel"><div className="section-top"><div><div className="desk-eyebrow">03 / 重要时间点</div><h2>接下来重点看什么</h2></div><button className="text-button" onClick={()=>setTab('calendar')}>完整日历 ↗</button></div>{upcoming.map(e=><div className="upcoming" key={e.id}><span>{stamp(e.starts_at,false)}</span><div><b>{e.category}</b><p>{e.title}</p><small>{e.source_stale?'来源过期，需核对':e.time_confirmed?`${stamp(e.starts_at)} ET`:'具体时刻待确认'}</small></div></div>)}</article><article className="desk-panel"><div className="section-top"><div><div className="desk-eyebrow">04 / 新闻追踪</div><h2>新的事件，新的问题</h2></div><button className="text-button" onClick={()=>setTab('news')}>新闻雷达 ↗</button></div>{data.news.slice(0,3).map(n=><div className="news-preview" key={n.id}><small>{n.source} · {stamp(n.published_at)} ET</small><a href={n.url} target="_blank" rel="noreferrer">{n.title} ↗</a><small>{n.topics.join(' / ')}</small></div>)}{data.news.length===0&&<div className="desk-empty">暂无匹配标题，请检查来源状态。</div>}</article></section>
          <SectorBoard items={data.watchlist} method={data.sector_method} onPrices={()=>setTab('prices')}/>
        </>}
        {tab==='news'&&<section className="desk-panel"><div className="section-top"><div><h2>每日新闻雷达</h2><p>主题相关标题按发布时间排序，去除相同标题；同一事件仍可能有多篇报道。新闻不自动改变周期评分。</p></div><select aria-label="新闻时间范围" value={newsDays} onChange={e=>setNewsDays(Number(e.target.value))}>{[1,7,30].map(d=><option key={d} value={d}>{d===1?'过去 24 小时':`过去 ${d} 天`}</option>)}</select></div><div className="topic-filter">{topics.map(t=><button className={topic===t?'selected':''} key={t} onClick={()=>setTopic(t)}>{t}</button>)}</div><div className="news-count">{news.length} 条标题 · 美东时间</div><div className="news-list">{news.map(n=><NewsCard key={n.id} item={n}/>)}</div>{news.length===0&&<div className="desk-empty">范围内无匹配标题，请扩大时间范围或检查来源。</div>}</section>}
        {tab==='calendar'&&<section className="desk-panel"><div className="section-top"><div><h2>宏观与政策日历</h2><p>美东时间，自动处理夏令时。日程可能调整，采集失败时保留旧日历并标记。</p></div><div className="calendar-filters"><select aria-label="事件时间范围" value={days} onChange={e=>setDays(Number(e.target.value))}>{[7,30,90,400,-7].map(d=><option key={d} value={d}>{d<0?'过去 7 天':`未来 ${d} 天`}</option>)}</select><select aria-label="事件类别" value={eventType} onChange={e=>setEventType(e.target.value)}>{['重点事件','全部',...new Set(data.events.map(e=>e.category))].map(t=><option key={t} value={t}>{t}</option>)}</select></div></div><div className="desk-note">尚未接入一致预期与发布结果配对，本版不标注“超预期／低于预期”。观察框架不等于事后分析。</div><div className="calendar-list">{events.map(e=><article className="calendar-event" key={e.id}><div className="calendar-time"><small>{e.starts_at.slice(0,4)} 年</small><strong>{stamp(e.starts_at,false)}</strong><span>{e.time_confirmed?`${new Date(e.starts_at).toLocaleTimeString('zh-CN',{timeZone:'America/New_York',hour:'2-digit',minute:'2-digit',hour12:false})} ET`:'时间待确认'}</span><span>{e.importance}关注</span></div><div><div className="tags"><span>{e.category}</span>{e.source_stale&&<span>来源过期</span>}</div><h3><a href={e.url} target="_blank" rel="noreferrer">{e.title} ↗</a></h3><p>{e.watch}</p><small>{e.source} · {e.status}</small></div></article>)}</div>{events.length===0&&<div className="desk-empty">筛选范围内无事件，请扩大范围并检查来源。</div>}</section>}
        <section className="desk-panel sources-section" id="source-status"><details><summary>数据来源、采集状态与方法边界 <span>{data.sources.length-failures}/{data.sources.length} 就绪</span></summary><div className="source-grid">{data.sources.map(s=><article key={s.name}><b>{s.name.replace('macro:','FRED · ').replace('news:','新闻 · ').replace('calendar:','日历 · ')}</b><span className={s.status==='available'?'source-ok':'source-bad'}>{states[s.status]}</span><small>最近成功 {stamp(s.last_success)} ET</small></article>)}</div><div className="desk-limitations">{data.limitations.map(l=><p key={l}>· {l}</p>)}<p>当前规则未经前瞻收益验证，不给出买入建议。未启用付费 AI，新闻不会作为模型指令执行。</p></div></details></section>
        <footer className="desk-footer"><span>SectorPulse / Evidence before conviction.</span><span>自动采集需要电脑开机、服务运行。{data.last_report_id&&<a href={`/api/research/reports/${data.last_report_id}`} target="_blank" rel="noreferrer">研究与输入归档 #{data.last_report_id} ↗</a>}</span></footer>
      </>}
    </main>}
  </div></Localized></LanguageContext.Provider>
}
