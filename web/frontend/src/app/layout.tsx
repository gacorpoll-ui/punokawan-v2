import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Punokawan by Markaz-Arshy — AI Gold Trading Signals",
  description:
    "Professional XAUUSD trading signals powered by AI. 14-day free trial. Real-time SMC analysis, 8-dimension confluence scoring, consistent profits. Built by Markaz-Arshy.",
  keywords: "XAUUSD, gold trading, AI signals, forex, trading bot, SMC, smart money concepts, Markaz-Arshy, Punokawan",
  openGraph: {
    title: "Punokawan by Markaz-Arshy — AI Gold Trading Signals",
    description: "Professional XAUUSD trading signals powered by AI. Start your 14-day free trial. Built by Markaz-Arshy.",
    type: "website",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-navy antialiased">{children}</body>
    </html>
  )
}
