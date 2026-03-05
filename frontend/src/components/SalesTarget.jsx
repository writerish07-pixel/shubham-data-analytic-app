import React, { useEffect, useState, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine, Legend
} from 'recharts'
import {
  Target, TrendingUp, TrendingDown, Zap, AlertTriangle,
  CheckCircle, Clock, Edit3, Trash2, Plus, ChevronDown,
  ChevronUp, Info, Calendar, Download, Users,
} from 'lucide-react'
import {
  getTargetsForMonth, getTargetPathway, getFullYearPlan,
  getAutoTargetPreview, setOverallTarget, setModelTarget,
  deleteModelTarget, getAllModels, getSkuTargets,
} from '../services/api'

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
]

const RISK_CONFIG = {
  achieved:  { color: 'text-green-400',  bg: 'bg-green-500/10',  border: 'border-green-500/30',  icon: CheckCircle,    label: 'Target Achieved!' },
  on_track:  { color: 'text-green-400',  bg: 'bg-green-500/10',  border: 'border-green-500/30',  icon: TrendingUp,     label: 'On Track' },
  at_risk:   { color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/30',  icon: AlertTriangle,  label: 'At Risk' },
  critical:  { color: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/30',    icon: AlertTriangle,  label: 'Critical' },
}

function MonthSelector({ year, month, onChange }) {
  const currentYear = new Date().getFullYear()
  const years = [currentYear - 1, currentYear, currentYear + 1]
  return (
    <div className="flex items-center gap-3">
      <select
        value={year}
        onChange={e => onChange(+e.target.value, month)}
        className="bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
      >
        {years.map(y => <option key={y} value={y}>{y}</option>)}
      </select>
      <select
        value={month}
        onChange={e => onChange(year, +e.target.value)}
        className="bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
      >
        {MONTH_NAMES.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
      </select>
    </div>
  )
}

function RiskBadge({ risk }) {
  const cfg = RISK_CONFIG[risk] || RISK_CONFIG.on_track
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${cfg.color} ${cfg.bg} border ${cfg.border}`}>
      <Icon size={13} />
      {cfg.label}
    </span>
  )
}

function ProgressBar({ pct, color = 'bg-saffron-500' }) {
  const clamped = Math.min(100, Math.max(0, pct || 0))
  return (
    <div className="w-full h-2 bg-brand-border rounded-full overflow-hidden">
      <div
        className={`h-2 rounded-full transition-all ${color}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

export default function SalesTarget() {
  const now = new Date()
  const [year, setYear]   = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [tab, setTab]     = useState('overview') // overview | models | pathway | annual

  const [targetData, setTargetData]   = useState(null)
  const [pathway, setPathway]         = useState(null)
  const [annualPlan, setAnnualPlan]   = useState([])
  const [allModels, setAllModels]     = useState([])
  const [autoPreview, setAutoPreview] = useState(null)
  const [loading, setLoading]         = useState(true)

  // Edit states
  const [editOverall, setEditOverall] = useState(false)
  const [overallInput, setOverallInput] = useState('')
  const [growthInput, setGrowthInput]   = useState('15')
  const [savingOverall, setSavingOverall] = useState(false)

  const [addModelOpen, setAddModelOpen]   = useState(false)
  const [modelForm, setModelForm]         = useState({ model_name: '', target_units: '', notes: '' })
  const [savingModel, setSavingModel]     = useState(false)
  const [deletingModel, setDeletingModel] = useState(null)

  // SKU targets
  const [skuTargets, setSkuTargets] = useState(null)
  const [skuLoading, setSkuLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [td, pw, ap, mdls, ap2] = await Promise.all([
        getTargetsForMonth(year, month),
        getTargetPathway(year, month),
        getFullYearPlan(year),
        getAllModels(),
        getAutoTargetPreview(year, month, 15),
      ])
      setTargetData(td)
      setPathway(pw)
      setAnnualPlan(ap)
      setAllModels(mdls.models || [])
      setAutoPreview(ap2)
      if (td?.overall?.target_units) {
        setOverallInput(String(td.overall.target_units))
        setGrowthInput(String(td.overall.growth_pct ?? 15))
      } else if (ap2?.target_units) {
        setOverallInput(String(ap2.target_units))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => { loadData() }, [loadData])

  // Auto-calculate target units when growth % changes (only while in edit mode)
  useEffect(() => {
    if (!editOverall) return
    const gPct = parseFloat(growthInput)
    if (isNaN(gPct) || gPct < 0) return
    const timer = setTimeout(() => {
      getAutoTargetPreview(year, month, gPct)
        .then(preview => {
          setAutoPreview(preview)
          setOverallInput(String(preview.target_units))
        })
        .catch(() => {})
    }, 400)
    return () => clearTimeout(timer)
  }, [growthInput, year, month, editOverall])

  // Load SKU targets when switching to SKU tab
  useEffect(() => {
    if (tab !== 'sku') return
    setSkuLoading(true)
    getSkuTargets(year, month)
      .then(setSkuTargets)
      .catch(console.error)
      .finally(() => setSkuLoading(false))
  }, [tab, year, month])

  const handleMonthChange = (y, m) => { setYear(y); setMonth(m) }

  const handleSaveOverall = async () => {
    setSavingOverall(true)
    try {
      await setOverallTarget(year, month, {
        target_units: parseInt(overallInput, 10),
        growth_pct: parseFloat(growthInput),
        notes: '',
      })
      setEditOverall(false)
      await loadData()
    } catch (e) { console.error(e) }
    finally { setSavingOverall(false) }
  }

  const handleSaveModel = async () => {
    if (!modelForm.model_name || !modelForm.target_units) return
    setSavingModel(true)
    try {
      await setModelTarget(year, month, {
        model_name: modelForm.model_name,
        target_units: parseInt(modelForm.target_units, 10),
        notes: modelForm.notes || '',
      })
      setModelForm({ model_name: '', target_units: '', notes: '' })
      setAddModelOpen(false)
      await loadData()
    } catch (e) { console.error(e) }
    finally { setSavingModel(false) }
  }

  const handleDeleteModel = async (modelName) => {
    setDeletingModel(modelName)
    try {
      await deleteModelTarget(year, month, modelName)
      await loadData()
    } catch (e) { console.error(e) }
    finally { setDeletingModel(null) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  const overall   = targetData?.overall
  const models    = targetData?.model_targets || []
  const actuals   = targetData?.actuals || {}
  const achieved  = actuals.units_sold || 0
  const target    = overall?.target_units || autoPreview?.target_units || 0
  const achPct    = target > 0 ? Math.round((achieved / target) * 100) : 0
  const gap       = Math.max(0, target - achieved)
  const pw        = pathway || {}

  const riskLevel = pw.risk || 'on_track'
  const riskCfg   = RISK_CONFIG[riskLevel] || RISK_CONFIG.on_track

  // Annual chart data
  const annualChartData = annualPlan.map(m => ({
    name: MONTH_NAMES[m.month - 1].slice(0, 3),
    target: m.target_units || 0,
    actuals: m.actual_units || 0,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-brand-text flex items-center gap-2">
            <Target size={20} className="text-saffron-400" />
            Sales Target Planner
          </h1>
          <p className="text-xs text-brand-muted mt-0.5">
            Set, track and achieve monthly sales targets with model-wise breakdown
          </p>
        </div>
        <MonthSelector year={year} month={month} onChange={handleMonthChange} />
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
        {[
          ['overview', 'Overview'],
          ['models',   'Model Targets'],
          ['sku',      'SKU Targets'],
          ['pathway',  'Achievement Pathway'],
          ['annual',   'Annual Plan'],
        ].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`text-sm px-4 py-2 rounded-lg border transition-all ${
              tab === k
                ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30'
                : 'text-brand-muted border-brand-border hover:text-brand-text'
            }`}>
            {l}
          </button>
        ))}
      </div>

      {/* ══ OVERVIEW TAB ══════════════════════════════════════════════════════════ */}
      {tab === 'overview' && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <Target size={15} className="text-saffron-400" />
                <span className="text-xs text-brand-muted">Monthly Target</span>
                {overall?.is_manual && (
                  <span className="text-[10px] text-blue-400 border border-blue-400/30 rounded px-1">manual</span>
                )}
              </div>
              <p className="text-2xl font-bold text-brand-text">
                {target > 0 ? target.toLocaleString('en-IN') : '—'}
              </p>
              <p className="text-xs text-brand-muted mt-1">
                {overall ? `${overall.growth_pct ?? 15}% growth target` : 'Auto: 15% growth'}
              </p>
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={15} className="text-green-400" />
                <span className="text-xs text-brand-muted">Units Sold</span>
              </div>
              <p className="text-2xl font-bold text-brand-text">{achieved.toLocaleString('en-IN')}</p>
              <p className="text-xs text-brand-muted mt-1">{MONTH_NAMES[month - 1]} {year} actuals</p>
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <Zap size={15} className="text-blue-400" />
                <span className="text-xs text-brand-muted">Achievement</span>
              </div>
              <p className="text-2xl font-bold text-brand-text">{achPct}%</p>
              <ProgressBar pct={achPct} color={achPct >= 100 ? 'bg-green-500' : achPct >= 75 ? 'bg-saffron-500' : 'bg-red-500'} />
            </div>
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={15} className={riskCfg.color} />
                <span className="text-xs text-brand-muted">Gap to Close</span>
              </div>
              <p className="text-2xl font-bold text-brand-text">
                {gap > 0 ? gap.toLocaleString('en-IN') : '0'}
              </p>
              <RiskBadge risk={riskLevel} />
            </div>
          </div>

          {/* Target Setting Card */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-brand-text">
                  {MONTH_NAMES[month - 1]} {year} — Overall Target
                </h2>
                {autoPreview && (
                  <p className="text-xs text-brand-muted mt-0.5">
                    Auto-computed: <span className="text-saffron-400 font-medium">{autoPreview.target_units?.toLocaleString('en-IN')} units</span>
                    {' '}(Last Year Same Month: {autoPreview.basis_units?.toLocaleString('en-IN')} × {autoPreview.input_growth_pct ?? autoPreview.growth_pct}% growth)
                  </p>
                )}
              </div>
              {!editOverall && (
                <button
                  onClick={() => setEditOverall(true)}
                  className="flex items-center gap-1.5 text-xs text-saffron-400 hover:text-saffron-300 border border-saffron-500/30 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <Edit3 size={13} /> Edit Target
                </button>
              )}
            </div>

            {editOverall ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-brand-muted mb-1 block">Target Units</label>
                    <input
                      type="number"
                      value={overallInput}
                      onChange={e => setOverallInput(e.target.value)}
                      className="w-full bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
                      placeholder="e.g. 150"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-brand-muted mb-1 block">Growth % (vs last year same month)</label>
                    <input
                      type="number"
                      value={growthInput}
                      onChange={e => setGrowthInput(e.target.value)}
                      className="w-full bg-brand-bg border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
                      placeholder="15"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveOverall}
                    disabled={savingOverall}
                    className="bg-saffron-500 hover:bg-saffron-600 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {savingOverall ? 'Saving…' : 'Save Target'}
                  </button>
                  <button
                    onClick={() => setEditOverall(false)}
                    className="text-sm text-brand-muted hover:text-brand-text border border-brand-border px-4 py-2 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  {autoPreview && (
                    <button
                      onClick={() => setOverallInput(String(autoPreview.target_units))}
                      className="text-xs text-blue-400 hover:text-blue-300 ml-auto"
                    >
                      Use auto ({autoPreview.target_units?.toLocaleString('en-IN')})
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 rounded-lg bg-saffron-500/5 border border-saffron-500/20">
                  <p className="text-xs text-brand-muted mb-1">Last Year Same Month</p>
                  <p className="text-lg font-bold text-brand-text">
                    {overall?.basis_units?.toLocaleString('en-IN') || autoPreview?.basis_units?.toLocaleString('en-IN') || '—'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-saffron-500/5 border border-saffron-500/20">
                  <p className="text-xs text-brand-muted mb-1">Min Growth</p>
                  <p className="text-lg font-bold text-saffron-400">+{overall?.growth_pct ?? 15}%</p>
                </div>
                <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                  <p className="text-xs text-brand-muted mb-1">Target Units</p>
                  <p className="text-lg font-bold text-green-400">{target > 0 ? target.toLocaleString('en-IN') : '—'}</p>
                </div>
              </div>
            )}
          </div>

          {/* Model targets summary */}
          {models.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-brand-text mb-3">Model-wise Targets (this month)</h2>
              <div className="space-y-2">
                {models.map((m, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs text-brand-muted w-4">{i + 1}</span>
                    <span className="text-sm text-brand-text flex-1">{m.model_name}</span>
                    <span className="text-sm font-semibold text-saffron-400">{m.target_units?.toLocaleString('en-IN')}</span>
                    <span className="text-xs text-brand-muted">(+{m.growth_pct?.toFixed(1)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ══ MODEL TARGETS TAB ═══════════════════════════════════════════════════ */}
      {tab === 'models' && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-brand-text">Model-wise Targets</h2>
                <p className="text-xs text-brand-muted mt-0.5">
                  Set company-given model targets. Overall target auto-adjusts to their sum.
                </p>
              </div>
              <button
                onClick={() => setAddModelOpen(v => !v)}
                className="flex items-center gap-1.5 text-xs bg-saffron-500 hover:bg-saffron-600 text-white rounded-lg px-3 py-1.5 transition-colors"
              >
                <Plus size={13} /> Add Model Target
              </button>
            </div>

            {/* Add model form */}
            {addModelOpen && (
              <div className="mb-4 p-4 rounded-lg bg-brand-bg border border-saffron-500/20">
                <p className="text-xs font-semibold text-saffron-400 mb-3">New Model Target</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-xs text-brand-muted mb-1 block">Model Name</label>
                    <select
                      value={modelForm.model_name}
                      onChange={e => setModelForm(f => ({ ...f, model_name: e.target.value }))}
                      className="w-full bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
                    >
                      <option value="">— Select model —</option>
                      {allModels.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-brand-muted mb-1 block">Target Units</label>
                    <input
                      type="number"
                      value={modelForm.target_units}
                      onChange={e => setModelForm(f => ({ ...f, target_units: e.target.value }))}
                      className="w-full bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
                      placeholder="e.g. 40"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-brand-muted mb-1 block">Notes (optional)</label>
                    <input
                      type="text"
                      value={modelForm.notes}
                      onChange={e => setModelForm(f => ({ ...f, notes: e.target.value }))}
                      className="w-full bg-brand-card border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-saffron-500"
                      placeholder="e.g. Company directive"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveModel}
                    disabled={savingModel || !modelForm.model_name || !modelForm.target_units}
                    className="bg-saffron-500 hover:bg-saffron-600 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {savingModel ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    onClick={() => setAddModelOpen(false)}
                    className="text-sm text-brand-muted hover:text-brand-text border border-brand-border px-4 py-2 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Model targets table */}
            {models.length === 0 ? (
              <div className="text-center py-10">
                <Target size={28} className="text-brand-muted mx-auto mb-2" />
                <p className="text-brand-muted text-sm">No model-wise targets set for this month.</p>
                <p className="text-brand-muted text-xs mt-1">
                  Add model targets when your company provides model-specific quotas.
                  Overall target will auto-adjust to their sum.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Model</th>
                      <th>Target Units</th>
                      <th>Growth %</th>
                      <th>Basis (LY)</th>
                      <th>Notes</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.map((m, i) => (
                      <tr key={i}>
                        <td className="text-brand-muted">{i + 1}</td>
                        <td className="font-medium text-brand-text">{m.model_name}</td>
                        <td className="font-semibold text-saffron-400">{m.target_units?.toLocaleString('en-IN')}</td>
                        <td>
                          <span className="text-green-400">+{m.growth_pct?.toFixed(1)}%</span>
                        </td>
                        <td className="text-brand-muted">{m.basis_units?.toLocaleString('en-IN') || '—'}</td>
                        <td className="text-xs text-brand-muted">{m.notes || '—'}</td>
                        <td>
                          <button
                            onClick={() => handleDeleteModel(m.model_name)}
                            disabled={deletingModel === m.model_name}
                            className="text-red-400 hover:text-red-300 disabled:opacity-40 transition-colors"
                            title="Remove model target"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-brand-border">
                      <td colSpan={2} className="text-xs font-semibold text-brand-text pt-3">Total (Model Sum)</td>
                      <td className="font-bold text-saffron-400 pt-3">
                        {models.reduce((s, m) => s + (m.target_units || 0), 0).toLocaleString('en-IN')}
                      </td>
                      <td colSpan={4}></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>

          {/* Info note */}
          <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-xs text-blue-400">
            <Info size={14} className="mt-0.5 shrink-0" />
            <span>
              When model-wise targets are set, the overall monthly target is automatically set to their sum.
              You can still override it manually from the Overview tab.
            </span>
          </div>
        </div>
      )}

      {/* ══ SKU TARGETS TAB ════════════════════════════════════════════════════ */}
      {tab === 'sku' && (
        <div className="space-y-4">
          {skuLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-xs text-blue-400">
                <Info size={14} className="mt-0.5 shrink-0" />
                <span>
                  SKU targets are distributed from model targets based on each SKU's 3-month sales mix.
                  Share this list with your sales team for model + colour-wise quotas.
                  {skuTargets && !skuTargets.has_model_targets && (
                    <span className="text-amber-400 ml-1">
                      Set model targets in the "Model Targets" tab for more accurate SKU distribution.
                    </span>
                  )}
                </span>
              </div>

              {/* Summary + Export */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex gap-4 text-sm">
                  <span className="text-brand-muted">
                    Overall Target: <span className="text-saffron-400 font-semibold">{skuTargets?.overall_target?.toLocaleString('en-IN')}</span>
                  </span>
                  <span className="text-brand-muted">
                    Total SKUs: <span className="text-brand-text font-semibold">{skuTargets?.sku_targets?.length || 0}</span>
                  </span>
                  <span className="text-brand-muted">
                    Allocated: <span className="text-green-400 font-semibold">{skuTargets?.total_allocated?.toLocaleString('en-IN')}</span>
                  </span>
                </div>
                {skuTargets?.sku_targets?.length > 0 && (
                  <button
                    onClick={() => {
                      const rows = [
                        ['#', 'SKU Code', 'Model', 'Colour', 'Target Units', 'Daily Target', 'Weekly Target', '3M Sales Mix %'],
                        ...skuTargets.sku_targets.map((s, i) => [
                          i + 1, s.sku_code, s.model_name, s.colour,
                          s.target_units, s.daily_target, s.weekly_target, s.sku_share_pct,
                        ]),
                      ]
                      const csv = rows.map(r => r.join(',')).join('\n')
                      const blob = new Blob([csv], { type: 'text/csv' })
                      const a = document.createElement('a')
                      a.href = URL.createObjectURL(blob)
                      a.download = `sku_targets_${MONTH_NAMES[month - 1]}_${year}.csv`
                      a.click()
                    }}
                    className="flex items-center gap-2 text-xs bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-4 py-2 rounded-lg transition font-medium"
                  >
                    <Download size={13} /> Export for Sales Team (CSV)
                  </button>
                )}
              </div>

              <div className="card">
                <div className="flex items-center gap-2 mb-4">
                  <Users size={16} className="text-saffron-400" />
                  <h2 className="text-sm font-semibold text-brand-text">
                    SKU-wise Sales Targets — {MONTH_NAMES[month - 1]} {year}
                  </h2>
                </div>
                {!skuTargets?.sku_targets?.length ? (
                  <div className="text-center py-10">
                    <Target size={28} className="text-brand-muted mx-auto mb-2" />
                    <p className="text-brand-muted text-sm">No SKU targets available.</p>
                    <p className="text-brand-muted text-xs mt-1">
                      Set an overall or model-wise target first, then come back to see SKU breakdown.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>SKU Code</th>
                          <th>Model</th>
                          <th>Colour</th>
                          <th title="Monthly units to sell">Monthly Target</th>
                          <th title="Units per day needed">Daily Target</th>
                          <th title="Units per week needed">Weekly Target</th>
                          <th title="SKU share of model target based on 3-month sales mix">Sales Mix %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {skuTargets.sku_targets.map((s, i) => (
                          <tr key={s.sku_code}>
                            <td className="text-brand-muted">{i + 1}</td>
                            <td className="font-mono text-xs text-saffron-400">{s.sku_code}</td>
                            <td className="font-medium text-brand-text">{s.model_name}</td>
                            <td className="text-brand-muted">{s.colour}</td>
                            <td className="font-bold text-saffron-400 text-base">{s.target_units?.toLocaleString('en-IN')}</td>
                            <td className="text-blue-400">{s.daily_target}</td>
                            <td className="text-green-400">{s.weekly_target}</td>
                            <td className="text-brand-muted text-xs">{s.sku_share_pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t border-brand-border font-semibold">
                          <td colSpan={4} className="text-brand-text pt-3">Total</td>
                          <td className="text-saffron-400 pt-3">
                            {skuTargets.sku_targets.reduce((s, r) => s + (r.target_units || 0), 0).toLocaleString('en-IN')}
                          </td>
                          <td colSpan={3}></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ══ PATHWAY TAB ════════════════════════════════════════════════════════ */}
      {tab === 'pathway' && (
        <div className="space-y-6">
          {!pw.target_units ? (
            <div className="card text-center py-12">
              <Clock size={32} className="text-brand-muted mx-auto mb-3" />
              <p className="text-brand-text font-medium">No target set for {MONTH_NAMES[month - 1]} {year}</p>
              <p className="text-brand-muted text-sm mt-1">
                Set a target in the Overview tab to see the achievement pathway.
              </p>
            </div>
          ) : (
            <>
              {/* Risk + Summary */}
              <div className="card">
                <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                  <div>
                    <h2 className="text-sm font-semibold text-brand-text">
                      {MONTH_NAMES[month - 1]} {year} — Achievement Pathway
                    </h2>
                    <p className="text-xs text-brand-muted mt-0.5">
                      {pw.working_days_remaining} working days remaining in the month
                    </p>
                  </div>
                  <RiskBadge risk={pw.risk} />
                </div>

                <div className="mb-4">
                  <div className="flex justify-between text-xs text-brand-muted mb-1">
                    <span>{pw.actual_units?.toLocaleString('en-IN')} sold</span>
                    <span>{pw.target_units?.toLocaleString('en-IN')} target</span>
                  </div>
                  <ProgressBar
                    pct={pw.achieved_pct}
                    color={pw.achieved_pct >= 100 ? 'bg-green-500' : pw.achieved_pct >= 75 ? 'bg-saffron-500' : 'bg-red-500'}
                  />
                  <p className="text-xs text-brand-muted mt-1 text-right">{pw.achieved_pct}% achieved</p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-3 rounded-lg bg-brand-bg border border-brand-border text-center">
                    <p className="text-xs text-brand-muted mb-1">Units Sold</p>
                    <p className="text-xl font-bold text-brand-text">{pw.actual_units?.toLocaleString('en-IN')}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-brand-bg border border-brand-border text-center">
                    <p className="text-xs text-brand-muted mb-1">Gap to Close</p>
                    <p className="text-xl font-bold text-red-400">{pw.gap?.toLocaleString('en-IN')}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-saffron-500/5 border border-saffron-500/20 text-center">
                    <p className="text-xs text-brand-muted mb-1">Daily Need</p>
                    <p className="text-xl font-bold text-saffron-400">{pw.daily_needed}</p>
                    <p className="text-[10px] text-brand-muted">units/day</p>
                  </div>
                  <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-center">
                    <p className="text-xs text-brand-muted mb-1">Working Days Left</p>
                    <p className="text-xl font-bold text-blue-400">{pw.working_days_remaining}</p>
                    <p className="text-[10px] text-brand-muted">business days</p>
                  </div>
                </div>
              </div>

              {/* Weekly Plan */}
              {pw.weekly_plan && pw.weekly_plan.length > 0 && (
                <div className="card">
                  <h2 className="text-sm font-semibold text-brand-text mb-4">Weekly Breakdown Plan</h2>
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Week</th>
                          <th>Dates</th>
                          <th>Working Days</th>
                          <th>Target Units</th>
                          <th>Daily Rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pw.weekly_plan.map((w, i) => (
                          <tr key={i}>
                            <td className="font-medium text-brand-text">Week {w.week}</td>
                            <td className="text-xs text-brand-muted">{w.dates}</td>
                            <td>{w.working_days}</td>
                            <td className="font-semibold text-saffron-400">{w.target_units}</td>
                            <td className="text-blue-400">{w.daily_rate}/day</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Festival boost events */}
              {pw.festival_boost && pw.festival_boost.length > 0 && (
                <div className="card">
                  <h2 className="text-sm font-semibold text-brand-text mb-3 flex items-center gap-2">
                    <Calendar size={15} className="text-saffron-400" /> Festival Opportunities This Month
                  </h2>
                  <div className="space-y-2">
                    {pw.festival_boost.map((f, i) => (
                      <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-saffron-500/5 border border-saffron-500/20">
                        <div>
                          <p className="text-sm font-medium text-brand-text">{f.name}</p>
                          <p className="text-xs text-brand-muted">{f.date} · {f.days_away} days away</p>
                        </div>
                        <span className="text-green-400 text-sm font-semibold">+{f.impact_pct}% demand</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Key Actions */}
              {pw.key_actions && pw.key_actions.length > 0 && (
                <div className="card">
                  <h2 className="text-sm font-semibold text-brand-text mb-3 flex items-center gap-2">
                    <Zap size={15} className="text-saffron-400" /> Key Actions to Hit Target
                  </h2>
                  <div className="space-y-2">
                    {pw.key_actions.map((action, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-brand-bg border border-brand-border">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-saffron-500/20 text-saffron-400 text-xs flex items-center justify-center font-bold">
                          {i + 1}
                        </span>
                        <p className="text-sm text-brand-text">{action}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Model-wise pathway */}
              {pw.model_pathways && pw.model_pathways.length > 0 && (
                <div className="card">
                  <h2 className="text-sm font-semibold text-brand-text mb-4">Model-wise Pathway</h2>
                  <div className="space-y-3">
                    {pw.model_pathways.map((m, i) => (
                      <div key={i} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-brand-text font-medium">{m.model_name}</span>
                          <span className="text-brand-muted">
                            {m.actual}/{m.target} units · {m.daily_needed}/day needed
                          </span>
                        </div>
                        <ProgressBar
                          pct={m.target > 0 ? (m.actual / m.target) * 100 : 0}
                          color={m.actual >= m.target ? 'bg-green-500' : 'bg-saffron-500'}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ══ ANNUAL PLAN TAB ════════════════════════════════════════════════════ */}
      {tab === 'annual' && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-1">
              {year} Annual Target vs Actuals
            </h2>
            <p className="text-xs text-brand-muted mb-4">
              12-month view — targets (auto if not set) vs actual sales
            </p>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={annualChartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                  formatter={(v, name) => [v?.toLocaleString('en-IN'), name === 'target' ? 'Target' : 'Actuals']}
                />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 11 }} />
                <Bar dataKey="target"  fill="#f97316" opacity={0.6} radius={[3, 3, 0, 0]} name="target" />
                <Bar dataKey="actuals" fill="#10b981" radius={[3, 3, 0, 0]} name="actuals" />
                <ReferenceLine y={0} stroke="#475569" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Annual table */}
          <div className="card">
            <h2 className="text-sm font-semibold text-brand-text mb-4">Month-by-Month Breakdown</h2>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Target</th>
                    <th>Actuals</th>
                    <th>Achievement</th>
                    <th>Gap / Surplus</th>
                    <th>Growth Target</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {annualPlan.map((m, i) => {
                    const pct = m.target_units > 0 ? Math.round((m.actual_units / m.target_units) * 100) : null
                    const gap = (m.actual_units || 0) - (m.target_units || 0)
                    return (
                      <tr key={i} className={m.month === month && m.year === year ? 'bg-saffron-500/5' : ''}>
                        <td className="font-medium text-brand-text">
                          {MONTH_NAMES[m.month - 1].slice(0, 3)} {m.year}
                          {m.month === month && m.year === year && (
                            <span className="ml-2 text-[10px] text-saffron-400 border border-saffron-500/30 rounded px-1">current</span>
                          )}
                        </td>
                        <td className="font-semibold">
                          {m.target_units?.toLocaleString('en-IN') || '—'}
                          {!m.is_manual && m.target_units && (
                            <span className="ml-1 text-[10px] text-brand-muted">auto</span>
                          )}
                        </td>
                        <td>{m.actual_units?.toLocaleString('en-IN') || '—'}</td>
                        <td>
                          {pct !== null ? (
                            <div className="flex items-center gap-2">
                              <ProgressBar pct={pct} color={pct >= 100 ? 'bg-green-500' : pct >= 75 ? 'bg-saffron-500' : 'bg-red-500'} />
                              <span className="text-xs whitespace-nowrap">{pct}%</span>
                            </div>
                          ) : '—'}
                        </td>
                        <td>
                          {gap !== 0 && m.actual_units ? (
                            <span className={gap >= 0 ? 'text-green-400' : 'text-red-400'}>
                              {gap > 0 ? '+' : ''}{gap.toLocaleString('en-IN')}
                            </span>
                          ) : '—'}
                        </td>
                        <td className="text-brand-muted text-xs">+{m.growth_pct ?? 15}%</td>
                        <td>
                          {m.actual_units ? (
                            <RiskBadge risk={
                              pct >= 100 ? 'achieved' :
                              pct >= 80  ? 'on_track' :
                              pct >= 60  ? 'at_risk' : 'critical'
                            } />
                          ) : (
                            <span className="text-xs text-brand-muted">Upcoming</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-brand-border font-semibold">
                    <td className="text-brand-text pt-3">Annual Total</td>
                    <td className="text-saffron-400 pt-3">
                      {annualPlan.reduce((s, m) => s + (m.target_units || 0), 0).toLocaleString('en-IN')}
                    </td>
                    <td className="text-green-400 pt-3">
                      {annualPlan.reduce((s, m) => s + (m.actual_units || 0), 0).toLocaleString('en-IN')}
                    </td>
                    <td colSpan={4}></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
