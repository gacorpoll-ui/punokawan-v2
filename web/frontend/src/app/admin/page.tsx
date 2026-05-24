"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  TrendingUp, Users, Activity, Shield, Server, Signal, Settings,
  BarChart3, DollarSign, Trash2, Edit, RefreshCw, LogOut, Home, Bell
} from "lucide-react"

function authHeaders(t: string) {
  return { Authorization: "Bearer " + t, "Content-Type": "application/json" }
}

export default function AdminDashboard() {
  const router = useRouter()
  const [token, setToken] = useState("")
  const [users, setUsers] = useState<any[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [system, setSystem] = useState<any>(null)
  const [perf, setPerf] = useState<any>(null)
  const [tab, setTab] = useState("users")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem("token") || ""
    setToken(t)
    if (!t) { router.push("/login"); return }
    fetchAll(t)
  }, [])

  async function fetchAll(t: string) {
    setLoading(true)
    try {
      const [uRes, sRes, sysRes, pRes] = await Promise.all([
        fetch("/api/admin/users", { headers: authHeaders(t) }),
        fetch("/api/admin/signals?limit=30", { headers: authHeaders(t) }),
        fetch("/api/admin/system", { headers: authHeaders(t) }),
        fetch("/api/admin/performance", { headers: authHeaders(t) }),
      ])
      if (uRes.status === 403) { router.push("/login"); return }
      if (uRes.ok) setUsers((await uRes.json()).users || [])
      if (sRes.ok) setSignals((await sRes.json()).signals || [])
      if (sysRes.ok) setSystem(await sysRes.json())
      if (pRes.ok) setPerf(await pRes.json())
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  async function updateTier(userId: string, tier: string) {
    await fetch("/api/admin/users/" + userId + "/subscription", {
      method: "PUT", headers: authHeaders(token),
      body: JSON.stringify({ tier }),
    })
    fetchAll(token)
  }

  async function deleteUser(userId: string) {
    if (!confirm("Delete this user?")) return
    await fetch("/api/admin/users/" + userId, { method: "DELETE", headers: authHeaders(token) })
    fetchAll(token)
  }

  const wr = perf?.win_rate ? (perf.win_rate * 100).toFixed(1) + "%" : "-"
  const np = perf?.net_profit ? "$" + perf.net_profit.toFixed(0) : "-"

  const statCards = [
    { icon: Users, label: "Total Users", value: String(users.length), color: "text-blue-400", bg: "bg-blue-500/10" },
    { icon: Signal, label: "Total Signals", value: String(signals.length), color: "text-gold", bg: "bg-gold/10" },
    { icon: Activity, label: "Win Rate", value: wr, color: "text-profit", bg: "bg-profit/10" },
    { icon: DollarSign, label: "Net Profit", value: np, color: "text-profit", bg: "bg-profit/10" },
  ]

  if (loading) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center">
        <p className="text-slate-500">Loading admin panel...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-navy flex">
      <aside className="hidden lg:flex flex-col w-64 glass-strong border-r border-white/5 p-6">
        <Link href="/" className="flex items-center gap-2 mb-10">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-navy" />
          </div>
          <div>
            <span className="text-lg font-bold text-white">Puno<span className="gold-text">kawan</span></span>
            <span className="block text-[10px] text-slate-600">Admin Panel</span>
          </div>
        </Link>

        <nav className="space-y-2 flex-1">
          {[
            { icon: Users, t: "users" },
            { icon: Signal, t: "signals" },
            { icon: Server, t: "system" },
            { icon: Settings, t: "config" },
          ].map((item, i) => (
            <button
              key={i}
              onClick={() => setTab(item.t)}
              className={"flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition w-full text-left " +
                (tab === item.t ? "bg-gold/10 text-gold font-semibold" : "text-slate-400 hover:text-white hover:bg-white/5")}
            >
              <item.icon className="w-4 h-4" /> {item.t.charAt(0).toUpperCase() + item.t.slice(1)}
            </button>
          ))}
        </nav>

        <div className="border-t border-white/5 pt-4 space-y-2">
          <Link href="/dashboard" className="flex items-center gap-2 text-sm text-slate-400 hover:text-white px-3 py-2 rounded-lg transition">
            <Home className="w-4 h-4" /> Dashboard
          </Link>
          <button onClick={() => { localStorage.removeItem("token"); router.push("/login") }} className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 px-3 py-2 rounded-lg transition w-full">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>

      <main className="flex-1 p-4 lg:p-8 overflow-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
            <p className="text-sm text-slate-500">Punokawan by Markaz-Arshy</p>
          </div>
          <button onClick={() => fetchAll(token)} className="flex items-center gap-2 glass px-4 py-2 rounded-xl text-sm text-slate-300 hover:text-white transition">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {statCards.map((s, i) => (
            <div key={i} className="glass rounded-xl p-4 text-center">
              <div className={"w-10 h-10 rounded-lg " + s.bg + " flex items-center justify-center mx-auto mb-3"}>
                <s.icon className={"w-5 h-5 " + s.color} />
              </div>
              <div className={"text-xl font-extrabold font-mono " + s.color}>{s.value}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </div>

        {tab === "users" && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-white/5 flex justify-between items-center">
              <h2 className="text-lg font-bold text-white">User Management</h2>
              <span className="text-sm text-slate-500">{users.length} users</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-3 px-4 font-medium">Email</th>
                    <th className="text-left py-3 px-4 font-medium">Name</th>
                    <th className="text-left py-3 px-4 font-medium">Tier</th>
                    <th className="text-left py-3 px-4 font-medium">Role</th>
                    <th className="text-left py-3 px-4 font-medium">Trial Ends</th>
                    <th className="text-left py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u: any) => (
                    <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-4 text-white font-mono text-xs">{u.email}</td>
                      <td className="py-3 px-4 text-slate-400">{u.name || "-"}</td>
                      <td className="py-3 px-4">
                        <select value={u.subscription_tier || "trial"} onChange={function(e) { updateTier(u.id, e.target.value) }}
                          className="text-xs font-semibold px-2 py-1 rounded-full border-0 bg-slate-700 text-slate-300">
                          <option value="trial">Trial</option>
                          <option value="pro">Pro</option>
                          <option value="enterprise">Enterprise</option>
                          <option value="expired">Expired</option>
                        </select>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-xs px-2 py-1 rounded-full bg-slate-500/20 text-slate-400">{u.role || "user"}</span>
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-500">{(u.trial_ends_at || "").slice(0, 10)}</td>
                      <td className="py-3 px-4">
                        <button onClick={function() { deleteUser(u.id) }} className="text-red-400 hover:text-red-300 p-1">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr><td colSpan={6} className="text-center py-12 text-slate-600">No users found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === "signals" && (
          <div className="glass rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-white/5">
              <h2 className="text-lg font-bold text-white">Signal Log</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-3 px-3 font-medium">Time</th>
                    <th className="text-left py-3 px-3 font-medium">Dir</th>
                    <th className="text-left py-3 px-3 font-medium">Entry</th>
                    <th className="text-left py-3 px-3 font-medium">SL</th>
                    <th className="text-left py-3 px-3 font-medium">TP</th>
                    <th className="text-left py-3 px-3 font-medium">Score</th>
                    <th className="text-left py-3 px-3 font-medium">RR</th>
                    <th className="text-left py-3 px-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.length === 0 ? (
                    <tr><td colSpan={8} className="text-center py-12 text-slate-600">No signals yet</td></tr>
                  ) : signals.map(function(s: any) {
                    return (
                      <tr key={s.id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-2 px-3 text-xs text-slate-500">{(s.created_at || "").slice(0, 19)}</td>
                        <td className={"py-2 px-3 text-xs font-bold " + (s.direction === "BUY" ? "text-profit" : "text-loss")}>{s.direction}</td>
                        <td className="py-2 px-3 text-xs text-white font-mono">{s.entry ? s.entry.toFixed(2) : "-"}</td>
                        <td className="py-2 px-3 text-xs text-loss font-mono">{s.sl ? s.sl.toFixed(2) : "-"}</td>
                        <td className="py-2 px-3 text-xs text-profit font-mono">{s.tp ? s.tp.toFixed(2) : "-"}</td>
                        <td className="py-2 px-3 text-xs text-gold">{s.score}</td>
                        <td className="py-2 px-3 text-xs text-slate-400">{s.rr_ratio ? s.rr_ratio.toFixed(1) : "-"}</td>
                        <td className="py-2 px-3 text-xs"><span className="px-2 py-0.5 rounded-full text-[10px] bg-gold/20 text-gold">{s.status}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === "system" && (
          <div className="space-y-6">
            <div className="glass rounded-2xl p-6">
              <h2 className="text-lg font-bold text-white mb-4">System Health</h2>
              {system?.servers ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(system.servers).map(function([name, status]: any) {
                    return (
                      <div key={name} className="glass rounded-xl p-4 text-center">
                        <div className={"w-3 h-3 rounded-full mx-auto mb-2 " + (status === "online" ? "bg-profit animate-pulse" : "bg-loss")} />
                        <div className="text-sm font-medium text-white">{name}</div>
                        <div className="text-xs text-slate-500">{status}</div>
                      </div>
                    )
                  })}
                </div>
              ) : <p className="text-slate-500">No system data available</p>}
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="glass rounded-xl p-4">
                  <div className="text-xs text-slate-500">MT5 Status</div>
                  <div className="text-sm text-white mt-1">{system?.mt5 || "unknown"}</div>
                </div>
                <div className="glass rounded-xl p-4">
                  <div className="text-xs text-slate-500">Total Users</div>
                  <div className="text-sm text-white mt-1">{system?.stats?.total_users || 0}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "config" && (
          <div className="glass rounded-2xl p-6">
            <h2 className="text-lg font-bold text-white mb-4">Trading Style Configuration</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                ["Trading Style", "SCALPING"],
                ["Primary TF", "M1"],
                ["Min Score", "6"],
                ["Min SL", "3.0 (30 pips)"],
                ["Max SL", "7.0 (70 pips)"],
                ["Max TP", "15.0 (150 pips)"],
                ["Risk/Trade", "10%"],
                ["Daily DD", "15%"],
                ["Trailing Stop", "5.0 (50 pips)"],
                ["Lot Mode", "FIXED"],
                ["Sessions", "London, NY"],
                ["TP Mode", "DYNAMIC"],
              ].map(function(item, i) {
                return (
                  <div key={i} className="glass rounded-xl p-4">
                    <div className="text-xs text-slate-500 mb-1">{item[0]}</div>
                    <div className="text-sm font-mono text-white">{item[1]}</div>
                  </div>
                )
              })}
            </div>
            <p className="text-xs text-slate-600 mt-4">
              Edit via <code className="text-gold">D:\Punokawan V2\.env</code>
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
