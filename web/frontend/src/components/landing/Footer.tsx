import Link from "next/link"
import { TrendingUp } from "lucide-react"

export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-navy" />
              </div>
              <span className="text-lg font-bold text-white">
                Puno<span className="gold-text">kawan</span>
              </span>
              <span className="text-xs text-slate-600 ml-1">by Markaz-Arshy</span>
            </Link>
            <p className="text-sm text-slate-500 leading-relaxed">
              AI-powered XAUUSD trading signals. Built for traders who demand precision. &copy; Markaz-Arshy.</p>
          </div>

          {[
            { title: "Product", links: ["Features", "Performance", "Pricing", "FAQ"] },
            { title: "Company", links: ["About", "Contact", "Privacy Policy", "Terms of Service"] },
            { title: "Connect", links: ["Telegram", "Discord", "Twitter", "Email"] },
          ].map((col, i) => (
            <div key={i}>
              <h4 className="text-white font-semibold mb-4">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link, j) => (
                  <li key={j}>
                    <a href="#" className="text-sm text-slate-500 hover:text-gold transition">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-white/5 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-600">
            &copy; {new Date().getFullYear()} Punokawan by Markaz-Arshy. All rights reserved.
          </p>
          <p className="text-xs text-slate-600">
            Trading forex/commodities involves substantial risk of loss. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </footer>
  )
}
