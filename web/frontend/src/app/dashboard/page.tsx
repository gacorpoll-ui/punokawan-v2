"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { TrendingUp, LogOut, Home, Bell, Settings, Menu, X } from "lucide-react"
import SignalCard from "@/components/dashboard/SignalCard"
import StatsGrid from "@/components/dashboard/StatsGrid"
import EquityCurve from "@/components/dashboard/EquityCurve"

export default function DashboardPage() {
  const [signal, setSignal] = useState<any>(null)
  const [performance, setPerformance] = useState<any>({
    total_trades: 0, win_rate: 0, profit_factor: 0,
    sharpe_ratio: 0, net_profit: 0, gross_profit: 0,
  })
  const [mobileNav, setMobileNav] = useState(false)

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sigRes, perfRes] = await Promise.all([
          fetch("/api/signals/public"),
          fetch("/api/performance").catch(() => null),
        ])
        const sig = await sigRes.json()
        setSignal(sig)
        if (perfRes) {
          const perf = await perfRes.json()
          setPerformance(perf)
        }
      } catch (e) {
        console.error("Failed to fetch data", e)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-navy flex">
      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 glass-strong border-r border-white/5 p-6">
        <Link href="/" className="flex items-center gap-2 mb-10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-navy" />
          </div>
          <span className="text-lg font-bold text-white">
            Puno<span className="gold-text">kawan</span>
          </span>
        </Link>

        <nav className="space-y-2 flex-1">
          {[
            { icon: Home, label: "Dashboard", active: true },
            { icon: Bell, label: "Signals", active: false },
            { icon: Settings, label: "Settings", active: false },
          ].map((item, i) => (
            <a
              key={i}
              href="#"
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition ${
                item.active
                  ? "bg-gold/10 text-gold font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </a>
          ))}
        </nav>

        <div className="border-t border-white/5 pt-4">
          <div className="text-xs text-slate-600 mb-1">Subscription</div>
          <div className="text-sm font-semibold text-gold">Free Trial &middot; 14 days left</div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-4 lg:p-8 overflow-auto">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between mb-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-navy" />
            </div>
            <span className="text-lg font-bold text-white">Punokawan</span>
          </Link>
          <button onClick={() => setMobileNav(!mobileNav)} className="text-white">
            {mobileNav ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Trading Dashboard</h1>
            <p className="text-sm text-slate-500">Real-time signals &amp; performance</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <div className="text-xs text-slate-500">Account Status</div>
              <div className="text-sm font-semibold text-profit">Active</div>
            </div>
            <div className="w-2 h-2 rounded-full bg-profit animate-pulse" />
          </div>
        </div>

        {/* Signal Card */}
        <div className="mb-8">
          <SignalCard signal={signal || { direction: "NO_TRADE", entry: 0, sl: 0, tp: 0, lot_size: 0, score: 0, rr_ratio: 0, session: "", tp_source: "" }} />
        </div>

        {/* Stats Grid */}
        <div className="mb-8">
          <h2 className="text-lg font-bold text-white mb-4">Performance Overview</h2>
          <StatsGrid performance={performance} />
        </div>

        {/* Equity Curve */}
        <div className="mb-8">
          <EquityCurve data={performance.monthly_breakdown || []} />
        </div>

        {/* Recent Signals */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-lg font-bold text-white mb-4">Recent Signals</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-white/5">
                  {["Direction", "Entry", "SL", "TP", "Score", "R:R", "Session", "Status"].map((h) => (
                    <th key={h} className="text-left py-3 px-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="text-slate-400">
                  <td colSpan={8} className="text-center py-12 text-slate-600">
                    No signals yet. Trading cycle will populate this table.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
