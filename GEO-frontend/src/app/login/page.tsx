"use client";

import { SignupPage } from "@/components/auth/signup-page";
import { useRouter } from "next/navigation";

export default function Login() {
    const router = useRouter();

    const handleSuccess = () => {
        // After login/signup, always check pricing first.
        // pricing-page will auto-skip to /dashboard if already paid.
        router.push("/pricing?source=login");
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="w-full max-w-md">
                <SignupPage onSuccess={handleSuccess} />
            </div>
        </div>
    );
}
