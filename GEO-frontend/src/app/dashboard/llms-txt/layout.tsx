"use client";


import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function LlmsTxtLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { logout, email } = useAuth();
    const router = useRouter();

    return (
        <div className="flex min-h-screen bg-gray-50/50">
            <div className="flex w-full min-h-screen">
                <Sidebar
                    activeTab={"llms-txt" as any}
                    onTabChange={(tab) => {
                        // Navigate to dashboard — the user clicked an analytics tab
                        router.push(`/dashboard`);
                    }}
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
