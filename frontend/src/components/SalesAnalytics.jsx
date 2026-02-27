import React, { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts'
import { getYoY, getMoM, getColourAnalysis, getSeasonalPatterns, getSkuPerf } from '../services/api'

const COLORS = ['#f97316','#3b82f6','#10b981','#a78bfa','#f59e0b','#ec4899','#06b6d4','#84cc16']
const YEARS = [2021, 2022, 2023, 2024]

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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getYoY(), getMoM(24), getColourAnalysis(), getSeasonalPatterns(), getSkuPerf()])
      .then(([yoy, mom, col, seas, sku]) => {
        setYoyData(yoy)
        setMomData(mom)
        setColours(col)
        setSeasonal(seas)
        setSkus(sku.slice(0, 15))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

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
          <p className="text-xs text-brand-muted mb-4">Units sold per month across 2021–2024</p>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={yoyPivot}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
              {YEARS.map((y, i) => (
                <Line key={y} type="monotone" dataKey={y} stroke={COLORS[i]} strokeWidth={2} dot={{ r: 3 }} name={String(y)} />
              ))}
            </LineChart>
          </ResponsiveContainer>
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
          <p className="text-xs text-brand-muted mb-4">Average monthly units with seasonal factor overlay</p>
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
          </div>
        </div>
      )}

      {/* SKU Table */}
      {tab === 'sku' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-4">SKU Performance Table</h2>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th><th>SKU Code</th><th>Model</th><th>Colour</th>
                  <th>Total Units</th><th>Revenue</th><th>YoY%</th><th>MoM%</th><th>Status</th>
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
