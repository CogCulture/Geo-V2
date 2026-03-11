import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { ArrowRight, TrendingUp, Shield, HelpCircle, Repeat2, Zap } from "lucide-react";

interface LandingPageProps {
  onGetStarted: () => void;
}

// Array of AI models for the dynamic heading
const AI_MODELS = ["Perplexity", "Claude", "Google AI", "ChatGPT"];

// LOGO CONFIGURATION - FIXED PATHS
const LOGOS = [
  { name: "Perplexity", src: "/logos/perplexity.png" }, 
  { name: "Claude", src: "/logos/claude.png" },
  { name: "ChatGPT", src: "/logos/chatgpt.png" },
  { name: "Google", src: "/logos/google.png" },
  { name: "Googleai", src: "/logos/googleai.png" },
  { name: "Mistral", src: "/logos/mistral.png" },
  { name: "Deepseek", src: "/logos/deepseek.png" },
];

export function LandingPage({ onGetStarted }: LandingPageProps) {
  const [modelIndex, setModelIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setModelIndex((prevIndex) => (prevIndex + 1) % AI_MODELS.length);
    }, 1200); 

    return () => clearInterval(interval);
  }, []);

  const currentModel = AI_MODELS[modelIndex];

  return (
    <div className="flex-1 w-full flex flex-col items-center bg-white text-gray-900">
      
      {/* 1. Hero Section */}
      <section className="relative w-full max-w-6xl mx-auto py-24 lg:py-32 text-center overflow-visible">


  
        <div className="relative z-10 px-4">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tighter mb-8 leading-[1.1]">
            Get Organic Traffic From <br />
            <span className="inline-block mt-2 text-blue-600 transition-opacity duration-300">
                {currentModel}
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-600 max-w-3xl mx-auto mb-10 leading-relaxed">
            Get discovered and recommended by ChatGPT, Google AI, Claude, Perplexity, and other AI search engines.
          </p>

          <Button
            onClick={onGetStarted}
            size="lg"
            className="h-14 px-10 text-lg font-semibold bg-black hover:bg-gray-800 text-white transition-all shadow-xl shadow-gray-200 hover:shadow-2xl hover:shadow-gray-300 flex items-center justify-center gap-2 rounded-full mx-auto"
          >
            Get Started
            <ArrowRight className="h-5 w-5" />
          </Button>
        </div>
      </section>

      {/* NEW: Logo Animation Section */}
      <div className="w-full border-t border-b border-gray-100 bg-gray-50/50 py-10 overflow-hidden">
        <p className="text-center text-sm font-semibold text-gray-500 mb-6 uppercase tracking-wider">
          Optimized for all major AI Engines
        </p>
        <div className="relative w-full max-w-7xl mx-auto px-4 overflow-hidden mask-image-linear-gradient">
          <div className="flex w-max animate-scroll gap-16 items-center">
            {/* First Copy */}
            {LOGOS.map((logo, index) => (
              <div key={`logo-1-${index}`} className="flex items-center justify-center h-12 w-32 transition-all duration-300 hover:scale-110">
                <img 
                  src={logo.src} 
                  alt={logo.name} 
                  className="max-h-full max-w-full object-contain"
                  onError={(e) => {
                    console.error(`Failed to load: ${logo.src}`);
                    e.currentTarget.style.display = 'none';
                  }}
                />
              </div>
            ))}
            {/* Second Copy */}
            {LOGOS.map((logo, index) => (
              <div key={`logo-2-${index}`} className="flex items-center justify-center h-12 w-32 transition-all duration-300 hover:scale-110">
                <img 
                  src={logo.src} 
                  alt={logo.name} 
                  className="max-h-full max-w-full object-contain"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              </div>
            ))}
            {/* Third Copy */}
            {LOGOS.map((logo, index) => (
              <div key={`logo-3-${index}`} className="flex items-center justify-center h-12 w-32 transition-all duration-300 hover:scale-110">
                <img 
                  src={logo.src} 
                  alt={logo.name} 
                  className="max-h-full max-w-full object-contain"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="w-full h-px bg-gray-100 my-12 max-w-6xl mx-auto"></div>

      {/* 2. Why is GEO important? */}
      <section className="w-full max-w-7xl mx-auto py-12 px-4 text-center">
        <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-8">
          Why is GEO important?
        </h2>
        <p className="text-lg md:text-xl text-gray-600 max-w-4xl mx-auto mb-20 leading-relaxed">
          AI-powered search is reshaping how customers discover businesses. With over 60% of searches now processed by AI engines, traditional SEO alone isn't enough. GEO ensures your brand gets cited, recommended, and discovered in the new era of conversational search.
        </p>

        <div className="flex flex-col md:flex-row justify-center items-start gap-12 lg:gap-24">
          <div className="flex flex-col items-center max-w-[320px] p-2 mx-auto">
            <div className="bg-gray-50 p-6 rounded-2xl mb-6">
                <TrendingUp className="h-10 w-10 text-gray-700" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Increase AI Visibility</h3>
            <p className="text-base text-gray-600 leading-relaxed">
              Get cited and recommended by leading AI engines like ChatGPT, Claude, and Bard.
            </p>
          </div>

          <div className="flex flex-col items-center max-w-[320px] p-2 mx-auto">
            <div className="bg-gray-50 p-6 rounded-2xl mb-6">
                 <Repeat2 className="h-10 w-10 text-gray-700" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Drive Quality Traffic</h3>
            <p className="text-base text-gray-600 leading-relaxed">
              Capture high-intent customers using conversational AI search to find your business.
            </p>
          </div>

          <div className="flex flex-col items-center max-w-[320px] p-2 mx-auto">
             <div className="bg-gray-50 p-6 rounded-2xl mb-6">
                 <Shield className="h-10 w-10 text-gray-700" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Stay Ahead of Competition</h3>
            <p className="text-base text-gray-600 leading-relaxed">
              Be ready for the AI-first search revolution before your competitors catch up.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Why Choose GEO for GEO? (Dark Section) */}
      <div className="w-full bg-[#0B1221] mt-24 py-24">
        <section className="max-w-6xl mx-auto px-6 text-center">
            <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-8 text-white">
            Why Choose GEO?
            </h2>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto mb-20 leading-relaxed">
            Define the future of AI search optimization with our GEO experts.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-[#111A2E] border border-gray-800 p-10 rounded-2xl text-left shadow-lg">
                <div className="bg-gray-800/50 w-fit p-3 rounded-lg mb-6">
                     <Zap className="text-white h-6 w-6" />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-white">Industry Pioneers</h3>
                <p className="text-gray-400 leading-relaxed text-lg">
                We're the first platform specializing exclusively in Generative Engine Optimization, giving our clients a significant first-mover advantage in this emerging field.
                </p>
            </div>
            
            <div className="bg-[#111A2E] border border-gray-800 p-10 rounded-2xl text-left shadow-lg">
                <div className="bg-gray-800/50 w-fit p-3 rounded-lg mb-6">
                    <TrendingUp className="text-white h-6 w-6" />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-white">Proven Results</h3>
                <p className="text-gray-400 leading-relaxed text-lg">
                Our GEO strategies will help businesses increase their AI citations by 300% and capture high-value traffic from AI-powered searches.
                </p>
            </div>
            </div>
        </section>
      </div>

      {/* 4. See GEO in Action */}
      <section className="w-full max-w-6xl mx-auto py-24 px-6 text-center">
        <h2 className="text-4xl font-extrabold tracking-tight mb-6">
          See GEO in Action
        </h2>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-12">
          Watch how GEO helps you optimize your content for AI search engines and track your performance across multiple platforms.
        </p>

        {/* Dashboard Screenshot */}
        <div className="relative w-full rounded-xl shadow-2xl overflow-hidden border border-gray-200 bg-gray-50">
             <img 
                src="/dashboard-preview.png" 
                alt="GEO Dashboard" 
                className="w-full h-auto" 
                onError={(e) => {
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent) {
                      parent.innerHTML = '<div class="flex items-center justify-center p-10 w-full bg-gray-100 text-gray-400">Dashboard preview image not found</div>';
                    }
                }}
             />
        </div>
      </section>

      {/* 5. FAQ */}
      <section className="w-full max-w-4xl mx-auto py-16 px-6 text-left mb-16">
        <h2 className="text-4xl font-extrabold tracking-tight mb-12 text-center">
          Frequently Asked Questions
        </h2>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto mb-16 text-center">
          Get answers to common questions about Generative Engine Optimization
        </p>

        <div className="space-y-4">
          <details className="border border-gray-200 rounded-xl p-6 shadow-sm group bg-white">
            <summary className="list-none cursor-pointer flex justify-between items-center text-lg font-semibold text-gray-900">
              What is GEO?
              <HelpCircle className="h-5 w-5 text-gray-400 transition-transform duration-200 group-open:rotate-180" />
            </summary>
            <div className="pt-4 text-gray-600 leading-relaxed border-t border-gray-100 mt-4">
              GEO is a comprehensive GEO (Generative Engine Optimization) platform that helps businesses optimize their content to be discovered, cited, and recommended by AI-powered search engines.
            </div>
          </details>

          <details className="border border-gray-200 rounded-xl p-6 shadow-sm group bg-white">
            <summary className="list-none cursor-pointer flex justify-between items-center text-lg font-semibold text-gray-900">
              What is the difference between SEO and GEO?
              <HelpCircle className="h-5 w-5 text-gray-400 transition-transform duration-200 group-open:rotate-180" />
            </summary>
            <div className="pt-4 text-gray-600 leading-relaxed border-t border-gray-100 mt-4">
              Traditional SEO focuses on ranking web pages in classic search result pages (SERPs). GEO focuses specifically on optimizing content to be recognized and cited by Generative AI models.
            </div>
          </details>

          <details className="border border-gray-200 rounded-xl p-6 shadow-sm group bg-white">
            <summary className="list-none cursor-pointer flex justify-between items-center text-lg font-semibold text-gray-900">
              How long does it take to see GEO results?
              <HelpCircle className="h-5 w-5 text-gray-400 transition-transform duration-200 group-open:rotate-180" />
            </summary>
            <div className="pt-4 text-gray-600 leading-relaxed border-t border-gray-100 mt-4">
              We often see initial positive changes in brand citation and sentiment within 4-8 weeks of implementing our core strategies.
            </div>
          </details>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-gray-200 py-10 text-center bg-gray-50">
        <p className="text-sm text-gray-500">
          © 2025 GEO. All rights reserved.
        </p>
      </footer>
    </div>
  );
}