import Pricing from "@/components/landing/Pricing"
import Navbar from "@/components/landing/Navbar"
import Footer from "@/components/landing/Footer"

export default function PricingPage() {
  return (
    <main>
      <Navbar />
      <div className="pt-24">
        <Pricing />
      </div>
      <Footer />
    </main>
  )
}
