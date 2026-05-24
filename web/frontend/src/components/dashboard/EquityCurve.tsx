"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts"

interface EquityProps {
  data: { month: string; pnl: number }[]
}

export default function EquityCurve({ data }: EquityProps) {
  if (!data || data.length === 0) {
    return (
      <div className="glass rounded-2xl p-8 text-center">
        <p className="text-slate-500">No performance data yet. Start trading to see your equity curve.</p>
      </div>
    )
  }

  // Build cumulative curve
  let cum = 0
  const chartData = data.map((d) => {
    cum += d.pnl
    return { ...d, equity: Math.round(cum) }
  })

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-white">Equity Curve</h3>
          <p className="text-xs text-slate-500">Monthly cumulative P&L</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-profit">
          <div className="w-2 h-2 rounded-full bg-profit animate-pulse" />
          Live
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00c853" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#00c853" stopOpacity="0" />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1f35" />
            <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{
                background: "#111827",
                border: "1px solid #252a45",
                borderRadius: "12px",
                color: "#e2e8f0",
              }}
            />
            <Area type="monotone" dataKey="equity" stroke="#00c853" strokeWidth={2} fill="url(#equityFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
