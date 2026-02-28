import React, { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts'
import { getYoY, getMoM, getColourAnalysis, getSeasonalPatterns, getSkuPerf, getDataInfo } from '../services/api'
import { Info } from 'lucide-react'

const COLORS = ['#f97316','#3b82f6','#10b981','#a78bfa','#f59e0b','#ec4899','#06b6d4','#84cc16']
const YEAR_LINE_COLORS = ['#94a3b8','#3b82f6','#10b981','#f97316','#a78bfa','#ec4899']

function Tab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm rounded-lg transition-all ${
        active ? 'bg-saffron-500/20 text-saffron-400 border border-saffron-500/30' :
                 'text-brand-muted hover:text-brand-text'
      }`}
    >
      {label}
    </button>
  )
}

export default function SalesAnalytics() {
  const [tab, setTab] = useState('yoy')
  const [yoyData, setYoyData] = useState([])
  const [momData, setMomData] = useState([])
  const [colours, setColours] = useState([])
  const [seasonal, setSeasonal] = useState([])
  const [skus, setSkus] = useState([])
  const [dataInfo, setDataInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getYoY(), getMoM(24), getColourAnalysis(), getSeasonalPatterns(), getSkuPerf(), getDataInfo()])
      .then(([yoy, mom, col, seas, sku, info]) => {
        setYoyData(yoy)
        setMomData(mom)
        setColours(col)
        setSeasonal(seas)
        setSkus(sku.slice(0, 15))
        setDataInfo(info)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Dynamically extract years from actual data — no hardcoding!
  const YEARS = [...new Set(yoyData.map(d => d.year))].sort()

  // Reshape YoY data for multi-line chart
  const yoyPivot = (() => {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return months.map((m, i) => {
      const row = { month: m }
      YEARS.forEach(y => {
        const entry = yoyData.find(d => d.year === y && d.month === i + 1)
        row[y] = entry?.units || 0
      })
      return row
    })
  })()

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Data info banner */}
      {dataInfo?.has_data && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
          <Info size={14} className="shrink-0" />
          <span>
            Analysing <strong>{dataInfo.total_records?.toLocaleString('en-IN')}</strong> sales records
            &nbsp;|&nbsp; {dataInfo.date_range_start} to {dataInfo.date_range_end}
            &nbsp;|&nbsp; {dataInfo.sku_count} SKUs &nbsp;|&nbsp; Years: {YEARS.join(', ')}
          </span>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-2 flex-wrap">
        {[['yoy','YoY Comparison'],['mom','MoM Trend'],['colour','Colour Analysis'],['seasonal','Seasonal Patterns'],['sku','SKU Table']].map(([k,l]) => (
          <Tab key={k} label={l} active={tab === k} onClick={() => setTab(k)} />
        ))}
      </div>

      {/* YoY Multi-line Chart */}
      {tab === 'yoy' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Year-on-Year Monthly Comparison</h2>
          <p className="text-xs text-brand-muted mb-4">
            Units sold per month — {YEARS.length > 0 ? YEARS.join(', ') : 'No data loaded'}
          </p>
          {YEARS.length === 0 ? (
            <div className="py-12 text-center text-brand-muted text-sm">
              No sales data loaded. Please upload your sales file from Upload Data.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={yoyPivot}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
                {YEARS.map((y, i) => (
                  <Line
                    key={y}
                    type="monotone"
                    dataKey={y}
                    stroke={YEAR_LINE_COLORS[i % YEAR_LINE_COLORS.length]}
                    strokeWidth={i === YEARS.length - 1 ? 3 : 2}
                    dot={{ r: i === YEARS.length - 1 ? 4 : 3 }}
                    name={String(y)}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}

          {/* YoY Growth Summary Cards */}
          {YEARS.length >= 2 && (() => {
            const latestYear = YEARS[YEARS.length - 1]
            const latestYearData = yoyData.filter(d => d.year === latestYear && d.growth_pct !== null)
            return latestYearData.length > 0 ? (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                {latestYearData.slice(0, 4).map((d, i) => (
                  <div key={i} className="bg-white/[0.03] rounded-lg p-3 border border-brand-border/50">
                    <p className="text-xs text-brand-muted">{d.month_name} {d.year}</p>
                    <p className={`text-lg font-bold ${d.growth_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {d.growth_pct > 0 ? '+' : ''}{d.growth_pct}%
                    </p>
                    <p className="text-xs text-brand-muted">vs {d.year - 1}</p>
                  </div>
                ))}
              </div>
            ) : null
          })()}
        </div>
      )}

      {/* MoM Trend */}
      {tab === 'mom' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Month-on-Month Sales Trend</h2>
          <p className="text-xs text-brand-muted mb-4">Last 24 months – units sold with growth rate</p>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={momData}>
              <defs>
                <linearGradient id="momGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month_name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
              <Area type="monotone" dataKey="units" stroke="#f97316" fill="url(#momGrad)" strokeWidth={2.5} name="Units" />
            </AreaChart>
          </ResponsiveContainer>
          {/* MoM growth table */}
          <div className="mt-4 overflow-x-auto">
            <table className="data-table">
              <thead><tr><th>Period</th><th>Units</th><th>MoM Growth</th><th>Revenue</th></tr></thead>
              <tbody>
                {momData.slice(-12).map((d, i) => (
                  <tr key={i}>
                    <td>{d.month_name} {d.year}</td>
                    <td>{d.units?.toLocaleString('en-IN')}</td>
                    <td className={d.mom_growth_pct > 0 ? 'text-green-400' : d.mom_growth_pct < 0 ? 'text-red-400' : 'text-brand-muted'}>
                      {d.mom_growth_pct !== null ? `${d.mom_growth_pct > 0 ? '+' : ''}${d.mom_growth_pct}%` : '—'}
                    </td>
                    <td>₹{(d.revenue / 100000).toFixed(1)}L</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Colour Analysis */}
      {tab === 'colour' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Colour Distribution (All Time)</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={colours} dataKey="total_units" nameKey="colour" cx="50%" cy="50%" outerRadius={100} label={({ colour, share_pct }) => `${share_pct}%`}>
                  {colours.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Colour Performance Table</h2>
            <table className="data-table">
              <thead><tr><th>Colour</th><th>Units</th><th>Share</th><th>YoY</th></tr></thead>
              <tbody>
                {colours.map((c, i) => (
                  <tr key={i}>
                    <td><span className="inline-block w-2.5 h-2.5 rounded-full mr-2" style={{ background: COLORS[i % COLORS.length] }}></span>{c.colour}</td>
                    <td>{c.total_units?.toLocaleString('en-IN')}</td>
                    <td>{c.share_pct}%</td>
                    <td className={c.yoy_growth > 0 ? 'text-green-400' : c.yoy_growth < 0 ? 'text-red-400' : 'text-brand-muted'}>
                      {c.yoy_growth !== null ? `${c.yoy_growth > 0 ? '+' : ''}${c.yoy_growth}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Seasonal Patterns */}
      {tab === 'seasonal' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Seasonal Demand Patterns</h2>
          <p className="text-xs text-brand-muted mb-4">Average monthly units derived from your actual sales data</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={seasonal}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month_name" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                formatter={(val, name) => [name === 'seasonal_factor' ? val.toFixed(2) : val.toLocaleString(), name]} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              <Bar dataKey="avg_units" name="Avg Units" fill="#f97316" radius={[4, 4, 0, 0]}
                   label={({ x, y, width, value, index }) =>
                     seasonal[index]?.is_festive_month ?
                     <text x={x + width / 2} y={y - 4} fill="#fbbf24" textAnchor="middle" fontSize={9}>🎆</text> : null
                   }
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-brand-muted">
            <span>🎆 Festive month</span>
            <span className="text-amber-400">High demand: Oct–Nov–Dec, Mar</span>
            <span className="text-blue-400">Low demand: Jun–Jul (monsoon)</span>
            <span className="text-green-400">Marriage months: Feb–May, Nov–Dec</span>
          </div>
        </div>
      )}

      {/* SKU Table */}
      {tab === 'sku' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">SKU Performance Table</h2>
          {skus[0]?.ref_year && (
            <p className="text-xs text-brand-muted mb-4">
              YoY: {skus[0].ref_year} vs {skus[0].ref_year - 1} &nbsp;|&nbsp; MoM: latest vs previous month in data
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th><th>SKU Code</th><th>Model</th><th>Colour</th>
                  <th>Total Units</th><th>Revenue</th><th>YoY%</th><th>MoM%</th><th>Cur Month</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {skus.map((s, i) => (
                  <tr key={s.sku_code}>
                    <td className="text-brand-muted">{i + 1}</td>
                    <td className="font-mono text-xs text-saffron-400">{s.sku_code}</td>
                    <td>{s.model_name}</td>
                    <td>{s.colour}</td>
                    <td>{s.total_units_sold?.toLocaleString('en-IN')}</td>
                    <td>₹{(s.total_revenue / 100000).toFixed(1)}L</td>
                    <td className={s.yoy_growth_percent > 0 ? 'text-green-400' : s.yoy_growth_percent < 0 ? 'text-red-400' : 'text-brand-muted'}>
                      {s.yoy_growth_percent !== null ? `${s.yoy_growth_percent > 0 ? '+' : ''}${s.yoy_growth_percent}%` : '—'}
                    </td>
                    <td className={s.mom_growth_percent > 0 ? 'text-green-400' : s.mom_growth_percent < 0 ? 'text-red-400' : 'text-brand-muted'}>
                      {s.mom_growth_percent !== null ? `${s.mom_growth_percent > 0 ? '+' : ''}${s.mom_growth_percent}%` : '—'}
                    </td>
                    <td className="font-semibold text-saffron-400">{s.current_month_units}</td>
                    <td>
                      {s.is_slow_moving
                        ? <span className="badge-understock">Slow Moving</span>
                        : <span className="badge-neutral">Active</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
