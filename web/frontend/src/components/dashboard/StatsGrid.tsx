"use client"

import { TrendingUp, Target, Activity, Shield, DollarSign, BarChart3 } from "lucide-react"

interface StatsProps {
  performance: {
    total_trades: number
    win_rate: number
    profit_factor: number
    sharpe_ratio: number
    net_profit: number
    gross_profit: number
  }
}

export default function StatsGrid({ performance: p }: StatsProps) {
  const stats = [
    { icon: TrendingUp, label: "Win Rate", value: `${(p.win_rate * 100).toFixed(1)}%`, color: "text-profit", bg: "bg-profit/10" },
    { icon: Target, label: "Profit Factor", value: p.profit_factor.toFixed(2), color: "text-blue-400", bg: "bg-blue-500/10" },
    { icon: Activity, label: "Sharpe Ratio", value: p.sharpe_ratio.toFixed(2), color: "text-gold", bg: "bg-gold/10" },
    { icon: DollarSign, label: "Net Profit", value: `$${p.net_profit.toFixed(0)}`, color: "text-profit", bg: "bg-profit/10" },
    { icon: BarChart3, label: "Total Trades", value: String(p.total_trades), color: "text-white", bg: "bg-slate-500/10" },
    { icon: Shield, label: "Gross Profit", value: `$${p.gross_profit.toFixed(0)}`, color: "text-profit", bg: "bg-profit/10" },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {stats.map((s, i) => (
        <div key={i} className="glass rounded-xl p-4 text-center hover:border-gold/20 transition">
          <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center mx-auto mb-3`}>
            <s.icon className={`w-5 h-5 ${s.color}`} />
          </div>
          <div className={`text-xl font-extrabold font-mono ${s.color} mb-0.5`}>{s.value}</div>
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">{s.label}</div>
        </div>
      ))}
    </div>
  )
}
