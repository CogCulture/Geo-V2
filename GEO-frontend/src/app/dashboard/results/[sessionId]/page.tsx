"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { CohortPromptSelector } from "@/components/analysis/cohort-prompt-selector";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

import { Header } from "@/components/layout/header";

export default function ResultsPage() {
    const params = useParams();
    const sessionId = params.sessionId as string;
    const router = useRouter();
    const { isAuthenticated, logout } = useAuth();

    const [showPromptSelection, setShowPromptSelection] = useState(false);

    const handleResultsReady = (sessionId: string) => {
        router.push("/dashboard");
    };

    const handlePromptSelectionReady = () => {
        setShowPromptSelection(true);
    };

    const handleExecuteWizardPrompts = () => {
        setShowPromptSelection(false);
    };

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-gray-50/50">
            <Header />
            <main className="max-w-7xl mx-auto px-6 py-12 animate-in fade-in duration-500">
                <Button variant="ghost" className="mb-4 text-gray-500 hover:text-gray-900" onClick={() => router.push("/dashboard")}>
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Projects
                </Button>
                {showPromptSelection ? (
                    <CohortPromptSelector
                        sessionId={sessionId}
                        onExecute={handleExecuteWizardPrompts}
                    />
                ) : (
                    <AnalysisProgress
                        sessionId={sessionId}
                        onComplete={handleResultsReady}
                        onPromptSelectionReady={handlePromptSelectionReady}
                    />
                )}
            </main>

        </div>
    );
}
