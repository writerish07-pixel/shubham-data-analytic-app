import React, { useEffect, useState } from 'react'
import { Globe, TrendingUp, TrendingDown, Zap } from 'lucide-react'
import { getMarketAll } from '../services/api'

const CATEGORY_CONFIG = {
  trends:      { label: 'Trends',      color: 'blue',   icon: TrendingUp },
  competitor:  { label: 'Competitor',  color: 'red',    icon: Zap },
  ev_trends:   { label: 'EV Trends',   color: 'green',  icon: Zap },
  fuel:        { label: 'Fuel',        color: 'amber',  icon: TrendingDown },
  policy:      { label: 'Policy',      color: 'purple', icon: Globe },
  market:      { label: 'Market',      color: 'saffron', icon: TrendingUp },
}

function ImpactBar({ score }) {
  const pct = Math.abs(score) * 100
  const positive = score >= 0
  return (
    <div className="flex items-center gap-2 mt-2">
      <span className="text-xs text-brand-muted w-16">Impact:</span>
      <div className="flex-1 h-1.5 bg-brand-border rounded-full">
        <div
          className={`h-1.5 rounded-full ${positive ? 'bg-green-500' : 'bg-red-500'}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className={`text-xs font-medium w-12 text-right ${positive ? 'text-green-400' : 'text-red-400'}`}>
        {positive ? '+' : ''}{score?.toFixed(2)}
      </span>
    </div>
  )
}

function MarketCard({ item }) {
  const catConf = CATEGORY_CONFIG[item.category] || CATEGORY_CONFIG.market
  const Icon = catConf.icon

  const colorMap = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    red:  'bg-red-500/10 text-red-400 border-red-500/20',
    green:'bg-green-500/10 text-green-400 border-green-500/20',
    amber:'bg-amber-500/10 text-amber-400 border-amber-500/20',
    purple:'bg-purple-500/10 text-purple-400 border-purple-500/20',
    saffron:'bg-saffron-500/10 text-saffron-400 border-saffron-500/20',
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-3 mb-3">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${colorMap[catConf.color]}`}>
          {catConf.label}
        </span>
        <span className="text-xs text-brand-muted">{item.data_date}</span>
      </div>
      <h3 className="font-semibold text-brand-text text-sm leading-snug mb-2">{item.title}</h3>
      <p className="text-xs text-brand-muted leading-relaxed">{item.summary}</p>
      <ImpactBar score={item.impact_score || 0} />
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-brand-muted">Source: {item.source}</span>
        <div className="flex flex-wrap gap-1">
          {(item.tags || []).slice(0, 3).map((t, i) => (
            <span key={i} className="text-xs bg-white/5 text-brand-muted rounded px-1.5 py-0.5">#{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function MarketIntelligence() {
  const [data, setData] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMarketAll().then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  const categories = ['all', ...Object.keys(CATEGORY_CONFIG)]
  const filtered = filter === 'all' ? data : data.filter(d => d.category === filter)

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  // Sentiment summary
  const avgImpact = data.reduce((s, d) => s + (d.impact_score || 0), 0) / Math.max(1, data.length)
  const positives = data.filter(d => (d.impact_score || 0) > 0).length
  const negatives = data.filter(d => (d.impact_score || 0) < 0).length

  return (
    <div className="space-y-6">
      {/* Market Sentiment Bar */}
      <div className="card">
        <h2 className="text-sm font-semibold text-brand-text mb-4">Market Sentiment Overview</h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-green-400">{positives}</p>
            <p className="text-xs text-brand-muted">Positive signals</p>
          </div>
          <div>
            <p className={`text-2xl font-bold ${avgImpact >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {avgImpact >= 0 ? '+' : ''}{(avgImpact * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-brand-muted">Avg market impact</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-400">{negatives}</p>
            <p className="text-xs text-brand-muted">Risk signals</p>
          </div>
        </div>
        <div className="mt-4 h-2 bg-brand-border rounded-full overflow-hidden">
          <div
            className="h-2 bg-gradient-to-r from-green-500 to-saffron-500 rounded-full"
            style={{ width: `${Math.min(100, 50 + avgImpact * 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-brand-muted mt-1">
          <span>Bearish</span><span>Neutral</span><span>Bullish</span>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map(c => (
          <button key={c} onClick={() => setFilter(c)}
            className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
              filter === c ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30' :
                            'text-brand-muted border-brand-border hover:text-brand-text'
            }`}>
            {c === 'all' ? 'All' : CATEGORY_CONFIG[c]?.label || c}
          </button>
        ))}
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map((item, i) => <MarketCard key={i} item={item} />)}
      </div>
    </div>
  )
}
