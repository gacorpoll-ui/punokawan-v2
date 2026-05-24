"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Menu, X, TrendingUp } from "lucide-react"

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", onScroll)
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        scrolled ? "glass-strong py-3" : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-navy" />
          </div>
          <span className="text-xl font-bold text-white">
            Puno<span className="gold-text">kawan</span>
          </span>
          <span className="hidden sm:inline text-[10px] text-slate-600 ml-1.5 -mt-1">by Markaz-Arshy</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <Link href="#features" className="text-sm text-slate-300 hover:text-gold transition">Features</Link>
          <Link href="#performance" className="text-sm text-slate-300 hover:text-gold transition">Performance</Link>
          <Link href="#pricing" className="text-sm text-slate-300 hover:text-gold transition">Pricing</Link>
          <Link href="#faq" className="text-sm text-slate-300 hover:text-gold transition">FAQ</Link>
          <Link
            href="/login"
            className="text-sm text-slate-300 hover:text-white transition px-4 py-2 rounded-lg border border-slate-700 hover:border-gold/50"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="text-sm font-semibold text-navy bg-gold hover:bg-gold/90 px-5 py-2.5 rounded-lg transition-all hover:scale-105 gold-glow"
          >
            Start Free Trial
          </Link>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-white" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass-strong border-t border-white/5 px-4 py-4 space-y-3">
          <Link href="#features" className="block text-slate-300 py-2" onClick={() => setMobileOpen(false)}>Features</Link>
          <Link href="#performance" className="block text-slate-300 py-2" onClick={() => setMobileOpen(false)}>Performance</Link>
          <Link href="#pricing" className="block text-slate-300 py-2" onClick={() => setMobileOpen(false)}>Pricing</Link>
          <Link href="/register" className="block w-full text-center font-semibold text-navy bg-gold py-3 rounded-lg">Start Free Trial</Link>
        </div>
      )}
    </nav>
  )
}
