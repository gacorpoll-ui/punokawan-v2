import Navbar from "@/components/landing/Navbar"
import Hero from "@/components/landing/Hero"
import Features from "@/components/landing/Features"
import Performance from "@/components/landing/Performance"
import Pricing from "@/components/landing/Pricing"
import FAQ from "@/components/landing/FAQ"
import Footer from "@/components/landing/Footer"

export default function LandingPage() {
  return (
    <main>
      <Navbar />
      <Hero />
      <Features />
      <Performance />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  )
}
