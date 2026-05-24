"use client"

import { TrendingUp, TrendingDown, Target, Shield, Zap, Clock } from "lucide-react"

interface SignalProps {
  direction: string
  entry: number
  sl: number
  tp: number
  lot_size: number
  score: number
  rr_ratio: number
  session: string
  tp_source: string
  confluence?: string
  created_at?: string
}

export default function SignalCard({ signal }: { signal: SignalProps }) {
  const isBuy = signal.direction === "BUY"
  const isNoTrade = signal.direction === "NO_TRADE" || signal.score === 0

  if (isNoTrade) {
    return (
      <div className="glass rounded-2xl p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-slate-700/50 flex items-center justify-center mx-auto mb-4">
          <Clock className="w-8 h-8 text-slate-500" />
        </div>
        <h2 className="text-xl font-bold text-slate-400 mb-2">Waiting for Signal</h2>
        <p className="text-sm text-slate-600">
          No high-confluence setup detected. System monitoring markets...
        </p>
      </div>
    )
  }

  return (
    <div className={`relative rounded-2xl p-8 overflow-hidden ${
      isBuy ? "glass profit-glow border-green-500/20" : "glass border-red-500/20"
    }`}>
      {/* Score badge */}
      <div className="absolute top-4 right-4">
        <div className={`text-xs font-bold px-3 py-1.5 rounded-full ${
          signal.score >= 7 ? "bg-profit/20 text-profit" :
          signal.score >= 5 ? "bg-gold/20 text-gold" :
          "bg-slate-700/50 text-slate-400"
        }`}>
          Score: {signal.score}/10
        </div>
      </div>

      {/* Direction */}
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
          isBuy ? "bg-profit/10" : "bg-loss/10"
        }`}>
          {isBuy ? (
            <TrendingUp className="w-6 h-6 text-profit" />
          ) : (
            <TrendingDown className="w-6 h-6 text-loss" />
          )}
        </div>
        <div>
          <div className={`text-2xl font-extrabold ${isBuy ? "text-profit" : "text-loss"}`}>
            {signal.direction}
          </div>
          <div className="text-xs text-slate-500">
            R:R 1:{signal.rr_ratio?.toFixed(1)} &middot; TP: [{signal.tp_source}]
          </div>
        </div>
      </div>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Entry", value: signal.entry?.toFixed(2), icon: Target, color: "text-white" },
          { label: "Stop Loss", value: signal.sl?.toFixed(2), icon: Shield, color: "text-loss" },
          { label: "Take Profit", value: signal.tp?.toFixed(2), icon: Zap, color: "text-profit" },
        ].map((item, i) => (
          <div key={i} className="text-center">
            <item.icon className={`w-4 h-4 ${item.color} mx-auto mb-1`} />
            <div className={`text-lg font-mono font-bold ${item.color}`}>{item.value}</div>
            <div className="text-[10px] text-slate-600 uppercase tracking-wider">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Bottom info */}
      <div className="flex items-center justify-between text-xs text-slate-600 border-t border-white/5 pt-4">
        <span>Lot: {signal.lot_size}</span>
        <span>{signal.session}</span>
        <span>{signal.created_at ? new Date(signal.created_at).toLocaleTimeString() : ""}</span>
      </div>
    </div>
  )
}
