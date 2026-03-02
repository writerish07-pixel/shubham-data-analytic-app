import React, { useEffect, useState, useCallback } from 'react'
import { Package, AlertTriangle, CheckCircle, TrendingUp, Download, Info, RefreshCw } from 'lucide-react'
import { getStockHealth, getTargetDispatchExportUrl } from '../services/api'

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
]

const STATUS_CONFIG = {
  critical: { label: 'Critical',  color: 'text-red-400',   bg: 'bg-red-500/10',   border: 'border-red-500/30',   bar: 'bg-red-500'   },
  low:      { label: 'Low Stock', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', bar: 'bg-amber-500' },
  ok:       { label: 'OK',        color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30', bar: 'bg-green-500' },
  excess:   { label: 'Excess',    color: 'text-blue-400',  bg: 'bg-blue-500/10',  border: 'border-blue-500/30',  bar: 'bg-blue-500'  },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.ok
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.color} ${cfg.bg} border ${cfg.border}`}>
      {cfg.label}
    </span>
  )
}

function CoverageBar({ ratio }) {
  const pct = Math.min(120, Math.round((ratio || 0) * 100))
  const color = pct >= 120 ? 'bg-blue-500' : pct >= 80 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 bg-brand-border rounded-full overflow-hidden">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className="text-xs text-brand-muted w-10 text-right">{Math.round((ratio || 0) * 100)}%</span>
    </div>
  )
}

export default function StockInventory() {
  const now = new Date()
  // Default to next month (plan for next month from current month)
  const defaultMonth = now.getMonth() === 11 ? 1 : now.getMonth() + 2
  const defaultYear  = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear()

  const [year, setYear]     = useState(defaultYear)
  const [month, setMonth]   = useState(defaultMonth)
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getStockHealth(year, month)
      setData(result)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => { load() }, [load])

  const currentYear = now.getFullYear()
  const years = [currentYear, currentYear + 1]

  const items   = data?.items || []
  const summary = data?.summary || {}
  const filtered = filter === 'all' ? items : items.filter(i => i.status === filter)

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-brand-text flex items-center gap-2">
            <Package size={20} className="text-saffron-400" />
            Stock Health vs Target
          </h1>
          <p className="text-xs text-brand-muted mt-0.5">
            Current stock compared to what's needed for{' '}
            <span className="text-saffron-400">{MONTH_NAMES[month - 1]} {year}</span> target
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select value={year} onChange={e => setYear(+e.target.value)}
            className="bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500">
            {years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <select value={month} onChange={e => setMonth(+e.target.value)}
            className="bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500">
            {MONTH_NAMES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <button onClick={load} className="text-brand-muted hover:text-brand-text border border-brand-border rounded-lg p-2">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Stock source notice */}
      {data && (
        <div className={`flex items-start gap-3 px-4 py-3 rounded-xl border text-xs ${
          data.stock_source === 'uploaded'
            ? 'bg-green-500/10 border-green-500/30 text-green-300'
            : data.stock_source === 'estimated'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <Package size={14} className="mt-0.5 shrink-0" />
          <span>
            {data.stock_source === 'uploaded'
              ? <><strong>Using your uploaded stock inventory.</strong> Coverage ratios are based on actual stock.</>
              : data.stock_source === 'estimated'
                ? <><strong>Stock estimated from sales history.</strong> Upload your actual stock (Upload Data → Current Stock) for precise planning.</>
                : <><strong>No stock data uploaded yet.</strong> Go to Upload Data → Current Stock to upload your inventory, then come back for accurate stock health analysis.</>
            }
          </span>
        </div>
      )}

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card border-l-2 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={15} className="text-red-400" />
            <span className="text-xs text-brand-muted">Critical</span>
          </div>
          <p className="text-2xl font-bold text-red-400">{summary.critical_count ?? 0}</p>
          <p className="text-xs text-brand-muted mt-1">models need urgent order</p>
        </div>
        <div className="card border-l-2 border-amber-500">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={15} className="text-amber-400" />
            <span className="text-xs text-brand-muted">Low Stock</span>
          </div>
          <p className="text-2xl font-bold text-amber-400">{summary.low_count ?? 0}</p>
          <p className="text-xs text-brand-muted mt-1">models below 80% coverage</p>
        </div>
        <div className="card border-l-2 border-green-500">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={15} className="text-green-400" />
            <span className="text-xs text-brand-muted">OK / Adequate</span>
          </div>
          <p className="text-2xl font-bold text-green-400">{summary.ok_count ?? 0}</p>
          <p className="text-xs text-brand-muted mt-1">models sufficiently stocked</p>
        </div>
        <div className="card border-l-2 border-blue-500">
          <div className="flex items-center gap-2 mb-2">
            <Package size={15} className="text-blue-400" />
            <span className="text-xs text-brand-muted">Excess</span>
          </div>
          <p className="text-2xl font-bold text-blue-400">{summary.excess_count ?? 0}</p>
          <p className="text-xs text-brand-muted mt-1">models overstocked</p>
        </div>
      </div>

      {/* Stock totals */}
      {summary.total_current_stock !== undefined && (
        <div className="card">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-xs text-brand-muted mb-1">Current Stock (Total)</p>
              <p className="text-2xl font-bold text-brand-text">{summary.total_current_stock?.toLocaleString('en-IN')}</p>
              <p className="text-xs text-brand-muted">units on hand</p>
            </div>
            <div>
              <p className="text-xs text-brand-muted mb-1">Target Needed ({MONTH_NAMES[month - 1]})</p>
              <p className="text-2xl font-bold text-saffron-400">{summary.total_target_needed?.toLocaleString('en-IN')}</p>
              <p className="text-xs text-brand-muted">overall target: {data?.overall_target?.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-xs text-brand-muted mb-1">Overall Coverage</p>
              <p className="text-2xl font-bold text-brand-text">
                {summary.total_target_needed > 0
                  ? `${Math.round((summary.total_current_stock / summary.total_target_needed) * 100)}%`
                  : '—'}
              </p>
              <p className="text-xs text-brand-muted">stock vs target</p>
            </div>
          </div>
        </div>
      )}

      {/* Filter + export */}
      <div className="flex flex-wrap items-center gap-3">
        {['all', 'critical', 'low', 'ok', 'excess'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors capitalize ${
              filter === f
                ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30'
                : 'text-brand-muted border-brand-border hover:text-brand-text'
            }`}>
            {f === 'all' ? 'All Models' : f}
            {f !== 'all' && (
              <span className="ml-1 text-brand-muted">
                ({items.filter(i => i.status === f).length})
              </span>
            )}
          </button>
        ))}
        <a
          href={getTargetDispatchExportUrl(year, month)}
          download
          className="ml-auto flex items-center gap-2 text-xs bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-4 py-2 rounded-lg transition font-medium"
        >
          <Download size={13} /> Export Order Plan (CSV)
        </a>
      </div>

      {/* Health table */}
      {items.length === 0 ? (
        <div className="card text-center py-12">
          <Package size={32} className="text-brand-muted mx-auto mb-3" />
          <p className="text-brand-text font-medium">No data available</p>
          <p className="text-brand-muted text-sm mt-1">
            Upload sales data and set a target for {MONTH_NAMES[month - 1]} {year} to see stock health.
          </p>
        </div>
      ) : (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-brand-text">
              Model-wise Stock Health — {MONTH_NAMES[month - 1]} {year}
            </h2>
            <span className="text-xs text-brand-muted">{filtered.length} models</span>
          </div>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Current Stock</th>
                  <th>Target Needed</th>
                  <th>Coverage</th>
                  <th>Gap / Surplus</th>
                  <th>Daily Sales</th>
                  <th>Days of Stock</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, i) => (
                  <tr key={i}>
                    <td><StatusBadge status={item.status} /></td>
                    <td className="font-medium text-brand-text">{item.model_name}</td>
                    <td className="font-semibold">
                      {item.current_stock?.toLocaleString('en-IN')}
                      {item.source === 'auto_distributed' && (
                        <span className="ml-1 text-[9px] text-brand-muted">(est.)</span>
                      )}
                    </td>
                    <td>{item.target_needed?.toLocaleString('en-IN')}</td>
                    <td><CoverageBar ratio={item.coverage_ratio} /></td>
                    <td>
                      {item.gap > 0 ? (
                        <span className="text-red-400 font-semibold">-{item.gap?.toLocaleString('en-IN')}</span>
                      ) : item.surplus > 0 ? (
                        <span className="text-blue-400">+{item.surplus?.toLocaleString('en-IN')}</span>
                      ) : (
                        <span className="text-green-400">✓</span>
                      )}
                    </td>
                    <td className="text-brand-muted">{item.daily_velocity}/day</td>
                    <td>
                      <span className={
                        item.days_of_stock < 10 ? 'text-red-400 font-semibold' :
                        item.days_of_stock < 20 ? 'text-amber-400' : 'text-green-400'
                      }>
                        {item.days_of_stock >= 999 ? '∞' : `${item.days_of_stock}d`}
                      </span>
                    </td>
                    <td className="text-xs">
                      {item.status === 'critical' && (
                        <span className="text-red-400 font-medium">Order {item.gap} units NOW</span>
                      )}
                      {item.status === 'low' && (
                        <span className="text-amber-400">Order {item.gap} units soon</span>
                      )}
                      {item.status === 'ok' && (
                        <span className="text-green-400">No action needed</span>
                      )}
                      {item.status === 'excess' && (
                        <span className="text-blue-400">Skip order this month</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Insight notes */}
      {summary.critical_count > 0 && (
        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20">
          <p className="text-red-400 font-semibold text-sm mb-1 flex items-center gap-2">
            <AlertTriangle size={15} /> Urgent Action Required
          </p>
          <p className="text-xs text-brand-muted">
            {summary.critical_count} model{summary.critical_count > 1 ? 's are' : ' is'} critically understocked for {MONTH_NAMES[month - 1]}.
            Place dispatch orders immediately — company lead time is typically 21 days.
          </p>
        </div>
      )}

      <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-xs text-blue-400">
        <Info size={14} className="mt-0.5 shrink-0" />
        <span>
          Coverage ratio = current stock ÷ target needed for this month.
          {' '}Target distribution uses {data?.has_stock_data ? 'your model-wise targets from Sales Targets page' : '3-month historical sales mix'}.
          Go to <strong>Dispatch Planner → Target Plan</strong> to see exact order quantities with festival adjustment and 15% buffer.
        </span>
      </div>
    </div>
  )
}
