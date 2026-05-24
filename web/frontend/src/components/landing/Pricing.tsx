"use client"

import Link from "next/link"
import { Check, Zap } from "lucide-react"
import { motion } from "framer-motion"

const plans = [
  {
    name: "Starter",
    price: "Free",
    period: "14 days",
    desc: "Try the full system risk-free.",
    features: [
      "Real-time signals (5-min delay)",
      "Dashboard access",
      "Basic performance stats",
      "Email support",
    ],
    cta: "Start Free Trial",
    href: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    desc: "Serious traders who want the edge.",
    features: [
      "Real-time signals (no delay)",
      "Full dashboard + analytics",
      "WebSocket live push",
      "AI reasoning on every signal",
      "Signal history (unlimited)",
      "Priority email support",
      "API access",
    ],
    cta: "Get Started",
    href: "/register?plan=pro",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$99",
    period: "/month",
    desc: "Professional traders & funds.",
    features: [
      "Everything in Pro",
      "Custom trading style config",
      "Dedicated signal channel",
      "MT5 auto-copy trading",
      "White-label option",
      "Phone support",
      "SLA guarantee",
    ],
    cta: "Contact Us",
    href: "mailto:markaz-arshy@punokawan.io",
    highlighted: false,
  },
]

export default function Pricing() {
  return (
    <section id="pricing" className="py-24 relative">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-gold/3 rounded-full blur-[150px]" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-gold text-sm font-semibold tracking-widest uppercase">Pricing</span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">
            Start Free,{" "}
            <span className="gold-text">Upgrade When Ready</span>
          </h2>
          <p className="text-slate-400 mt-4 max-w-xl mx-auto">
            14-day full-featured trial. No credit card required. Cancel anytime.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`relative rounded-2xl p-8 ${
                plan.highlighted
                  ? "glass-strong gold-glow border-gold/30 scale-[1.02]"
                  : "glass"
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gold text-navy text-xs font-bold px-4 py-1 rounded-full flex items-center gap-1">
                  <Zap className="w-3 h-3" /> MOST POPULAR
                </div>
              )}

              <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
              <p className="text-sm text-slate-500 mb-4">{plan.desc}</p>

              <div className="mb-6">
                <span className="text-4xl font-extrabold text-white">{plan.price}</span>
                <span className="text-slate-500 ml-1">{plan.period}</span>
              </div>

              <Link
                href={plan.href}
                className={`block w-full text-center font-semibold py-3 rounded-xl transition-all mb-6 ${
                  plan.highlighted
                    ? "bg-gold hover:bg-gold/90 text-navy"
                    : "glass border border-slate-700 text-white hover:border-gold/30"
                }`}
              >
                {plan.cta}
              </Link>

              <ul className="space-y-3">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-start gap-2 text-sm text-slate-400">
                    <Check className="w-4 h-4 text-profit mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
