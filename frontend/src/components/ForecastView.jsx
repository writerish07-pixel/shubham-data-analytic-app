import React, { useEffect, useState } from 'react'
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { getForecastAll, getForecastSummary, runWhatIf } from '../services/api'

const SCENARIOS = [
  { value: 'diwali_shift',      label: 'Diwali shifts N days',      unit: 'days',    default: -10 },
  { value: 'fuel_price',        label: 'Fuel price changes by %',   unit: '%',       default: 5 },
  { value: 'competitor_launch', label: 'Competitor launch impact',  unit: '(0-1)',   default: 0.5 },
  { value: 'marriage_season',   label: 'Extra marriage muhurat days', unit: 'days',  default: 7 },
]

export default function ForecastView() {
  const [summary, setSummary] = useState([])
  const [allFc, setAllFc] = useState([])
  const [selectedSku, setSelectedSku] = useState('')
  const [whatIfScenario, setWhatIfScenario] = useState('diwali_shift')
  const [whatIfParam, setWhatIfParam] = useState(-10)
  const [whatIfResult, setWhatIfResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [whatIfLoading, setWhatIfLoading] = useState(false)

  useEffect(() => {
    Promise.all([getForecastSummary(60), getForecastAll(60)])
      .then(([sum, all]) => {
        setSummary(sum)
        setAllFc(all)
        if (sum.length > 0) setSelectedSku(sum[0].sku_code)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleWhatIf = async () => {
    setWhatIfLoading(true)
    try {
      const result = await runWhatIf({ scenario: whatIfScenario, parameter: Number(whatIfParam) })
      setWhatIfResult(result)
    } catch (e) { console.error(e) }
    finally { setWhatIfLoading(false) }
  }

  // Chart data for selected SKU
  const skuForecast = allFc
    .filter(f => f.sku_code === selectedSku)
    .slice(0, 60)
    .map(f => ({
      date: f.forecast_date,
      predicted: parseFloat(f.predicted_quantity?.toFixed(1)),
      lower: parseFloat(f.confidence_lower?.toFixed(1)),
      upper: parseFloat(f.confidence_upper?.toFixed(1)),
      festival_boost: f.festival_boost,
    }))

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* SKU Forecast Chart */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="text-sm font-semibold text-brand-text">60-Day SKU Forecast</h2>
          <select
            value={selectedSku}
            onChange={e => setSelectedSku(e.target.value)}
            className="ml-auto bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-1.5"
          >
            {summary.map(s => (
              <option key={s.sku_code} value={s.sku_code}>
                {s.model_name} – {s.colour} ({s.sku_code})
              </option>
            ))}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={skuForecast}>
            <defs>
              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="upperGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }}
              tickFormatter={v => v?.slice(5)} interval={6} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
            <Area type="monotone" dataKey="upper" stroke="#3b82f6" fill="url(#upperGrad)" strokeDasharray="4 2" name="CI Upper" strokeWidth={1} />
            <Area type="monotone" dataKey="predicted" stroke="#f97316" fill="url(#predGrad)" strokeWidth={2.5} name="Predicted" />
            <Area type="monotone" dataKey="lower" stroke="#64748b" fill="transparent" strokeDasharray="4 2" name="CI Lower" strokeWidth={1} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Forecast Summary Table */}
      <div className="card">
        <h2 className="text-sm font-semibold text-brand-text mb-4">Forecast Summary – All SKUs</h2>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>SKU</th><th>Model</th><th>Colour</th>
                <th>30-Day Forecast</th><th>60-Day Forecast</th>
                <th>Festival Impact</th><th>Peak Day</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((s, i) => (
                <tr key={s.sku_code} className={selectedSku === s.sku_code ? 'bg-saffron-500/5' : ''}>
                  <td className="font-mono text-xs text-saffron-400 cursor-pointer" onClick={() => setSelectedSku(s.sku_code)}>{s.sku_code}</td>
                  <td>{s.model_name}</td>
                  <td>{s.colour}</td>
                  <td className="font-semibold">{Math.round(s.total_forecast_30d)}</td>
                  <td className="font-semibold">{Math.round(s.total_forecast_60d)}</td>
                  <td>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      s.festival_impact === 'High' ? 'bg-red-900/30 text-red-400' :
                      s.festival_impact === 'Medium' ? 'bg-amber-900/30 text-amber-400' :
                      'bg-green-900/30 text-green-400'
                    }`}>{s.festival_impact}</span>
                  </td>
                  <td className="text-brand-muted text-xs">{s.peak_day || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* What-If Simulator */}
      <div className="card">
        <h2 className="text-sm font-semibold text-brand-text mb-4">What-If Simulator</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-brand-muted mb-1">Scenario</label>
            <select
              value={whatIfScenario}
              onChange={e => {
                setWhatIfScenario(e.target.value)
                const sc = SCENARIOS.find(s => s.value === e.target.value)
                setWhatIfParam(sc?.default || 0)
              }}
              className="w-full bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2"
            >
              {SCENARIOS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-brand-muted mb-1">
              Parameter ({SCENARIOS.find(s => s.value === whatIfScenario)?.unit})
            </label>
            <input
              type="number"
              value={whatIfParam}
              onChange={e => setWhatIfParam(e.target.value)}
              className="w-full bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleWhatIf}
              disabled={whatIfLoading}
              className="w-full bg-saffron-500 hover:bg-saffron-600 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
            >
              {whatIfLoading ? 'Simulating…' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {whatIfResult && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
            {[
              { label: 'Baseline Units (60d)', value: whatIfResult.baseline_units?.toFixed(0) },
              { label: 'Adjusted Units (60d)', value: whatIfResult.adjusted_units?.toFixed(0) },
              { label: 'Delta Units', value: `${whatIfResult.delta_units > 0 ? '+' : ''}${whatIfResult.delta_units?.toFixed(0)}` },
              { label: 'Delta %', value: `${whatIfResult.delta_pct > 0 ? '+' : ''}${whatIfResult.delta_pct}%` },
            ].map((m, i) => (
              <div key={i} className="bg-white/[0.03] rounded-xl p-4 border border-brand-border/50">
                <p className="text-xs text-brand-muted mb-1">{m.label}</p>
                <p className={`text-xl font-bold ${i >= 2 ? (whatIfResult.delta_units >= 0 ? 'text-green-400' : 'text-red-400') : 'text-brand-text'}`}>
                  {m.value}
                </p>
              </div>
            ))}
            <div className="lg:col-span-4 bg-amber-900/10 border border-amber-700/30 rounded-xl p-4">
              <p className="text-sm text-amber-300">{whatIfResult.notes}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
