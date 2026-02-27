import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { CalendarDays, Heart } from 'lucide-react'
import { getUpcomingFestivals, getFestivalImpact, getMarriageSeason } from '../services/api'

const FESTIVAL_EMOJIS = {
  'Diwali': '🪔', 'Dhanteras': '💰', 'Navratri': '💃', 'Dussehra': '🏹',
  'Onam': '🌸', 'Pongal': '🍯', 'Holi': '🎨', 'Eid ul-Fitr': '🌙',
  'Akshaya Tritiya': '⭐', 'Bhai Dooj': '🎁', 'Gurpurab': '🙏',
  'Maha Shivratri': '🔱',
}

const TYPE_COLORS = {
  national: 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30',
  regional: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  auspicious: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

const SELECTED_FESTIVALS = ['Diwali', 'Dhanteras', 'Navratri', 'Dussehra', 'Onam', 'Akshaya Tritiya']

export default function FestivalCalendar() {
  const [upcoming, setUpcoming] = useState([])
  const [marriage, setMarriage] = useState(null)
  const [selectedFestival, setSelectedFestival] = useState('Diwali')
  const [impactHistory, setImpactHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getUpcomingFestivals(180), getMarriageSeason()])
      .then(([up, mar]) => { setUpcoming(up); setMarriage(mar) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedFestival) {
      getFestivalImpact(selectedFestival)
        .then(setImpactHistory)
        .catch(console.error)
    }
  }, [selectedFestival])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-2 border-saffron-500 border-t-transparent rounded-full" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Marriage Season Banner */}
      {marriage && (
        <div className={`card border-2 ${marriage.currently_in_season ? 'border-pink-500/40 bg-pink-900/10' : 'border-brand-border'}`}>
          <div className="flex items-start gap-4">
            <Heart size={24} className={marriage.currently_in_season ? 'text-pink-400' : 'text-brand-muted'} />
            <div className="flex-1">
              <h3 className={`font-semibold ${marriage.currently_in_season ? 'text-pink-400' : 'text-brand-text'}`}>
                Marriage Season {marriage.currently_in_season ? '– Currently Active!' : '– Upcoming'}
              </h3>
              {marriage.currently_in_season && marriage.current_season && (
                <p className="text-sm text-brand-muted mt-1">
                  <strong className="text-brand-text">{marriage.current_season.season} Season</strong> is active.
                  Expected uplift: <strong className="text-green-400">+{marriage.current_season.uplift_pct}%</strong>.
                  High demand colours: {marriage.current_season.colours?.join(', ')}.
                </p>
              )}
              {!marriage.currently_in_season && marriage.next_season && (
                <p className="text-sm text-brand-muted mt-1">
                  Next marriage season in <strong className="text-saffron-400">{marriage.next_season.days_away} days</strong>.
                  Expected uplift: <strong className="text-green-400">+{marriage.next_season.uplift_pct}%</strong>.
                  Stock recommended: {marriage.next_season.recommended_colours?.join(', ')}.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Upcoming Festivals Grid */}
      <div>
        <h2 className="text-sm font-semibold text-brand-text mb-4">Upcoming Festivals (Next 180 Days)</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {upcoming.map((f, i) => (
            <div key={i} className="card hover:border-saffron-500/40 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <span className="text-2xl">{FESTIVAL_EMOJIS[f.name] || '🎉'}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${TYPE_COLORS[f.type] || TYPE_COLORS.national}`}>
                  {f.type}
                </span>
              </div>
              <h3 className="font-semibold text-brand-text">{f.name}</h3>
              <p className="text-sm text-brand-muted">{f.date}</p>
              {f.region && <p className="text-xs text-blue-400 mt-0.5">{f.region}</p>}
              <div className="mt-3 flex items-center justify-between">
                <div className="text-center">
                  <p className="text-xl font-bold text-saffron-400">{f.days_away}</p>
                  <p className="text-xs text-brand-muted">days away</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold text-green-400">+{f.impact_pct}%</p>
                  <p className="text-xs text-brand-muted">demand boost</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold text-blue-400">{f.pre_window_days || 14}</p>
                  <p className="text-xs text-brand-muted">pre-window</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Festival Impact History */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="text-sm font-semibold text-brand-text">Historical Festival Impact</h2>
          <div className="flex flex-wrap gap-2 ml-auto">
            {SELECTED_FESTIVALS.map(f => (
              <button key={f} onClick={() => setSelectedFestival(f)}
                className={`text-xs px-3 py-1 rounded-lg border transition-all ${
                  selectedFestival === f
                    ? 'bg-saffron-500/20 text-saffron-400 border-saffron-500/30'
                    : 'text-brand-muted border-brand-border hover:text-brand-text'
                }`}
              >
                {FESTIVAL_EMOJIS[f]} {f}
              </button>
            ))}
          </div>
        </div>

        {impactHistory.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={impactHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `+${v}%`} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9' }}
                  formatter={(v) => [`+${v}%`, 'Demand Uplift']} />
                <Bar dataKey="impact_pct" fill="#f97316" radius={[4, 4, 0, 0]} name="Impact %" />
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 overflow-x-auto">
              <table className="data-table">
                <thead><tr><th>Year</th><th>Festival Date</th><th>Expected Impact</th><th>Pre-window Days</th></tr></thead>
                <tbody>
                  {impactHistory.map((h, i) => (
                    <tr key={i}>
                      <td>{h.year}</td>
                      <td>{h.date}</td>
                      <td className="text-green-400 font-semibold">+{h.impact_pct}%</td>
                      <td className="text-brand-muted">14–21 days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-brand-muted text-sm">No historical data for {selectedFestival}.</p>
        )}
      </div>
    </div>
  )
}
