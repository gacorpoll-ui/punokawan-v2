"use client"

import Link from "next/link"
import { useState } from "react"
import { TrendingUp, Mail, Lock, User, Eye, EyeOff, Check } from "lucide-react"

export default function RegisterPage() {
  const [showPw, setShowPw] = useState(false)

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy p-4">
      <div className="absolute inset-0 bg-grid opacity-30" />

      <div className="relative z-10 w-full max-w-md">
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-navy" />
          </div>
          <span className="text-2xl font-bold text-white">
            Puno<span className="gold-text">kawan</span>
          </span>
        </Link>

        <div className="glass-strong rounded-2xl p-8">
          <div className="inline-flex items-center gap-2 bg-gold/10 text-gold text-xs font-semibold px-3 py-1 rounded-full mb-4">
            <Check className="w-3 h-3" /> 14-day free trial included
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Create your account</h1>
          <p className="text-slate-400 text-sm mb-6">Start your 14-day free trial. No credit card required.</p>

          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1.5">Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                <input type="text" className="w-full bg-navy border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-600 focus:border-gold/50 focus:outline-none transition" placeholder="John Doe" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                <input type="email" className="w-full bg-navy border border-slate-700 rounded-xl py-3 pl-10 pr-4 text-white placeholder-slate-600 focus:border-gold/50 focus:outline-none transition" placeholder="you@email.com" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                <input type={showPw ? "text" : "password"} className="w-full bg-navy border border-slate-700 rounded-xl py-3 pl-10 pr-12 text-white placeholder-slate-600 focus:border-gold/50 focus:outline-none transition" placeholder="Min. 6 characters" />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" className="w-full bg-gold hover:bg-gold/90 text-navy font-bold py-3 rounded-xl transition-all hover:scale-[1.02] gold-glow">
              Start Free Trial
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-gold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
