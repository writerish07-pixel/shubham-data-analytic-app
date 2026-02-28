import React, { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend
} from 'recharts'
import { MapPin, TrendingUp, TrendingDown, Package, IndianRupee } from 'lucide-react'
import { getLocationAnalysis } from '../services/api'

const COLORS = ['#f97316','#3b82f6','#10b981','#a78bfa','#f59e0b','#ec4899','#06b6d4','#84cc16','#fb923c','#60a5fa']

function GrowthBadge({ pct }) {
  if (pct === null || pct === undefined) return <span className="text-brand-muted">—</span>
  return (
    <span className={`flex items-center gap-1 text-xs font-medium ${pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
      {pct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {pct > 0 ? '+' : ''}{pct}%
    </span>
  )
}

export default function LocationAnalytics() {
  const [locations, setLocations] = useState([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('bar')

  useEffect(() => {
    getLocationAnalysis()
      .then(setLocations)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  if (locations.length === 0) return (
    <div className="card text-center py-12">
      <MapPin size={32} className="text-brand-muted mx-auto mb-3" />
      <p className="text-brand-text font-medium mb-1">No Location Data Available</p>
      <p className="text-brand-muted text-sm">
        Upload your sales file with a <strong>location</strong> or <strong>city</strong> column to see city-wise analytics.
      </p>
    </div>
  )

  const fmt = (n) => n >= 10000000 ? `₹${(n / 10000000).toFixed(1)}Cr` :
                      n >= 100000  ? `₹${(n / 100000).toFixed(1)}L` : `₹${n?.toLocaleString('en-IN')}`

  const totalUnits = locations.reduce((s, l) => s + l.total_units, 0)
  const totalRevenue = locations.reduce((s, l) => s + l.total_revenue, 0)

  return (
    <div className="space-y-6">
      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <MapPin size={16} className="text-saffron-400" />
            <span className="text-xs text-brand-muted">Locations</span>
          </div>
          <p className="text-2xl font-bold text-brand-text">{locations.length}</p>
          <p className="text-xs text-brand-muted mt-1">cities / dealers tracked</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Package size={16} className="text-green-400" />
            <span className="text-xs text-brand-muted">Total Units</span>
          </div>
          <p className="text-2xl font-bold text-brand-text">{totalUnits.toLocaleString('en-IN')}</p>
          <p className="text-xs text-brand-muted mt-1">all locations combined</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <IndianRupee size={16} className="text-blue-400" />
            <span className="text-xs text-brand-muted">Total Revenue</span>
          </div>
          <p className="text-2xl font-bold text-brand-text">{fmt(totalRevenue)}</p>
          <p className="text-xs text-brand-muted mt-1">all locations combined</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-saffron-400" />
            <span className="text-xs text-brand-muted">Top Location</span>
          </div>
          <p className="text-xl font-bold text-saffron-400">{locations[0]?.location}</p>
          <p className="text-xs text-brand-muted mt-1">{locations[0]?.share_pct}% of total volume</p>
        </div>
      </div>

      {/* View toggle */}
      <div className="flex gap-2">
        {[['bar','Bar Chart'],['pie','Pie Chart'],['table','Table']].map(([k,l]) => (
          <button key={k} onClick={() => setView(k)}
            className={`text-sm px-4 py-2 rounded-lg border transition-all ${
              view === k ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30' :
                           'text-brand-muted border-brand-border hover:text-brand-text'
            }`}>
            {l}
          </button>
        ))}
      </div>

      {/* Bar chart */}
      {view === 'bar' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-1">Units Sold by Location</h2>
          <p className="text-xs text-brand-muted mb-4">All-time total, sorted by volume</p>
          <ResponsiveContainer width="100%" height={Math.max(280, locations.length * 32)}>
            <BarChart data={locations} layout="vertical" margin={{ left: 15, right: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis dataKey="location" type="category" tick={{ fill: '#94a3b8', fontSize: 11 }} width={90} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                formatter={(v, name) => [v.toLocaleString('en-IN'), 'Units Sold']}
              />
              <Bar dataKey="total_units" radius={[0, 4, 4, 0]} name="Units">
                {locations.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Pie chart */}
      {view === 'pie' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Volume Share by Location</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={locations.slice(0, 8)}
                  dataKey="total_units"
                  nameKey="location"
                  cx="50%" cy="50%"
                  outerRadius={110}
                  label={({ location, share_pct }) => `${share_pct}%`}
                >
                  {locations.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Revenue Share by Location</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={locations.slice(0, 8)}
                  dataKey="total_revenue"
                  nameKey="location"
                  cx="50%" cy="50%"
                  outerRadius={110}
                  label={({ location, total_revenue }) => `${((total_revenue / totalRevenue) * 100).toFixed(1)}%`}
                >
                  {locations.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                  formatter={(v) => [fmt(v), 'Revenue']}
                />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Table view */}
      {view === 'table' && (
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-4">Location Performance Table</h2>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Location</th>
                  <th>Region</th>
                  <th>Units Sold</th>
                  <th>Revenue</th>
                  <th>Share %</th>
                  <th>YoY Growth</th>
                  <th>Top Model</th>
                </tr>
              </thead>
              <tbody>
                {locations.map((loc, i) => (
                  <tr key={i}>
                    <td className="text-brand-muted">{i + 1}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }}></span>
                        <span className="font-medium text-brand-text">{loc.location}</span>
                      </div>
                    </td>
                    <td className="text-brand-muted text-xs">{loc.region}</td>
                    <td className="font-semibold">{loc.total_units?.toLocaleString('en-IN')}</td>
                    <td>{fmt(loc.total_revenue)}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-brand-border rounded-full max-w-[80px]">
                          <div
                            className="h-1.5 rounded-full bg-saffron-500"
                            style={{ width: `${Math.min(100, loc.share_pct * 3)}%` }}
                          />
                        </div>
                        <span className="text-xs">{loc.share_pct}%</span>
                      </div>
                    </td>
                    <td><GrowthBadge pct={loc.yoy_growth} /></td>
                    <td className="text-xs text-brand-muted">{loc.top_model}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Insights */}
      <div className="card">
        <h2 className="text-sm font-semibold text-brand-text mb-3">Location Insights</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {/* Top grower */}
          {(() => {
            const growthLocs = locations.filter(l => l.yoy_growth !== null).sort((a, b) => b.yoy_growth - a.yoy_growth)
            const top = growthLocs[0]
            const bottom = growthLocs[growthLocs.length - 1]
            return (
              <>
                {top && (
                  <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                    <p className="text-green-400 font-semibold mb-1">Fastest Growing Location</p>
                    <p className="text-brand-text font-bold">{top.location}</p>
                    <p className="text-brand-muted">+{top.yoy_growth}% YoY · {top.total_units?.toLocaleString('en-IN')} units</p>
                    <p className="text-brand-muted">Top model: {top.top_model}</p>
                  </div>
                )}
                {bottom && bottom.yoy_growth < 0 && (
                  <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                    <p className="text-red-400 font-semibold mb-1">Needs Attention</p>
                    <p className="text-brand-text font-bold">{bottom.location}</p>
                    <p className="text-brand-muted">{bottom.yoy_growth}% YoY · Check local competition</p>
                    <p className="text-brand-muted">Consider promotional scheme or demo drive</p>
                  </div>
                )}
                <div className="p-3 rounded-lg bg-saffron-500/5 border border-saffron-500/20">
                  <p className="text-saffron-400 font-semibold mb-1">Volume Leader</p>
                  <p className="text-brand-text font-bold">{locations[0]?.location}</p>
                  <p className="text-brand-muted">{locations[0]?.share_pct}% of total sales · {locations[0]?.total_units?.toLocaleString('en-IN')} units</p>
                  <p className="text-brand-muted">Prioritise stock availability here</p>
                </div>
                <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <p className="text-blue-400 font-semibold mb-1">Stocking Recommendation</p>
                  <p className="text-brand-muted">
                    Top 3 locations account for{' '}
                    <span className="text-brand-text font-medium">
                      {locations.slice(0, 3).reduce((s, l) => s + l.share_pct, 0).toFixed(1)}%
                    </span> of all sales.
                    Maintain 60% of buffer stock at these locations.
                  </p>
                </div>
              </>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
