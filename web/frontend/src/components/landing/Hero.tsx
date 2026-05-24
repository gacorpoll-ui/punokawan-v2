"use client"

import Link from "next/link"
import { ArrowRight, TrendingUp, Shield, Zap, BarChart3 } from "lucide-react"
import { motion } from "framer-motion"
import { useEffect, useState } from "react"

export default function Hero() {
  const [price, setPrice] = useState("4,507.82")

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      {/* Background effects */}
      <div className="absolute inset-0 bg-grid" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-gold/5 rounded-full blur-[120px]" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-[120px]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-br from-gold/3 via-transparent to-blue-500/3 rounded-full blur-[100px]" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 text-center py-20">
        {/* Live price ticker */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-3 glass px-5 py-2.5 rounded-full mb-8"
        >
          <div className="w-2 h-2 rounded-full bg-profit animate-pulse" />
          <span className="text-sm text-slate-400">XAUUSD</span>
          <span className="text-lg font-mono font-bold text-white">${price}</span>
          <span className="text-xs text-profit font-mono">+0.12%</span>
        </motion.div>

        {/* Main heading */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-5xl md:text-7xl font-extrabold tracking-tight leading-tight max-w-4xl mx-auto"
        >
          <span className="gold-text">AI-Powered</span>{" "}
          <span className="text-white">Gold Trading Signals</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed"
        >
          Autonomous XAUUSD scalping system with 8-dimension SMC confluence scoring.
          Real-time signals delivered to your dashboard. Start your 14-day free trial.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-10 flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 bg-gold hover:bg-gold/90 text-navy font-bold px-8 py-4 rounded-xl text-lg transition-all hover:scale-105 gold-glow"
          >
            Start 14-Day Free Trial
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            href="#performance"
            className="inline-flex items-center gap-2 glass text-white font-semibold px-8 py-4 rounded-xl text-lg hover:border-gold/30 transition-all"
          >
            <BarChart3 className="w-5 h-5" />
            View Performance
          </Link>
        </motion.div>

        {/* Trust badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto"
        >
          {[
            { icon: TrendingUp, label: "Win Rate", value: "68%" },
            { icon: Shield, label: "Max Drawdown", value: "<15%" },
            { icon: Zap, label: "Signal Delay", value: "<1 sec" },
            { icon: BarChart3, label: "Profit Factor", value: "1.8" },
          ].map((item, i) => (
            <div key={i} className="glass rounded-xl p-4 text-center">
              <item.icon className="w-5 h-5 text-gold mx-auto mb-2" />
              <div className="text-xs text-slate-500 mb-1">{item.label}</div>
              <div className="text-lg font-bold text-white">{item.value}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
