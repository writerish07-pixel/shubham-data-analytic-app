import React, { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown, Package, IndianRupee, Bell, Zap } from 'lucide-react'
import { getDashboard, getAlerts, getUpcomingFestivals } from '../services/api'

function KPICard({ title, value, sub, icon: Icon, trend, color = 'saffron' }) {
  const colorMap = {
    saffron: 'text-saffron-400 bg-saffron-500/10',
    green:   'text-green-400 bg-green-500/10',
    blue:    'text-blue-400 bg-blue-500/10',
    red:     'text-red-400 bg-red-500/10',
  }
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg ${colorMap[color]}`}>
          <Icon size={20} className={colorMap[color].split(' ')[0]} />
        </div>
        {trend !== undefined && (
          <span className={`flex items-center text-xs gap-1 ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {trend >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-brand-text">{value}</p>
      <p className="text-sm text-brand-muted mt-0.5">{title}</p>
      {sub && <p className="text-xs text-brand-muted mt-1">{sub}</p>}
    </div>
  )
}

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#a78bfa', '#f59e0b', '#ec4899', '#06b6d4', '#84cc16']

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [festivals, setFestivals] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboard(), getAlerts(), getUpcomingFestivals(60)])
      .then(([dash, alts, fests]) => {
        setData(dash)
        setAlerts(alts.slice(0, 3))
        setFestivals(fests.slice(0, 4))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  if (!data) return <p className="text-brand-muted">Failed to load dashboard data.</p>

  const fmt = (n) => n >= 10000000 ? `₹${(n / 10000000).toFixed(1)}Cr` :
                      n >= 100000  ? `₹${(n / 100000).toFixed(1)}L` : `₹${n.toLocaleString('en-IN')}`

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Units Sold YTD"
          value={data.total_units_ytd?.toLocaleString('en-IN') || '—'}
          sub="Year to date"
          icon={Package}
          trend={data.yoy_growth_pct}
          color="saffron"
        />
        <KPICard
          title="Revenue YTD"
          value={fmt(data.total_revenue_ytd || 0)}
          sub="Year to date"
          icon={IndianRupee}
          trend={data.yoy_growth_pct}
          color="green"
        />
        <KPICard
          title="YoY Growth"
          value={`${data.yoy_growth_pct > 0 ? '+' : ''}${data.yoy_growth_pct}%`}
          sub="vs same period last year"
          icon={TrendingUp}
          color={data.yoy_growth_pct >= 0 ? 'green' : 'red'}
        />
        <KPICard
          title="Forecast Accuracy"
          value={`${data.forecast_accuracy_pct}%`}
          sub="Model confidence"
          icon={Zap}
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Monthly trend */}
        <div className="card xl:col-span-2">
          <h2 className="text-sm font-semibold text-brand-text mb-4">Monthly Sales Trend (Last 12 Months)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.monthly_trend?.slice(-12) || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="month_name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
              <Line type="monotone" dataKey="units" stroke="#f97316" strokeWidth={2.5} dot={{ fill: '#f97316', r: 4 }} name="Units" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Upcoming festivals */}
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-4">Upcoming Festivals</h2>
          <div className="space-y-3">
            {festivals.length === 0 && <p className="text-brand-muted text-sm">No upcoming festivals in 60 days.</p>}
            {festivals.map((f, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.03] border border-brand-border/50">
                <div className="text-center min-w-[40px]">
                  <p className="text-lg font-bold text-saffron-400">{f.days_away}</p>
                  <p className="text-xs text-brand-muted">days</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-brand-text">{f.name}</p>
                  <p className="text-xs text-brand-muted">{f.date}</p>
                  <p className="text-xs text-green-400 mt-0.5">+{f.impact_pct}% demand expected</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Top 5 SKUs */}
        <div className="card xl:col-span-2">
          <h2 className="text-sm font-semibold text-brand-text mb-4">Top SKU Rankings</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={(data.sku_rankings || []).slice(0, 8)} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis dataKey="model_name" type="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={110} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
              <Bar dataKey="total_units_sold" fill="#f97316" radius={[0, 4, 4, 0]} name="Units Sold" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Active Alerts */}
        <div className="card">
          <h2 className="text-sm font-semibold text-brand-text mb-4 flex items-center gap-2">
            <Bell size={15} className="text-saffron-400" /> Active Alerts
          </h2>
          <div className="space-y-3">
            {alerts.length === 0 && <p className="text-brand-muted text-sm">No active alerts.</p>}
            {alerts.map((a, i) => (
              <div key={i} className={`p-3 rounded-lg border text-sm ${
                a.priority === 'high' ? 'bg-red-900/20 border-red-700/30' :
                a.priority === 'medium' ? 'bg-amber-900/20 border-amber-700/30' :
                'bg-brand-card border-brand-border'
              }`}>
                <p className={`font-medium ${
                  a.priority === 'high' ? 'text-red-400' :
                  a.priority === 'medium' ? 'text-amber-400' : 'text-brand-text'
                }`}>{a.title}</p>
                <p className="text-xs text-brand-muted mt-1 line-clamp-2">{a.message}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
