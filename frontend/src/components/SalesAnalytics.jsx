import React, { useEffect, useState, useMemo } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts'
import { getYoY, getMoM, getColourAnalysis, getSeasonalPatterns, getSkuPerf, getDataInfo } from '../services/api'
import { Info, Search, ChevronUp, ChevronDown, Filter } from 'lucide-react'

const COLORS = ['#f97316','#3b82f6','#10b981','#a78bfa','#f59e0b','#ec4899','#06b6d4','#84cc16']
const YEAR_COLORS = ['#94a3b8','#3b82f6','#10b981','#f97316','#a78bfa','#ec4899']

function Tab({ label, active, onClick }) {
  return (
    <button onClick={onClick}
      className={`px-4 py-2 text-sm rounded-lg transition-all ${
        active ? 'bg-saffron-500/20 text-saffron-400 border border-saffron-500/30'
               : 'text-brand-muted hover:text-brand-text'
      }`}>{label}</button>
  )
}

function GrowthCell({ pct }) {
  if (pct === null || pct === undefined) return <span className="text-brand-muted text-xs">—</span>
  const cls = pct > 0 ? 'text-green-400' : pct < 0 ? 'text-red-400' : 'text-brand-muted'
  return <span className={cls + ' text-xs font-medium'}>{pct > 0 ? '+' : ''}{pct}%</span>
}

function SortIcon({ col, sortCol, sortDir }) {
  if (sortCol !== col) return <span className="text-brand-muted/40 text-xs ml-1">↕</span>
  return sortDir === 'asc'
    ? <ChevronUp size={12} className="inline ml-1 text-saffron-400" />
    : <ChevronDown size={12} className="inline ml-1 text-saffron-400" />
}

export default function SalesAnalytics() {
  const [tab, setTab]         = useState('yoy')
  const [yoyData, setYoyData] = useState([])
  const [momData, setMomData] = useState([])
  const [colours, setColours] = useState([])
  const [seasonal, setSeasonal] = useState([])
  const [skus, setSkus]       = useState([])
  const [dataInfo, setDataInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  // SKU table controls
  const [search, setSearch]     = useState('')
  const [sortCol, setSortCol]   = useState('total_units_sold')
  const [sortDir, setSortDir]   = useState('desc')
  const [filterStatus, setFilterStatus] = useState('all')  // all | active | slow
  const [page, setPage]         = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    Promise.all([getYoY(), getMoM(24), getColourAnalysis(), getSeasonalPatterns(), getSkuPerf(), getDataInfo()])
      .then(([yoy, mom, col, seas, sku, info]) => {
        setYoyData(yoy)
        setMomData(mom)
        setColours(col)
        setSeasonal(seas)
        setSkus(sku)        // ALL models — no slice
        setDataInfo(info)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const YEARS = useMemo(() => [...new Set(yoyData.map(d => d.year))].sort(), [yoyData])

  const yoyPivot = useMemo(() => {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return months.map((m, i) => {
      const row = { month: m }
      YEARS.forEach(y => {
        const entry = yoyData.find(d => d.year === y && d.month === i + 1)
        row[y] = entry?.units || 0
      })
      return row
    })
  }, [yoyData, YEARS])

  // Filtered + sorted SKU list
  const filteredSkus = useMemo(() => {
    let list = [...skus]
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(s =>
        s.model_name?.toLowerCase().includes(q) ||
        s.colour?.toLowerCase().includes(q) ||
        s.variant?.toLowerCase().includes(q) ||
        s.sku_code?.toLowerCase().includes(q)
      )
    }
    if (filterStatus === 'active') list = list.filter(s => !s.is_slow_moving)
    if (filterStatus === 'slow')   list = list.filter(s => s.is_slow_moving)

    list.sort((a, b) => {
      const av = a[sortCol] ?? -Infinity
      const bv = b[sortCol] ?? -Infinity
      return sortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
    })
    return list
  }, [skus, search, filterStatus, sortCol, sortDir])

  const pageData = filteredSkus.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(filteredSkus.length / PAGE_SIZE)

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
    setPage(0)
  }

  const hasPriceData = dataInfo?.has_price_data
  const fmtRev = (v) => hasPriceData ? `₹${(v / 100000).toFixed(1)}L` : 'N/A'

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Data info banner */}
      {dataInfo?.has_data && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
          <Info size={13} className="shrink-0" />
          <span>
            <strong>{dataInfo.total_records?.toLocaleString('en-IN')}</strong> records ·{' '}
            {dataInfo.date_range_start} → {dataInfo.date_range_end} ·{' '}
            {dataInfo.model_count} models · {dataInfo.sku_count} SKUs · Years: <strong>{YEARS.join(', ')}</strong>
          </span>
          {!hasPriceData && (
            <span className="ml-auto text-amber-400 flex items-center gap-1">
              <Info size={11} /> Revenue N/A — no price column in uploaded file
            </span>
          )}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-2 flex-wrap">
        {[['yoy','YoY Comparison'],['mom','MoM Trend'],['colour','Colour Analysis'],
          ['seasonal','Seasonal Patterns'],['sku','All Models']].map(([k,l]) => (
          <Tab key={k} label={l} active={tab===k} onClick={() => setTab(k)} />
        ))}
      </div>

      {/* ── YoY ── */}
      {tab === 'yoy' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Year-on-Year Monthly Comparison</h2>
          <p className="text-xs text-brand-muted mb-4">
            Units sold per month — {YEARS.length ? YEARS.join(', ') : 'No data'}
          </p>
          {YEARS.length === 0
            ? <p className="text-brand-muted py-8 text-center text-sm">Upload your sales file to see data.</p>
            : (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={yoyPivot}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="month" tick={{ fill:'#64748b', fontSize:12 }} />
                  <YAxis tick={{ fill:'#64748b', fontSize:12 }} />
                  <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8, color:'#f1f5f9' }} />
                  <Legend wrapperStyle={{ color:'#94a3b8', fontSize:12 }} />
                  {YEARS.map((y, i) => (
                    <Line key={y} type="monotone" dataKey={y}
                      stroke={YEAR_COLORS[i % YEAR_COLORS.length]}
                      strokeWidth={i===YEARS.length-1 ? 3 : 2}
                      dot={{ r: i===YEARS.length-1 ? 4 : 3 }}
                      name={String(y)}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )
          }
          {YEARS.length >= 2 && (() => {
            const ly = YEARS[YEARS.length-1]
            const cards = yoyData.filter(d => d.year===ly && d.growth_pct!==null).slice(0,4)
            return cards.length > 0 ? (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                {cards.map((d,i) => (
                  <div key={i} className="bg-white/[0.03] rounded-lg p-3 border border-brand-border/50">
                    <p className="text-xs text-brand-muted">{d.month_name} {d.year}</p>
                    <p className={`text-lg font-bold ${d.growth_pct>=0?'text-green-400':'text-red-400'}`}>
                      {d.growth_pct>0?'+':''}{d.growth_pct}%
                    </p>
                    <p className="text-xs text-brand-muted">vs {d.year-1}</p>
                  </div>
                ))}
              </div>
            ) : null
          })()}
        </div>
      )}

      {/* ── MoM ── */}
      {tab === 'mom' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Month-on-Month Sales Trend</h2>
          <p className="text-xs text-brand-muted mb-4">Last 24 months</p>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={momData}>
              <defs>
                <linearGradient id="momGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month_name" tick={{ fill:'#64748b', fontSize:11 }} />
              <YAxis tick={{ fill:'#64748b', fontSize:11 }} />
              <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8, color:'#f1f5f9' }} />
              <Area type="monotone" dataKey="units" stroke="#f97316" fill="url(#momGrad)" strokeWidth={2.5} name="Units" />
            </AreaChart>
          </ResponsiveContainer>
          <div className="mt-4 overflow-x-auto">
            <table className="data-table">
              <thead><tr><th>Period</th><th>Units</th><th>MoM Growth</th><th>Revenue</th></tr></thead>
              <tbody>
                {momData.slice(-12).map((d,i) => (
                  <tr key={i}>
                    <td>{d.month_name} {d.year}</td>
                    <td>{d.units?.toLocaleString('en-IN')}</td>
                    <td><GrowthCell pct={d.mom_growth_pct} /></td>
                    <td>{hasPriceData ? `₹${(d.revenue/100000).toFixed(1)}L` : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Colour ── */}
      {tab === 'colour' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Colour Distribution</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={colours} dataKey="total_units" nameKey="colour" cx="50%" cy="50%" outerRadius={100}
                  label={({ share_pct }) => `${share_pct}%`}>
                  {colours.map((_,i) => <Cell key={i} fill={COLORS[i%COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8, color:'#f1f5f9' }} />
                <Legend wrapperStyle={{ color:'#94a3b8', fontSize:12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Colour Performance</h2>
            <table className="data-table">
              <thead><tr><th>Colour</th><th>Units</th><th>Share</th><th>YoY</th></tr></thead>
              <tbody>
                {colours.map((c,i) => (
                  <tr key={i}>
                    <td>
                      <span className="inline-block w-2.5 h-2.5 rounded-full mr-2" style={{ background:COLORS[i%COLORS.length] }} />
                      {c.colour}
                    </td>
                    <td>{c.total_units?.toLocaleString('en-IN')}</td>
                    <td>{c.share_pct}%</td>
                    <td><GrowthCell pct={c.yoy_growth} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Seasonal ── */}
      {tab === 'seasonal' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Seasonal Demand Patterns</h2>
          <p className="text-xs text-brand-muted mb-4">Average monthly units from your actual data</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={seasonal}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month_name" tick={{ fill:'#64748b', fontSize:12 }} />
              <YAxis tick={{ fill:'#64748b', fontSize:12 }} />
              <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8, color:'#f1f5f9' }} />
              <Bar dataKey="avg_units" name="Avg Units" fill="#f97316" radius={[4,4,0,0]}
                label={({ x,y,width,value,index }) =>
                  seasonal[index]?.is_festive_month
                  ? <text x={x+width/2} y={y-4} fill="#fbbf24" textAnchor="middle" fontSize={9}>🎆</text>
                  : null
                }
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-brand-muted">
            <span>🎆 Festive month</span>
            <span className="text-amber-400">High: Oct–Nov–Dec, Mar</span>
            <span className="text-blue-400">Low: Jun–Jul (monsoon)</span>
            <span className="text-green-400">Marriage: Feb–May, Nov–Dec</span>
          </div>
        </div>
      )}

      {/* ── ALL MODELS TABLE ── */}
      {tab === 'sku' && (
        <div className="card">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div>
              <h2 className="text-sm font-semibold text-brand-text">All Models Performance</h2>
              {skus[0]?.ref_period && (
                <p className="text-xs text-brand-muted mt-0.5">
                  YoY: <span className="text-saffron-400">{skus[0].ref_period}</span> vs{' '}
                  <span className="text-blue-400">{skus[0].last_period}</span> (same period)
                </p>
              )}
            </div>
            <span className="text-xs text-brand-muted ml-auto">
              {filteredSkus.length} of {skus.length} models
            </span>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap gap-3 mb-4">
            {/* Search */}
            <div className="relative flex-1 min-w-[180px]">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-muted" />
              <input
                type="text"
                placeholder="Search model, colour…"
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(0) }}
                className="w-full pl-8 pr-3 py-2 text-xs bg-brand-bg border border-brand-border rounded-lg text-brand-text placeholder:text-brand-muted focus:outline-none focus:border-saffron-500/50"
              />
            </div>
            {/* Status filter */}
            <div className="flex gap-1">
              {[['all','All'],['active','Active'],['slow','Slow Moving']].map(([v,l]) => (
                <button key={v} onClick={() => { setFilterStatus(v); setPage(0) }}
                  className={`text-xs px-3 py-2 rounded-lg border transition-colors ${
                    filterStatus===v ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30'
                                     : 'text-brand-muted border-brand-border hover:text-brand-text'
                  }`}>{l}</button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-8">#</th>
                  <th onClick={() => handleSort('model_name')} className="cursor-pointer hover:text-brand-text select-none">
                    Model <SortIcon col="model_name" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th>Colour</th>
                  <th onClick={() => handleSort('total_units_sold')} className="cursor-pointer hover:text-brand-text select-none">
                    Total Units <SortIcon col="total_units_sold" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th onClick={() => handleSort('avg_monthly_units')} className="cursor-pointer hover:text-brand-text select-none">
                    Avg/Month <SortIcon col="avg_monthly_units" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th>{hasPriceData ? 'Revenue' : 'Revenue'}</th>
                  <th onClick={() => handleSort('yoy_growth_percent')} className="cursor-pointer hover:text-brand-text select-none">
                    YoY% <SortIcon col="yoy_growth_percent" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th onClick={() => handleSort('mom_growth_percent')} className="cursor-pointer hover:text-brand-text select-none">
                    MoM% <SortIcon col="mom_growth_percent" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th onClick={() => handleSort('current_month_units')} className="cursor-pointer hover:text-brand-text select-none">
                    Cur Month <SortIcon col="current_month_units" sortCol={sortCol} sortDir={sortDir} />
                  </th>
                  <th>Last Month</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {pageData.length === 0 && (
                  <tr><td colSpan={11} className="text-center text-brand-muted py-6">No models match your search.</td></tr>
                )}
                {pageData.map((s, i) => (
                  <tr key={`${s.model_name}-${s.colour}`}>
                    <td className="text-brand-muted">{page * PAGE_SIZE + i + 1}</td>
                    <td className="font-medium text-brand-text">{s.model_name}</td>
                    <td className="text-brand-muted text-xs">{s.colour}</td>
                    <td className="font-semibold">{s.total_units_sold?.toLocaleString('en-IN')}</td>
                    <td className="text-brand-muted">{s.avg_monthly_units}</td>
                    <td className={!hasPriceData ? 'text-brand-muted italic text-xs' : ''}>
                      {fmtRev(s.total_revenue)}
                    </td>
                    <td><GrowthCell pct={s.yoy_growth_percent} /></td>
                    <td><GrowthCell pct={s.mom_growth_percent} /></td>
                    <td className="font-semibold text-saffron-400">{s.current_month_units}</td>
                    <td className="text-brand-muted">{s.last_month_units}</td>
                    <td>
                      {s.is_slow_moving
                        ? <span className="badge-understock text-[10px]">Slow</span>
                        : <span className="badge-neutral text-[10px]">Active</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-xs text-brand-muted">
              <span>Page {page+1} of {totalPages} · {filteredSkus.length} models</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(0, p-1))} disabled={page===0}
                  className="px-3 py-1.5 rounded border border-brand-border disabled:opacity-40 hover:text-brand-text">
                  Prev
                </button>
                <button onClick={() => setPage(p => Math.min(totalPages-1, p+1))} disabled={page===totalPages-1}
                  className="px-3 py-1.5 rounded border border-brand-border disabled:opacity-40 hover:text-brand-text">
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
