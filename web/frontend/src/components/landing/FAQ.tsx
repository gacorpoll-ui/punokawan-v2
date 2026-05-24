"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { motion } from "framer-motion"

const faqs = [
  {
    q: "How does the AI generate trading signals?",
    a: "Our system analyzes XAUUSD across 4 timeframes using Smart Money Concepts (Order Blocks, FVGs, Liquidity Sweeps), 8 technical indicators, and candlestick patterns. Each setup receives a confluence score from 0-10. Only setups scoring 6+ are approved, after passing 11 deterministic risk checks.",
  },
  {
    q: "What brokers are supported?",
    a: "Any MetaTrader 5 (MT5) broker. Tested and working with Exness, IC Markets, and other major brokers. Both cent accounts and standard accounts are supported with automatic symbol detection.",
  },
  {
    q: "Can I auto-copy trades to my MT5 account?",
    a: "Yes — Enterprise plan includes MT5 auto-copy trading. The system writes trade directives that your MT5 bridge executes automatically. Pro users can use the API to build their own integration.",
  },
  {
    q: "What happens after the 14-day trial?",
    a: "After 14 days, you'll need to subscribe to continue receiving real-time signals. We'll send you a reminder 3 days before your trial ends. No automatic charges — you choose when to upgrade.",
  },
  {
    q: "How are signals delivered?",
    a: "Real-time via WebSocket to your dashboard. Each signal includes: direction, entry price, stop loss, take profit, lot size, confluence score, scoring breakdown, and AI reasoning.",
  },
  {
    q: "Is there a money-back guarantee?",
    a: "Yes. If you're not satisfied within 7 days of your paid subscription, we'll refund your payment. No questions asked.",
  },
]

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null)

  return (
    <section id="faq" className="py-24 relative">
      <div className="absolute inset-0 bg-grid opacity-30" />

      <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-gold text-sm font-semibold tracking-widest uppercase">FAQ</span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">
            Frequently Asked{" "}
            <span className="gold-text">Questions</span>
          </h2>
        </motion.div>

        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="glass rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-4 text-left"
              >
                <span className="text-white font-medium pr-4">{faq.q}</span>
                <ChevronDown
                  className={`w-5 h-5 text-slate-400 shrink-0 transition-transform ${
                    open === i ? "rotate-180" : ""
                  }`}
                />
              </button>
              {open === i && (
                <div className="px-6 pb-4 text-sm text-slate-400 leading-relaxed">{faq.a}</div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
