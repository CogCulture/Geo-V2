"use client";

import { AnalysisForm } from "@/components/analysis/analysis-form";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowLeft } from "lucide-react";


export default function AnalysisPage() {
    const router = useRouter();
    const { logout } = useAuth();

    const handleAnalysisStart = (sessionId: string) => {
        router.push(`/dashboard/results/${sessionId}`);
    };

    const renderHeader = () => (
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
                <Button variant="ghost" onClick={() => router.push("/dashboard")}>Projects</Button>
                <Button variant="ghost" onClick={() => router.push("/pricing")}>Pricing</Button>
                <Button variant="default" className="bg-black text-white" onClick={() => { logout(); router.push("/"); }}>
                    Log Out
                </Button>
            </div>
        </header>
    );

    return (
        <div className="min-h-screen bg-gray-50/50">
            {renderHeader()}
            <main className="max-w-7xl mx-auto px-6 py-4 animate-in fade-in duration-500">
                <Button variant="ghost" className="mb-4 text-gray-500 hover:text-gray-900" onClick={() => router.push("/dashboard")}>
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Projects
                </Button>
                <div className="flex flex-col lg:flex-row w-full gap-6">

                    <div className="w-full lg:w-[60%] bg-white p-5 lg:p-7 rounded-2xl shadow-sm border border-gray-100">
                        <AnalysisForm onAnalysisStart={handleAnalysisStart} />
                    </div>
                    <div className="hidden lg:block lg:w-[40%] bg-white/50 border border-dashed border-gray-200 p-8 rounded-2xl">
                        <div className="h-full w-full flex flex-col justify-center gap-4 text-center">
                            <h3 className="font-semibold text-gray-900">Analysis Wizard</h3>
                            <p className="text-sm text-gray-500">
                                Fill in the details to generate custom prompts and track your brand visibility across top AI models.
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
