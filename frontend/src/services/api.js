import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE, timeout: 30000 })

// ─── Sales ───────────────────────────────────────────────────────────────────
export const getDashboard     = ()           => api.get('/api/sales/dashboard').then(r => r.data)
export const getYoY           = ()           => api.get('/api/sales/yoy').then(r => r.data)
export const getMoM           = (months=24)  => api.get('/api/sales/mom', { params: { months } }).then(r => r.data)
export const getSkuPerf       = ()           => api.get('/api/sales/sku-performance').then(r => r.data)
export const getTopPerformers = (limit=10)   => api.get('/api/sales/top-performers', { params: { limit } }).then(r => r.data)
export const getSlowMovers    = ()           => api.get('/api/sales/slow-movers').then(r => r.data)
export const getColourAnalysis= ()           => api.get('/api/sales/colour-analysis').then(r => r.data)
export const getSeasonalPatterns = ()        => api.get('/api/sales/seasonal-patterns').then(r => r.data)

// ─── Forecast ────────────────────────────────────────────────────────────────
export const getForecastSummary = (days=60) => api.get('/api/forecast/summary', { params: { horizon_days: days } }).then(r => r.data)
export const getForecastAll     = (days=60) => api.get('/api/forecast/', { params: { horizon_days: days } }).then(r => r.data)
export const getForecastSku     = (sku, days=60) => api.get(`/api/forecast/sku/${sku}`, { params: { horizon_days: days } }).then(r => r.data)
export const runWhatIf          = (body)    => api.post('/api/forecast/what-if', body).then(r => r.data)

// ─── Dispatch ────────────────────────────────────────────────────────────────
export const getDispatchRecs    = (lead=21) => api.get('/api/dispatch/recommendations', { params: { lead_time_days: lead } }).then(r => r.data)
export const getWorkingCapital  = ()        => api.get('/api/dispatch/working-capital').then(r => r.data)
export const getRiskScores      = ()        => api.get('/api/dispatch/risk-scores').then(r => r.data)

// ─── Festivals ───────────────────────────────────────────────────────────────
export const getUpcomingFestivals = (days=90) => api.get('/api/festivals/upcoming', { params: { days_ahead: days } }).then(r => r.data)
export const getFullCalendar       = ()        => api.get('/api/festivals/calendar').then(r => r.data)
export const getFestivalImpact     = (name)    => api.get(`/api/festivals/impact/${encodeURIComponent(name)}`).then(r => r.data)
export const getMarriageSeason     = ()        => api.get('/api/festivals/marriage-season').then(r => r.data)

// ─── Alerts ───────────────────────────────────────────────────────────────────
export const getAlerts       = ()  => api.get('/api/alerts/').then(r => r.data)
export const getCriticalAlerts = () => api.get('/api/alerts/critical').then(r => r.data)
export const getAlertCount   = ()  => api.get('/api/alerts/count').then(r => r.data)

// ─── Copilot ─────────────────────────────────────────────────────────────────
export const chatCopilot     = (body) => api.post('/api/copilot/chat', body).then(r => r.data)
export const getCopilotSuggestions = () => api.get('/api/copilot/suggestions').then(r => r.data)

// ─── Market ───────────────────────────────────────────────────────────────────
export const getMarketAll    = ()  => api.get('/api/market/all').then(r => r.data)
export const getMarketTrends = ()  => api.get('/api/market/trends').then(r => r.data)
export const getCompetitorNews = () => api.get('/api/market/competitor-news').then(r => r.data)
export const getEvTrends     = ()  => api.get('/api/market/ev-trends').then(r => r.data)

// ─── Data Upload ──────────────────────────────────────────────────────────────
export const uploadData      = (formData, onProgress) =>
  api.post('/api/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  }).then(r => r.data)
export const getUploadStatus = () => api.get('/api/upload/status').then(r => r.data)
