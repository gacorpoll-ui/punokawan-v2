"use client"

import { Brain, CandlestickChart, Shield, Database, Zap, Globe, BarChart3, Clock } from "lucide-react"
import { motion } from "framer-motion"

const features = [
  {
    icon: Brain,
    title: "8-Dimension AI Scoring",
    desc: "BOS, Order Blocks, Multi-TF alignment, Divergence, FVG magnet, Sweeps — AI evaluates every setup across 8 criteria.",
  },
  {
    icon: CandlestickChart,
    title: "Smart Money Concepts",
    desc: "Algorithmic SMC detection — Order Blocks, Fair Value Gaps, Liquidity Sweeps, CHoCH — no manual charting.",
  },
  {
    icon: Shield,
    title: "Risk Guardrail System",
    desc: "11 deterministic risk checks before every trade. Kill switch, drawdown limits, spread protection, news blackout.",
  },
  {
    icon: Database,
    title: "Self-Learning Memory",
    desc: "ChromaDB vector database remembers losing patterns. Blocks repeat mistakes with 80%+ similarity detection.",
  },
  {
    icon: Zap,
    title: "Real-Time Signals",
    desc: "WebSocket push to your dashboard. Signals include entry, SL, TP, score, confluence breakdown, and AI reasoning.",
  },
  {
    icon: Clock,
    title: "Multi-Timeframe Analysis",
    desc: "M1 to D1 analysis synchronized. Scalping, intraday, or swing — one system, three trading styles.",
  },
  {
    icon: Globe,
    title: "Broker Compatible",
    desc: "MT5 integration. Works with Exness, IC Markets, and any MT5 broker. Cent and standard accounts supported.",
  },
  {
    icon: BarChart3,
    title: "Performance Analytics",
    desc: "Win rate, profit factor, Sharpe ratio, equity curve, monthly breakdown. Full transparency on every trade.",
  },
]

export default function Features() {
  return (
    <section id="features" className="py-24 relative">
      <div className="absolute inset-0 bg-grid opacity-50" />
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-gold text-sm font-semibold tracking-widest uppercase">Features</span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">
            Everything You Need to{" "}
            <span className="gold-text">Trade Gold</span>
          </h2>
          <p className="text-slate-400 mt-4 max-w-xl mx-auto">
            Built by traders, for traders. Every feature designed to give you an edge in the XAUUSD market.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-2xl p-6 hover:border-gold/30 transition-all group"
            >
              <div className="w-12 h-12 rounded-xl bg-gold/10 flex items-center justify-center mb-4 group-hover:bg-gold/20 transition">
                <f.icon className="w-6 h-6 text-gold" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
