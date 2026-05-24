"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { TrendingUp, RefreshCw, Trash2 } from "lucide-react"

export default function AdminDashboard() {
  const router = useRouter()
  const [users, setUsers] = useState<any[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [system, setSystem] = useState<any>(null)
  const [perf, setPerf] = useState<any>(null)
  const [tab, setTab] = useState("users")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    const t = window.localStorage.getItem("token") || ""
    if (!t) { router.push("/login"); return }
    loadData(t)
  }, [])

  function loadData(t: string) {
    const h = { Authorization: "Bearer " + t, "Content-Type": "application/json" }
    Promise.all([
      fetch("/api/admin/users", { headers: h }),
      fetch("/api/admin/signals?limit=30", { headers: h }),
      fetch("/api/admin/system", { headers: h }),
      fetch("/api/admin/performance", { headers: h }),
    ]).then(function ([u, s, y, p]) {
      if (u.status === 403) { router.push("/login"); return }
      u.json().then(function (d) { setUsers(d.users || []) }).catch(function () {})
      s.json().then(function (d) { setSignals(d.signals || []) }).catch(function () {})
      y.json().then(function (d) { setSystem(d) }).catch(function () {})
      p.json().then(function (d) { setPerf(d) }).catch(function () {})
      setLoading(false)
    }).catch(function (e: any) {
      setError(e.message || "Network error")
      setLoading(false)
    })
  }

  function updateTier(uid: string, tier: string) {
    const t = window.localStorage.getItem("token") || ""
    fetch("/api/admin/users/" + uid + "/subscription", {
      method: "PUT",
      headers: { Authorization: "Bearer " + t, "Content-Type": "application/json" },
      body: JSON.stringify({ tier }),
    }).then(function () { loadData(t) })
  }

  function deleteUser(uid: string) {
    if (!confirm("Delete user?")) return
    const t = window.localStorage.getItem("token") || ""
    fetch("/api/admin/users/" + uid, { method: "DELETE", headers: { Authorization: "Bearer " + t } })
      .then(function () { loadData(t) })
  }

  return (
    <div style={{ background: "#090d1a", minHeight: "100vh", display: "flex", fontFamily: "Inter, sans-serif" }}>
      <div style={{ width: 260, background: "#111827", borderRight: "1px solid #1f2937", padding: 24 }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 40, textDecoration: "none" }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: "#fff" }}>Punokawan</span>
          <span style={{ fontSize: 11, color: "#666" }}>Admin</span>
        </Link>
        {["users","signals","system","config"].map(function (t) {
          return (
            <button
              key={t}
              onClick={function () { setTab(t) }}
              style={{
                display: "block", width: "100%", textAlign: "left", padding: "10px 16px",
                borderRadius: 10, marginBottom: 4, border: "none", cursor: "pointer", fontSize: 14,
                background: tab === t ? "rgba(240,185,11,0.1)" : "transparent",
                color: tab === t ? "#f0b90b" : "#94a3b8",
                fontWeight: tab === t ? 600 : 400,
              }}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          )
        })}
        <div style={{ borderTop: "1px solid #1f2937", marginTop: 20, paddingTop: 16 }}>
          <Link href="/dashboard" style={{ color: "#94a3b8", textDecoration: "none", fontSize: 13, display: "block", padding: "6px 0" }}>Dashboard</Link>
          <button
            onClick={function () { window.localStorage.removeItem("token"); router.push("/login") }}
            style={{ color: "#f87171", background: "none", border: "none", cursor: "pointer", fontSize: 13, padding: "6px 0" }}
          >Logout</button>
        </div>
      </div>

      <div style={{ flex: 1, padding: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 32 }}>
          <div>
            <h1 style={{ color: "#fff", fontSize: 24, fontWeight: 700, margin: 0 }}>Admin Dashboard</h1>
            <p style={{ color: "#64748b", fontSize: 13, margin: "4px 0 0" }}>Punokawan by Markaz-Arshy</p>
          </div>
          <button onClick={function () { loadData(window.localStorage.getItem("token") || "") }}
            style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 10, padding: "8px 16px", color: "#e2e8f0", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
          {[
            ["Total Users", users.length],
            ["Total Signals", signals.length],
            ["Win Rate", perf ? (perf.win_rate * 100).toFixed(1) + "%" : "-"],
            ["Net Profit", perf ? "$" + perf.net_profit.toFixed(0) : "-"],
          ].map(function (s, i) {
            return (
              <div key={i} style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 12, padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{s[1]}</div>
                <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", marginTop: 4 }}>{s[0]}</div>
              </div>
            )
          })}
        </div>

        {tab === "users" ? (
          <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ padding: "16px 24px", borderBottom: "1px solid #1f2937" }}>
              <h2 style={{ color: "#fff", fontSize: 16, fontWeight: 600, margin: 0 }}>Users ({users.length})</h2>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1f2937" }}>
                  {["Email", "Name", "Tier", "Role", "Trial Ends", "Actions"].map(function (h) {
                    return <th key={h} style={{ textAlign: "left", padding: "10px 16px", color: "#64748b", fontSize: 12, fontWeight: 500 }}>{h}</th>
                  })}
                </tr>
              </thead>
              <tbody>
                {users.map(function (u: any) {
                  return (
                    <tr key={u.id} style={{ borderBottom: "1px solid #1f2937" }}>
                      <td style={{ padding: "10px 16px", color: "#fff", fontSize: 12, fontFamily: "monospace" }}>{u.email}</td>
                      <td style={{ padding: "10px 16px", color: "#94a3b8", fontSize: 13 }}>{u.name || "-"}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <select value={u.subscription_tier || "trial"} onChange={function (e) { updateTier(u.id, e.target.value) }}
                          style={{ background: "#1e293b", color: "#f0b90b", border: "none", borderRadius: 6, padding: "4px 8px", fontSize: 11, fontWeight: 600 }}>
                          <option value="trial">Trial</option>
                          <option value="pro">Pro</option>
                          <option value="enterprise">Enterprise</option>
                          <option value="expired">Expired</option>
                        </select>
                      </td>
                      <td style={{ padding: "10px 16px" }}>
                        <span style={{ background: u.role === "admin" ? "rgba(239,68,68,0.2)" : "rgba(100,116,139,0.2)", color: u.role === "admin" ? "#f87171" : "#94a3b8", padding: "2px 8px", borderRadius: 100, fontSize: 10 }}>{u.role || "user"}</span>
                      </td>
                      <td style={{ padding: "10px 16px", color: "#64748b", fontSize: 11 }}>{(u.trial_ends_at || "").slice(0, 10)}</td>
                      <td style={{ padding: "10px 16px" }}>
                        <button onClick={function () { deleteUser(u.id) }} style={{ background: "none", border: "none", cursor: "pointer", color: "#f87171" }}><Trash2 size={14} /></button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : tab === "signals" ? (
          <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 12, padding: 24 }}>
            <h2 style={{ color: "#fff", fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>Signal Log</h2>
            {signals.length === 0 ? <p style={{ color: "#64748b", textAlign: "center", padding: 40 }}>No signals yet.</p> : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #1f2937" }}>
                    {["Time","Dir","Entry","SL","TP","Score","RR","Status"].map(function (h) {
                      return <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "#64748b", fontSize: 12 }}>{h}</th>
                    })}
                  </tr>
                </thead>
                <tbody>
                  {signals.map(function (s: any) {
                    return (
                      <tr key={s.id} style={{ borderBottom: "1px solid #1f2937" }}>
                        <td style={{ padding: "8px 12px", color: "#64748b", fontSize: 11 }}>{(s.created_at || "").slice(0, 19)}</td>
                        <td style={{ padding: "8px 12px", fontSize: 12, fontWeight: 600, color: s.direction === "BUY" ? "#00c853" : "#ff1744" }}>{s.direction}</td>
                        <td style={{ padding: "8px 12px", color: "#fff", fontSize: 12, fontFamily: "monospace" }}>{s.entry?.toFixed(2)}</td>
                        <td style={{ padding: "8px 12px", color: "#ff1744", fontSize: 12, fontFamily: "monospace" }}>{s.sl?.toFixed(2)}</td>
                        <td style={{ padding: "8px 12px", color: "#00c853", fontSize: 12, fontFamily: "monospace" }}>{s.tp?.toFixed(2)}</td>
                        <td style={{ padding: "8px 12px", color: "#f0b90b", fontSize: 12 }}>{s.score}</td>
                        <td style={{ padding: "8px 12px", color: "#94a3b8", fontSize: 12 }}>{s.rr_ratio?.toFixed(1)}</td>
                        <td style={{ padding: "8px 12px" }}><span style={{ background: "rgba(240,185,11,0.2)", color: "#f0b90b", padding: "2px 6px", borderRadius: 100, fontSize: 10 }}>{s.status}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        ) : tab === "system" ? (
          <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 12, padding: 24 }}>
            <h2 style={{ color: "#fff", fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>System Health</h2>
            {system?.servers ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                {Object.entries(system.servers).map(function ([name, status]: any) {
                  return (
                    <div key={name} style={{ background: "#0f1425", borderRadius: 12, padding: 16, textAlign: "center" }}>
                      <div style={{ width: 10, height: 10, borderRadius: "50%", background: status === "online" ? "#00c853" : "#ff1744", margin: "0 auto 8px" }} />
                      <div style={{ color: "#fff", fontSize: 13 }}>{name}</div>
                      <div style={{ color: "#64748b", fontSize: 11 }}>{status}</div>
                    </div>
                  )
                })}
              </div>
            ) : <p style={{ color: "#64748b" }}>No system data</p>}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ background: "#0f1425", borderRadius: 12, padding: 16 }}>
                <div style={{ color: "#64748b", fontSize: 11 }}>MT5 Status</div>
                <div style={{ color: "#fff", fontSize: 14, marginTop: 4 }}>{system?.mt5 || "unknown"}</div>
              </div>
              <div style={{ background: "#0f1425", borderRadius: 12, padding: 16 }}>
                <div style={{ color: "#64748b", fontSize: 11 }}>Total Users</div>
                <div style={{ color: "#fff", fontSize: 14, marginTop: 4 }}>{system?.stats?.total_users || 0}</div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 12, padding: 24 }}>
            <h2 style={{ color: "#fff", fontSize: 16, fontWeight: 600, margin: "0 0 16px" }}>Trading Configuration</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              {[
                ["Trading Style", "SCALPING"], ["Primary TF", "M1"], ["Min Score", "6"],
                ["Min SL", "3.0 (30 pips)"], ["Max SL", "7.0 (70 pips)"], ["Max TP", "15.0 (150 pips)"],
                ["Risk/Trade", "10%"], ["Daily DD", "15%"], ["Trail Stop", "5.0 (50 pips)"],
                ["Lot Mode", "FIXED"], ["Sessions", "London, NY"], ["TP Mode", "DYNAMIC"],
              ].map(function (item, i) {
                return (
                  <div key={i} style={{ background: "#0f1425", borderRadius: 10, padding: 14 }}>
                    <div style={{ color: "#64748b", fontSize: 11 }}>{item[0]}</div>
                    <div style={{ color: "#fff", fontSize: 13, fontFamily: "monospace", marginTop: 4 }}>{item[1]}</div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
