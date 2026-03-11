"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

export default function BrandLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { logout, email } = useAuth();
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const [activeTab, setActiveTab] = useState<'overview' | 'prompts' | 'competitors' | 'citations'>('overview');

    useEffect(() => {
        const tab = searchParams.get("tab");
        if (tab === "prompts") setActiveTab("prompts");
        else if (tab === "competitors") setActiveTab("competitors");
        else if (tab === "citations") setActiveTab("citations");
        else setActiveTab("overview");
    }, [searchParams]);

    const handleTabChange = (tab: 'overview' | 'prompts' | 'competitors' | 'citations') => {
        router.push(`${pathname}?tab=${tab}`);
    };

    return (
        <div className="flex min-h-screen bg-gray-50/50">
            <div className="flex w-full min-h-screen">
                <Sidebar
                    activeTab={activeTab}
                    onTabChange={handleTabChange}
                    onProjectsClick={() => router.push("/dashboard")}
                    onLogout={() => { logout(); router.push("/"); }}
                    email={email || "user@example.com"}
                />
                <div className="flex-1 ml-44 p-5 overflow-y-auto h-screen bg-gray-50/50">
                    <div className="max-w-[1400px] mx-auto">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
