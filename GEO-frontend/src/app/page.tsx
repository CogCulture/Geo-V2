"use client";

import { LandingPage } from "@/components/layout/landing-page";
import { UserProfileMenu } from "@/components/layout/user-profile-menu";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import Link from "next/link";

export default function Home() {
  const { isAuthenticated, subscription } = useAuth();
  const router = useRouter();

  const handleGetStarted = () => {
    if (isAuthenticated) {
      // Paid users go directly to their workspace; unpaid go to pricing.
      router.push(subscription.is_active ? "/dashboard" : "/pricing");
    } else {
      router.push("/login");
    }
  };

  const renderPublicHeader = () => (
    <header className="w-full px-6 py-4 flex items-center justify-between border-b bg-white sticky top-0 z-50 h-[72px]">
      <div className="flex items-center gap-2 cursor-pointer" onClick={() => router.push("/")}>
        <img
          src="/logo.png"
          alt="CogCulture"
          className="h-10 w-auto object-contain"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
            e.currentTarget.parentElement!.innerHTML = '<span class="font-extrabold text-2xl tracking-tighter text-gray-900">CogCulture</span>';
          }}
        />
      </div>
      <div className="flex items-center gap-4">
        {isAuthenticated && (
          <Link href="/dashboard">
            <Button variant="ghost">Dashboard</Button>
          </Link>
        )}
        <Link href="/pricing">
          <Button variant="ghost">Pricing</Button>
        </Link>

        {isAuthenticated ? (
          <UserProfileMenu />
        ) : (
          <Link href="/login">
            <Button variant="default" className="bg-black text-white">
              <LogIn className="h-4 w-4 mr-2" /> Login
            </Button>
          </Link>
        )}
      </div>
    </header>
  );

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {renderPublicHeader()}
      <main className="flex-1 w-full">
        <LandingPage onGetStarted={handleGetStarted} />
      </main>
    </div>
  );
}