import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { AlertTriangle, TrendingDown, CheckCircle, IndianRupee, Download, Package, Info } from 'lucide-react'
import { getDispatchRecs, getWorkingCapital, getDispatchExportUrl } from '../services/api'

function RiskBadge({ type }) {
  if (type === 'understock') return <span className="badge-understock">⚠ Understock</span>
  if (type === 'overstock')  return <span className="badge-overstock">📦 Overstock</span>
  return <span className="badge-neutral">✓ Neutral</span>
}

function RiskBar({ score }) {
  const pct = Math.round(score * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-brand-border rounded-full">
        <div
          className={`h-1.5 rounded-full ${pct > 60 ? 'bg-red-500' : pct > 30 ? 'bg-amber-500' : 'bg-green-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-brand-muted w-8">{pct}%</span>
    </div>
  )
}

export default function DispatchPlanner() {
  const [recs, setRecs] = useState([])
  const [wc, setWc] = useState(null)
  const [leadTime, setLeadTime] = useState(21)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [stockSource, setStockSource] = useState(null)

  const load = () => {
    setLoading(true)
    Promise.all([getDispatchRecs(leadTime), getWorkingCapital()])
      .then(([r, w]) => {
        setRecs(r)
        setWc(w)
        if (r.length > 0) setStockSource(r[0].stock_source)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [leadTime])

  const filtered = filter === 'all' ? recs : recs.filter(r => r.risk_type === filter)

  const fmt = n => n >= 10000000 ? `₹${(n / 10000000).toFixed(1)}Cr` :
                   n >= 100000  ? `₹${(n / 100000).toFixed(1)}L` : `₹${n?.toLocaleString('en-IN')}`

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Stock source notice */}
      {stockSource && (
        <div className={`flex items-start gap-3 px-4 py-3 rounded-xl border text-xs ${
          stockSource === 'uploaded'
            ? 'bg-green-500/10 border-green-500/30 text-green-300'
            : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
        }`}>
          <Package size={14} className="mt-0.5 shrink-0" />
          <span>
            {stockSource === 'uploaded'
              ? <><span className="font-semibold">Using your uploaded stock inventory.</span> Dispatch quantities already subtract your current stock — no over-ordering.</>
              : <><span className="font-semibold">Stock estimated from sales history.</span> Upload your actual stock inventory (Upload Data → Current Stock) to get exact dispatch quantities.</>
            }
          </span>
        </div>
      )}

      {/* Working Capital Summary */}
      {wc && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Total Dispatch Value', value: fmt(wc.total_dispatch_value), icon: IndianRupee, color: 'saffron' },
            { label: 'Buffer Stock Value',   value: fmt(wc.total_buffer_value),   icon: CheckCircle,  color: 'green' },
            { label: 'Dead Stock Exposure',  value: fmt(wc.dead_stock_exposure),  icon: AlertTriangle,color: 'red' },
            { label: 'Capital Rotation',     value: `${wc.capital_rotation_days?.toFixed(0)} days`, icon: TrendingDown, color: 'blue' },
          ].map((m, i) => (
            <div key={i} className="card">
              <p className="text-xs text-brand-muted mb-1">{m.label}</p>
              <p className={`text-xl font-bold ${
                m.color === 'red' ? 'text-red-400' : m.color === 'green' ? 'text-green-400' :
                m.color === 'blue' ? 'text-blue-400' : 'text-saffron-400'
              }`}>{m.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Risk Score Chart */}
      <div className="card">
        <h2 className="text-sm font-semibold text-brand-text mb-4">Risk Score by Model (Top 15)</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={recs.slice(0, 15)} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
            <XAxis type="number" domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `${Math.round(v*100)}%`} />
            <YAxis dataKey="model_name" type="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={110} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
              formatter={(v) => [`${Math.round(v*100)}%`, 'Risk Score']}
            />
            <Bar dataKey="risk_score" radius={[0, 4, 4, 0]} name="Risk Score">
              {recs.slice(0, 15).map((r, i) => (
                <Cell key={i} fill={r.risk_type === 'understock' ? '#ef4444' : r.risk_type === 'overstock' ? '#f59e0b' : '#10b981'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Controls + Export */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-brand-muted">Lead Time:</label>
          <select
            value={leadTime}
            onChange={e => setLeadTime(Number(e.target.value))}
            className="bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-1.5"
          >
            {[14, 21, 30, 45].map(d => <option key={d} value={d}>{d} days</option>)}
          </select>
        </div>

        <div className="flex gap-2">
          {['all', 'understock', 'overstock', 'neutral'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                filter === f ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30' :
                               'text-brand-muted border-brand-border hover:text-brand-text'
              }`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
              {f !== 'all' && <span className="ml-1 text-brand-muted">({recs.filter(r => r.risk_type === f).length})</span>}
            </button>
          ))}
        </div>

        <span className="text-xs text-brand-muted">{filtered.length} SKUs</span>

        {/* Export button */}
        <a
          href={getDispatchExportUrl(leadTime)}
          download
          className="ml-auto flex items-center gap-2 text-xs bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-4 py-2 rounded-lg transition font-medium"
        >
          <Download size={13} /> Export Plan (CSV)
        </a>
      </div>

      {/* Recommendations Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-brand-text">Dispatch Recommendations — Next Month</h2>
          {stockSource === 'uploaded' && (
            <span className="text-[10px] bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-1 rounded-full">
              Stock-adjusted quantities
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Model</th>
                <th>Colour</th>
                <th title="Units forecast to sell in planning window">Forecast</th>
                <th title="Current stock on hand (from your upload or estimated)">Stock on Hand</th>
                <th title="Quantity to order/dispatch after deducting existing stock">Order Qty</th>
                <th>Buffer (+15%)</th>
                <th>Total Dispatch</th>
                <th>WC Impact</th>
                <th>Festival Boost</th>
                <th>Risk</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.sku_code}>
                  <td className="font-mono text-xs text-saffron-400">{r.sku_code}</td>
                  <td>{r.model_name}</td>
                  <td>{r.colour}</td>
                  <td className="text-brand-muted">{r.forecast_units}</td>
                  <td className={`font-medium ${
                    r.stock_source === 'uploaded' ? 'text-green-400' : 'text-amber-400'
                  }`}>
                    {r.current_stock}
                    <span className="text-[9px] text-brand-muted ml-1">
                      {r.stock_source === 'uploaded' ? '(real)' : '(est.)'}
                    </span>
                  </td>
                  <td className="font-semibold">{r.recommended_quantity}</td>
                  <td className="text-brand-muted">{r.buffer_stock}</td>
                  <td className="font-bold text-saffron-400">{r.total_dispatch}</td>
                  <td>₹{(r.working_capital_impact / 100000).toFixed(1)}L</td>
                  <td>
                    <span className={r.festival_factor > 1.2 ? 'text-amber-400 font-semibold' : 'text-brand-muted'}>
                      {r.festival_factor > 1 ? `+${Math.round((r.festival_factor - 1) * 100)}%` : 'None'}
                    </span>
                  </td>
                  <td><RiskBadge type={r.risk_type} /></td>
                  <td className="text-xs text-brand-muted max-w-[200px]">{r.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {wc?.high_risk_skus?.length > 0 && (
          <div className="mt-4 p-4 bg-red-900/10 border border-red-700/30 rounded-xl">
            <p className="text-sm font-medium text-red-400 mb-1">High Risk SKUs — Immediate Action Required</p>
            <p className="text-xs text-brand-muted">{wc.high_risk_skus.join(' • ')}</p>
          </div>
        )}

        {/* Summary footer */}
        {filtered.length > 0 && (
          <div className="mt-4 pt-4 border-t border-brand-border flex flex-wrap gap-6 text-xs text-brand-muted">
            <span>Total units to dispatch: <span className="text-brand-text font-semibold">{filtered.reduce((s, r) => s + r.total_dispatch, 0).toLocaleString('en-IN')}</span></span>
            <span>Total WC: <span className="text-brand-text font-semibold">{fmt(filtered.reduce((s, r) => s + r.working_capital_impact, 0))}</span></span>
            <span className="ml-auto text-[10px] text-brand-muted/60">
              <Info size={10} className="inline mr-1" />
              Quantities already deduct stock on hand
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
