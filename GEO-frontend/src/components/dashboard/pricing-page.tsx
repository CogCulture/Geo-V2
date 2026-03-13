"use client";

import React, { useState, useEffect } from "react";
import { Check, ChevronDown, ChevronUp, Plus, Minus, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface PricingPageProps {
  onGetStarted: () => void;
  onClose?: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface FAQItem {
  q: string;
  a: string;
}

export function PricingPage({ onGetStarted, onClose }: PricingPageProps) {
  const router = useRouter();
  const { subscription, refreshUser } = useAuth();
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [loading, setLoading] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  // ── Removed Auto-skip: allowing users to view pricing even if subscribed ──

  const plans = [
    {
      name: "Lite Plan",
      description: "Perfect for Individuals",
      monthlyPrice: 29,
      yearlyPrice: 290,
      badge: "Most Affordable",
      features: [
        { text: "2 Projects", included: true },
        { text: "5 Prompts Per Project", included: true },
        { text: "5 Content Generation", included: true },
        { text: "72-Hour Refresh", included: true },
        { text: "Detailed Citation Data", included: true },
        { text: "2 Locations", included: true },
        { text: "Competitor Monitoring", included: true },
        { text: "Actionable AI Insights", included: true },
        { text: "AI Traffic Analytics", included: true },
        { text: "Human Support", included: true },
        { text: "No Extra Seats", included: false }
      ],
      cta: "Start 7-day trial",
      popular: false
    },
    {
      name: "Growth Plan",
      description: "Ideal for Advanced Users",
      monthlyPrice: 79,
      yearlyPrice: 790,
      badge: "Most Popular",
      features: [
        { text: "4 Projects", included: true },
        { text: "10 Prompts Per Project", included: true },
        { text: "15 Content Generation", included: true },
        { text: "Daily Refresh", included: true },
        { text: "Detailed Citation Data", included: true },
        { text: "5 Locations", included: true },
        { text: "Competitor Monitoring", included: true },
        { text: "Actionable AI Insights", included: true },
        { text: "AI Traffic Analytics", included: true },
        { text: "Human Support", included: true },
        { text: "2 Extra Seats", included: true }
      ],
      cta: "Start 7-day trial",
      popular: true
    },
    {
      name: "Custom Plan",
      description: "Built for Small Teams",
      monthlyPrice: 139,
      yearlyPrice: 1390,
      badge: "Best Value",
      features: [
        { text: "8 Projects", included: true },
        { text: "10 Prompts Per Project", included: true },
        { text: "32 Content Generation", included: true },
        { text: "Daily Refresh", included: true },
        { text: "Detailed Citation Data", included: true },
        { text: "10 Locations", included: true },
        { text: "Competitor Monitoring", included: true },
        { text: "Actionable AI Insights", included: true },
        { text: "AI Traffic Analytics", included: true },
        { text: "Priority Human Support", included: true },
        { text: "5 Extra Seats", included: true }
      ],
      cta: "Start 7-day trial",
      popular: false
    }
  ];

  const faqData: FAQItem[] = [
    { q: "What is Radarkit and how does it work?", a: "Radarkit is a Generative Engine Optimization (GEO) and AI search tracking tool that monitors how your brand appears across various AI assistants and provides actionable insights to improve visibility and performance." },
    { q: "Which AI platforms does Radarkit monitor?", a: "We monitor all major AI search engines and assistants including ChatGPT, Claude, Gemini, Perplexity, and Mistral, providing a comprehensive view of your brand's AI presence." },
    { q: "Do you offer free trial?", a: "Yes, we offer a 7-day free trial on all our plans so you can experience the full power of Radarkit before committing." },
    { q: "Can I track my competitors?", a: "Absolutely. Radarkit allows you to monitor competitor visibility alongside your own, giving you a clear picture of your industry's share of voice in AI results." }
  ];

  // Dynamically load Razorpay script
  React.useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleCheckout = async (planName: string) => {
    const userId = localStorage.getItem("userId");
    const userEmail = localStorage.getItem("userEmail") || "";

    // If not logged in, redirect to login flow
    if (!userId) {
      onGetStarted();
      return;
    }

    setLoading(planName);

    try {
      // ── 1. Create Razorpay order on backend (price calculated server-side) ──
      const response = await fetch(`${API_URL}/api/payments/razorpay/create-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          plan_name: planName,
          billing_cycle: billingCycle
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create payment order");
      }

      const orderData = await response.json();

      // ── 2. Open Razorpay Checkout widget ──────────────────────────────────
      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: "CogCulture",
        description: `Subscription for ${planName}`,
        order_id: orderData.order_id,
        handler: async function (razorpayResponse: any) {
          // ── 3. Verify payment signature on backend ─────────────────────
          try {
            const verifyRes = await fetch(`${API_URL}/api/payments/razorpay/verify-payment`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                razorpay_order_id: razorpayResponse.razorpay_order_id,
                razorpay_payment_id: razorpayResponse.razorpay_payment_id,
                razorpay_signature: razorpayResponse.razorpay_signature,
                user_id: userId,
                plan_name: planName,
                billing_cycle: billingCycle
              })
            });

            if (verifyRes.ok) {
              // ── 4. Force-sync subscription state from the server ───────
              await refreshUser();
              // ── 5. Redirect to dashboard after state settles ───────────
              setTimeout(() => {
                router.push("/dashboard");
              }, 300);
            } else {
              const errData = await verifyRes.json();
              alert(errData.detail || "Payment verification failed. Please contact support.");
            }
          } catch (err) {
            console.error("Verification error:", err);
            alert("An error occurred during payment verification.");
          }
        },
        prefill: {
          email: userEmail
        },
        theme: {
          color: "#000000"
        }
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();

    } catch (err: any) {
      console.error(err);
      alert(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-white text-black font-sans selection:bg-black selection:text-white pb-20">
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-gray-50 to-white -z-10" />

      {/* Nav Offset / Close Button */}
      <div className="max-w-7xl mx-auto px-6 py-12 flex justify-end">
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-full border border-gray-200 hover:bg-black hover:text-white transition-all duration-200"
          >
            <Plus className="rotate-45 h-6 w-6" />
          </button>
        )}
      </div>

      {/* Header Section */}
      <div className="max-w-4xl mx-auto text-center px-6 mb-16">
        <div className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 border border-gray-200 text-[10px] font-bold tracking-widest text-gray-500 uppercase mb-6">
          Pricing
        </div>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
          Our Pricing Is Simple
        </h1>
        <p className="text-lg text-gray-500 mb-8 max-w-2xl mx-auto">
          There is a package to fit every customer's needs and budget
        </p>

        <div className="flex flex-col items-center gap-4">
          <p className="text-sm font-medium text-gray-400">Work with any AI Assistants on all plans</p>
          <div className="flex flex-wrap justify-center items-center gap-8 opacity-40 grayscale pointer-events-none">
            {/* AI Assistant Icons Placeholder Similes */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 bg-black rounded-lg" />
              <span className="text-[10px] font-bold">ChatGPT</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 bg-black rounded-full" />
              <span className="text-[10px] font-bold">Claude</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-black rounded-full" />
              <span className="text-[10px] font-bold">Gemini</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 bg-gray-200 rounded-md" />
              <span className="text-[10px] font-bold">Perplexity</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border border-gray-300 rounded-sm" />
              <span className="text-[10px] font-bold">AI Studio</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 bg-gray-100 rounded-lg border border-gray-200" />
              <span className="text-[10px] font-bold">Mistral</span>
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Grid */}
      <div className="max-w-7xl mx-auto px-6 mb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan, idx) => (
            <div
              key={idx}
              className={`relative bg-white rounded-[2rem] border ${plan.popular ? 'border-gray-200 shadow-2xl' : 'border-gray-100'} p-10 flex flex-col transition-all duration-300 hover:scale-[1.02]`}
            >
              <div className="mb-8">
                <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
                <p className="text-sm text-gray-400 font-medium">{plan.description}</p>
              </div>

              <div className="mb-8">
                <div className="inline-flex px-4 py-1.5 rounded-full bg-gray-50 border border-gray-100 text-[10px] font-bold uppercase tracking-wider text-gray-700 mb-6">
                  {plan.badge}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-bold">${billingCycle === 'monthly' ? plan.monthlyPrice : plan.yearlyPrice / 10}.00</span>
                  <span className="text-gray-400 font-medium">/ Month</span>
                </div>
              </div>

              <Button
                onClick={() => handleCheckout(plan.name)}
                disabled={subscription?.is_active && subscription?.subscription_plan?.toLowerCase() === plan.name.toLowerCase()}
                className={`w-full py-6 rounded-2xl text-base font-bold transition-all mb-4 ${subscription?.is_active && subscription?.subscription_plan?.toLowerCase() === plan.name.toLowerCase()
                    ? 'bg-emerald-50 text-emerald-600 border border-emerald-100'
                    : 'bg-black text-white hover:bg-gray-800'
                  }`}
              >
                {subscription?.is_active && subscription?.subscription_plan?.toLowerCase() === plan.name.toLowerCase() ? "Current Plan" : plan.cta}
              </Button>
              <p className="text-center text-[11px] text-gray-400 font-medium mb-10 flex items-center justify-center gap-1.5">
                <Check className="h-3 w-3" /> Cancel Your Subscription Anytime
              </p>

              <div className="space-y-4">
                <p className="text-xs font-bold text-gray-900 uppercase tracking-widest mb-4">Features included:</p>
                {plan.features.map((feature, fIdx) => (
                  <div key={fIdx} className={`flex items-center gap-3 ${feature.included ? 'text-gray-600' : 'text-gray-300 line-through decoration-gray-200'}`}>
                    <div className={`p-0.5 rounded-full border ${feature.included ? 'border-gray-200 bg-gray-50' : 'border-gray-100 bg-transparent'}`}>
                      <Check className={`h-3 w-3 ${feature.included ? 'text-black' : 'text-gray-200'}`} />
                    </div>
                    <span className="text-[13px] font-medium">{feature.text}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Enterprise / Dedicated Section */}
      <div className="max-w-7xl mx-auto px-6 mb-32">
        <div className="bg-gray-50 rounded-[2.5rem] border border-gray-100 overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2">
            <div className="p-12 md:p-16 border-b md:border-b-0 md:border-r border-gray-100">
              <div className="inline-block px-3 py-1 rounded-full bg-white border border-gray-200 text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-6">
                Enterprise
              </div>
              <h3 className="text-2xl font-bold mb-6 max-w-md">
                Dedicated Manager to help you get the most out of Radarkit and your brand monitoring needs.
              </h3>
              <div className="flex items-baseline gap-1 mb-8">
                <span className="text-3xl font-bold">$449.00</span>
                <span className="text-gray-400 font-medium">/ Month</span>
              </div>
              <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-8">Annual commitment required</p>
              <Button className="bg-black text-white px-10 py-6 rounded-2xl font-bold hover:bg-gray-800 transition-all">
                Contact sales
              </Button>
            </div>
            <div className="p-12 md:p-16 bg-white/50">
              <div className="inline-block px-3 py-1 rounded-full bg-white border border-gray-200 text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-6">
                Key Perks
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-8">
                {[
                  "Dashboard Manager",
                  "GEO Strategy",
                  "API Access",
                  "Custom Branding",
                  "Custom Reports & KPIs",
                  "Priority Account Services"
                ].map((perk, pIdx) => (
                  <div key={pIdx} className="flex items-center gap-3">
                    <div className="p-1 rounded-full bg-gray-900">
                      <Check className="h-3 w-3 text-white" />
                    </div>
                    <span className="text-sm font-bold text-gray-700">{perk}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="max-w-3xl mx-auto px-6 mb-32">
        <div className="text-center mb-12">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-gray-50 border border-gray-100 text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-6">
            FAQ
          </div>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Quick answers</h2>
        </div>

        <div className="space-y-4">
          {faqData.map((faq, fIdx) => (
            <div key={fIdx} className="bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden">
              <button
                onClick={() => setOpenFaq(openFaq === fIdx ? null : fIdx)}
                className="w-full p-6 flex items-center justify-between text-left hover:bg-gray-100/50 transition-all"
              >
                <span className="font-bold text-gray-800">{faq.q}</span>
                {openFaq === fIdx ? <Minus className="h-4 w-4 text-gray-400" /> : <Plus className="h-4 w-4 text-gray-400" />}
              </button>
              {openFaq === fIdx && (
                <div className="p-6 pt-0 text-sm text-gray-500 leading-relaxed animate-in fade-in slide-in-from-top-2 duration-300">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Final Call to Action */}
      <div className="max-w-7xl mx-auto px-6 mb-32">
        <div className="bg-gray-50 rounded-[3rem] p-12 md:p-24 text-center border border-gray-100 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/50 rounded-full blur-3xl -mr-32 -mt-32" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/50 rounded-full blur-3xl -ml-32 -mb-32" />

          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-10 relative z-10">
            Find how LLM's talking about your Brand
          </h2>
          <Button
            onClick={onGetStarted}
            className="bg-black text-white px-10 py-7 rounded-2xl text-lg font-bold hover:bg-gray-800 transition-all shadow-xl shadow-gray-200 relative z-10"
          >
            Get started free
          </Button>
        </div>
      </div>

      {/* Extended Footer */}
      <footer className="max-w-7xl mx-auto px-6 border-t border-gray-100 pt-20">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-20">
          <div className="col-span-1 md:col-span-1">
            <h2 className="text-2xl font-black mb-6">CogCulture</h2>
            <p className="text-sm text-gray-400 font-medium leading-relaxed max-w-xs">
              Track your brand's visibility across Generative AI search engines and optimized your digital presence for the LLM era.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-sm uppercase tracking-widest text-gray-900 mb-6">Product</h4>
            <ul className="space-y-4">
              {['Features', 'Dashboard', 'Pricing', 'API Docs'].map(item => (
                <li key={item}><a href="#" className="text-sm text-gray-400 hover:text-black transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-sm uppercase tracking-widest text-gray-900 mb-6">Company</h4>
            <ul className="space-y-4">
              {['About Us', 'Contact', 'Privacy Policy', 'Terms of Service'].map(item => (
                <li key={item}><a href="#" className="text-sm text-gray-400 hover:text-black transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-sm uppercase tracking-widest text-gray-900 mb-6">Resources</h4>
            <ul className="space-y-4">
              {['Blog', 'Help Center', 'Community', 'Security'].map(item => (
                <li key={item}><a href="#" className="text-sm text-gray-400 hover:text-black transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="flex flex-col md:flex-row justify-between items-center py-10 border-t border-gray-50 gap-6">
          <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">
            Made with ♥ © 2026 CogCulture — All rights reserved.
          </p>
          <div className="flex gap-4">
            {['Twitter', 'LinkedIn', 'Github'].map(platform => (
              <a key={platform} href="#" className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center hover:bg-black group transition-all">
                <div className="w-4 h-4 bg-gray-300 rounded-sm group-hover:bg-white transition-colors" />
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
