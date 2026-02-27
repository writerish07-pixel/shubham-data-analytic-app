import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Truck, CalendarDays,
  MessageSquare, Bell, Globe, Menu, X, Bike, Upload
} from 'lucide-react'

import Dashboard         from './components/Dashboard'
import SalesAnalytics    from './components/SalesAnalytics'
import ForecastView      from './components/ForecastView'
import DispatchPlanner   from './components/DispatchPlanner'
import FestivalCalendar  from './components/FestivalCalendar'
import AICopilot         from './components/AICopilot'
import Alerts            from './components/Alerts'
import MarketIntelligence from './components/MarketIntelligence'
import UploadData        from './components/UploadData'
import { getAlertCount } from './services/api'

const NAV_ITEMS = [
  { path: '/',           label: 'Dashboard',          icon: LayoutDashboard },
  { path: '/sales',      label: 'Sales Analytics',    icon: TrendingUp },
  { path: '/forecast',   label: 'Forecast',           icon: TrendingUp },
  { path: '/dispatch',   label: 'Dispatch Planner',   icon: Truck },
  { path: '/festivals',  label: 'Festival Calendar',  icon: CalendarDays },
  { path: '/alerts',     label: 'Smart Alerts',       icon: Bell },
  { path: '/market',     label: 'Market Intel',       icon: Globe },
  { path: '/copilot',    label: 'AI Copilot',         icon: MessageSquare },
  { path: '/upload',     label: 'Upload Data',        icon: Upload },
]

function Sidebar({ open, onClose, alertCount }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={onClose} />
      )}
      <aside className={`
        fixed top-0 left-0 h-full w-64 bg-brand-card border-r border-brand-border z-30
        flex flex-col transition-transform duration-300
        ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-brand-border">
          <div className="w-9 h-9 rounded-xl bg-saffron-500/20 flex items-center justify-center">
            <Bike size={20} className="text-saffron-400" />
          </div>
          <div>
            <p className="text-sm font-bold text-brand-text leading-tight">Sales Intelligence</p>
            <p className="text-xs text-brand-muted">Two-Wheeler Analytics</p>
          </div>
          <button onClick={onClose} className="ml-auto lg:hidden text-brand-muted hover:text-white">
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(item => {
            const active = location.pathname === item.path
            return (
              <button
                key={item.path}
                onClick={() => { navigate(item.path); onClose() }}
                className={`nav-item w-full ${active ? 'active' : ''}`}
              >
                <item.icon size={17} />
                <span>{item.label}</span>
                {item.path === '/alerts' && alertCount > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
                    {alertCount}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-brand-border">
          <p className="text-xs text-brand-muted">Hero MotoCorp Intelligence</p>
          <p className="text-xs text-brand-muted">v1.0.0 · {new Date().getFullYear()}</p>
        </div>
      </aside>
    </>
  )
}

function Layout({ children, alertCount }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const currentPage = NAV_ITEMS.find(n => n.path === location.pathname)?.label || 'Dashboard'

  return (
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} alertCount={alertCount} />

      <div className="flex-1 lg:ml-64 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-10 bg-brand-bg/80 backdrop-blur border-b border-brand-border px-6 py-4 flex items-center gap-4">
          <button
            className="lg:hidden text-brand-muted hover:text-white"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={22} />
          </button>
          <h1 className="text-lg font-semibold text-brand-text">{currentPage}</h1>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-xs text-brand-muted hidden sm:block">
              {new Date().toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}
            </span>
            {alertCount > 0 && (
              <span className="flex items-center gap-1.5 bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-3 py-1.5 rounded-lg">
                <Bell size={13} />
                {alertCount} active {alertCount === 1 ? 'alert' : 'alerts'}
              </span>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    getAlertCount().then(d => setAlertCount(d.total)).catch(() => {})
  }, [])

  return (
    <BrowserRouter>
      <Layout alertCount={alertCount}>
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/sales"     element={<SalesAnalytics />} />
          <Route path="/forecast"  element={<ForecastView />} />
          <Route path="/dispatch"  element={<DispatchPlanner />} />
          <Route path="/festivals" element={<FestivalCalendar />} />
          <Route path="/alerts"    element={<Alerts />} />
          <Route path="/market"    element={<MarketIntelligence />} />
          <Route path="/copilot"   element={<AICopilot />} />
          <Route path="/upload"    element={<UploadData />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
