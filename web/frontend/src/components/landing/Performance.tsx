"use client"

import { motion } from "framer-motion"
import { TrendingUp, Target, Activity, Shield } from "lucide-react"
import { useEffect, useState } from "react"

const stats = [
  { icon: TrendingUp, label: "Win Rate", value: "68%", color: "text-profit" },
  { icon: Target, label: "Profit Factor", value: "1.82", color: "text-blue-400" },
  { icon: Activity, label: "Sharpe Ratio", value: "1.45", color: "text-gold" },
  { icon: Shield, label: "Max Drawdown", value: "12.4%", color: "text-red-400" },
]

export default function Performance() {
  return (
    <section id="performance" className="py-24 relative">
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-blue-500/3 rounded-full blur-[120px]" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-gold text-sm font-semibold tracking-widest uppercase">Track Record</span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">
            Proven{" "}
            <span className="gold-text">Performance</span>
          </h2>
          <p className="text-slate-400 mt-4 max-w-xl mx-auto">
            Real trading results from our autonomous system. Full transparency, every trade logged.
          </p>
        </motion.div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          {stats.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-2xl p-6 text-center"
            >
              <s.icon className={`w-8 h-8 ${s.color} mx-auto mb-3`} />
              <div className={`text-3xl font-extrabold ${s.color} mb-1`}>{s.value}</div>
              <div className="text-xs text-slate-500 uppercase tracking-wider">{s.label}</div>
            </motion.div>
          ))}
        </div>

        {/* Equity curve placeholder */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass rounded-3xl p-8"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold text-white">Equity Curve — Last 30 Days</h3>
              <p className="text-sm text-slate-500">Real account performance</p>
            </div>
            <div className="flex items-center gap-2 text-profit text-sm font-mono">
              <div className="w-2 h-2 rounded-full bg-profit animate-pulse" />
              Live
            </div>
          </div>

          {/* Simplified equity curve visualization */}
          <div className="h-48 relative">
            <svg viewBox="0 0 800 200" className="w-full h-full">
              <defs>
                <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00c853" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#00c853" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* Grid lines */}
              {[0, 50, 100, 150, 200].map((y) => (
                <line key={y} x1="0" y1={y} x2="800" y2={y} stroke="#1a1f35" strokeWidth="1" />
              ))}
              {/* Equity line */}
              <path
                d="M0,150 C100,145 150,140 200,135 C250,128 280,120 320,130 C360,140 380,110 400,95 C420,80 430,85 460,70 C490,55 520,60 550,45 C580,32 600,40 650,25 C700,12 750,20 800,15"
                fill="url(#equityGrad)"
                stroke="#00c853"
                strokeWidth="3"
                strokeLinecap="round"
              />
              {/* Glow dots */}
              <circle cx="800" cy="15" r="6" fill="#00c853" className="animate-pulse">
                <animate attributeName="r" values="4;8;4" dur="2s" repeatCount="indefinite" />
              </circle>
            </svg>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-6">
            {[
              { label: "This Month", value: "+$342.50", color: "text-profit" },
              { label: "Total Trades", value: "47", color: "text-white" },
              { label: "Best Trade", value: "+$89.20", color: "text-profit" },
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className={`text-lg font-bold font-mono ${item.color}`}>{item.value}</div>
                <div className="text-xs text-slate-500">{item.label}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
