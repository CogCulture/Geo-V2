"use client";

import { PricingPage } from "@/components/dashboard/pricing-page";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function Pricing() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    // If user is not logged in and clicks a plan CTA, send them to login
    const handleGetStarted = () => {
        router.push("/login");
    };

    // Close button goes back to the landing page
    const handleClose = () => {
        router.push("/");
    };

    return (
        <div className="min-h-screen">
            <PricingPage
                onGetStarted={handleGetStarted}
                onClose={handleClose}
            />
        </div>
    );
}
