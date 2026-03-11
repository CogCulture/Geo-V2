"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { isAuthenticated, isLoading, subscription } = useAuth();
    const router = useRouter();
    // Guard against double-redirects while React re-renders
    const redirectingRef = useRef(false);

    useEffect(() => {
        // Wait until auth state is resolved
        if (isLoading) return;
        if (redirectingRef.current) return;

        // ── Gate 1: Must be logged in ─────────────────────────────────────
        if (!isAuthenticated) {
            redirectingRef.current = true;
            router.push("/login");
            return;
        }

        // ── Gate 2: Must have an active subscription ──────────────────────
        // Only enforce once subscription check is done (is_active = false by default while loading)
        if (!subscription.is_active) {
            redirectingRef.current = true;
            router.push("/pricing");
            return;
        }
    }, [isAuthenticated, isLoading, subscription, router]);

    // Reset the redirect guard whenever auth state changes legitimately
    useEffect(() => {
        redirectingRef.current = false;
    }, [isAuthenticated, subscription.is_active]);

    // ── Loading spinner while auth + subscription resolves ────────────────
    if (isLoading) {
        return (
            <div className="h-screen w-full flex flex-col items-center justify-center gap-4 bg-white">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900" />
                <p className="text-sm text-gray-500 font-medium">Loading workspace…</p>
            </div>
        );
    }

    // Don't flash children while redirect is in progress
    if (!isAuthenticated || !subscription.is_active) return null;

    return (
        <div className="min-h-screen bg-transparent">
            <main className="w-full">
                {children}
            </main>
        </div>
    );
}
