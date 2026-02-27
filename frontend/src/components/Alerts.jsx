import React, { useEffect, useState } from 'react'
import { Bell, AlertTriangle, Info, CheckCircle, Calendar, TrendingDown, Package } from 'lucide-react'
import { getAlerts } from '../services/api'

const ALERT_ICONS = {
  festival_approaching:     Calendar,
  marriage_season:          CheckCircle,
  marriage_season_approaching: Calendar,
  slow_moving_inventory:    TrendingDown,
  high_growth_sku:          CheckCircle,
  year_end_clearance:       Package,
}

const PRIORITY_CONFIG = {
  high:   { color: 'red',   label: '🔴 High',   bg: 'bg-red-900/20 border-red-700/30 hover:border-red-600/50' },
  medium: { color: 'amber', label: '🟡 Medium', bg: 'bg-amber-900/20 border-amber-700/30 hover:border-amber-600/50' },
  low:    { color: 'blue',  label: '🔵 Low',    bg: 'bg-brand-card border-brand-border hover:border-brand-muted/50' },
}

function AlertCard({ alert }) {
  const [expanded, setExpanded] = useState(false)
  const pConfig = PRIORITY_CONFIG[alert.priority] || PRIORITY_CONFIG.low
  const Icon = ALERT_ICONS[alert.alert_type] || Bell

  return (
    <div
      className={`p-4 rounded-xl border transition-all cursor-pointer ${pConfig.bg}`}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 p-1.5 rounded-lg ${
          alert.priority === 'high' ? 'bg-red-500/20' :
          alert.priority === 'medium' ? 'bg-amber-500/20' : 'bg-blue-500/20'
        }`}>
          <Icon size={15} className={
            alert.priority === 'high' ? 'text-red-400' :
            alert.priority === 'medium' ? 'text-amber-400' : 'text-blue-400'
          } />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className={`font-medium text-sm ${
              alert.priority === 'high' ? 'text-red-300' :
              alert.priority === 'medium' ? 'text-amber-300' : 'text-brand-text'
            }`}>{alert.title}</p>
            <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full border ${
              alert.priority === 'high' ? 'bg-red-900/40 text-red-400 border-red-700/40' :
              alert.priority === 'medium' ? 'bg-amber-900/40 text-amber-400 border-amber-700/40' :
              'bg-blue-900/40 text-blue-400 border-blue-700/40'
            }`}>{pConfig.label}</span>
          </div>
          <p className={`text-sm text-brand-muted mt-1 ${expanded ? '' : 'line-clamp-2'}`}>
            {alert.message}
          </p>
          {alert.related_festival && (
            <span className="inline-block mt-2 text-xs bg-saffron-500/10 text-saffron-400 border border-saffron-500/20 rounded-full px-2 py-0.5">
              {alert.related_festival}
            </span>
          )}
          {alert.sku_code && (
            <span className="inline-block ml-2 mt-2 text-xs font-mono bg-white/5 text-brand-muted border border-brand-border rounded-full px-2 py-0.5">
              {alert.sku_code}
            </span>
          )}
        </div>
      </div>
      {alert.action_required && (
        <div className="mt-3 ml-10">
          <span className="text-xs text-saffron-400">⚡ Action required</span>
        </div>
      )}
    </div>
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.priority === filter)

  const counts = {
    all:    alerts.length,
    high:   alerts.filter(a => a.priority === 'high').length,
    medium: alerts.filter(a => a.priority === 'medium').length,
    low:    alerts.filter(a => a.priority === 'low').length,
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Alerts', count: counts.all, color: 'saffron' },
          { label: 'High Priority', count: counts.high, color: 'red' },
          { label: 'Medium Priority', count: counts.medium, color: 'amber' },
          { label: 'Low Priority', count: counts.low, color: 'blue' },
        ].map((c, i) => (
          <div key={i} className="card text-center">
            <p className={`text-3xl font-bold ${
              c.color === 'red' ? 'text-red-400' : c.color === 'amber' ? 'text-amber-400' :
              c.color === 'blue' ? 'text-blue-400' : 'text-saffron-400'
            }`}>{c.count}</p>
            <p className="text-xs text-brand-muted mt-1">{c.label}</p>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'high', 'medium', 'low'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`text-sm px-4 py-2 rounded-lg border transition-colors ${
              filter === f ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30' :
                            'text-brand-muted border-brand-border hover:text-brand-text'
            }`}>
            {f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
          </button>
        ))}
      </div>

      {/* Alert cards */}
      {filtered.length === 0 ? (
        <div className="card text-center py-12">
          <Bell size={40} className="text-brand-muted mx-auto mb-3" />
          <p className="text-brand-muted">No alerts for this filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((a, i) => <AlertCard key={a.id || i} alert={a} />)}
        </div>
      )}
    </div>
  )
}
