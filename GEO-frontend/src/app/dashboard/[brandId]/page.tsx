"use client";

import { useState, useEffect, useMemo } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { AnalysisResults } from "@/components/analysis/analysis-results";
import { DashboardPromptManager } from "@/components/dashboard/dashboard-prompt-manager";
import { CompetitorManager } from "@/components/prompts/competitor-manager";
import { CitationAnalytics } from "@/components/citations/citation-analytics";
import { Users } from "lucide-react";
import type { AnalysisResults as AnalysisResultsType } from "@shared/schema";
import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export default function BrandDashboard() {
    const params = useParams();
    const searchParams = useSearchParams();
    const router = useRouter();
    const brandName = params.brandId as string;
    const tab = searchParams.get("tab") || "overview";

    const { isAuthenticated } = useAuth();
    const [analysisResults, setAnalysisResults] = useState<AnalysisResultsType | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isReanalyzing, setIsReanalyzing] = useState(false);

    useEffect(() => {
        if (!isAuthenticated || !brandName) return;

        const fetchLatestSession = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem("token");
                let resolvedBrandName = decodeURIComponent(brandName);

                // Detect if brandName is a UUID (Project ID)
                const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
                if (uuidRegex.test(resolvedBrandName)) {
                    // It's a project ID, resolve it to a brand name first
                    const projectRes = await fetch(`${API_BASE_URL}/projects/${resolvedBrandName}`, {
                        headers: { "Authorization": `Bearer ${token}` }
                    });
                    if (projectRes.ok) {
                        const projectData = await projectRes.json();
                        resolvedBrandName = projectData.project.name;
                        console.log("Resolved UUID to brand:", resolvedBrandName);
                    }
                }

                // 1. Get recent analyses to find the latest for this brand
                const response = await fetch(`${API_BASE_URL}/recent-analyses`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (!response.ok) throw new Error("Failed to fetch sessions");
                const data = await response.json();
                const sessions = data.analyses || [];

                const latestSession = sessions.find((s: any) =>
                    s.brand_name.toLowerCase() === resolvedBrandName.toLowerCase()
                );

                if (latestSession) {
                    setSessionId(latestSession.session_id);
                    // 2. Load results for this session
                    const resultsRes = await fetch(`${API_BASE_URL}/results/${latestSession.session_id}`, {
                        headers: { "Authorization": `Bearer ${token}` }
                    });
                    if (!resultsRes.ok) throw new Error("Failed to load results");
                    const resultsData = await resultsRes.json();
                    setAnalysisResults(resultsData);
                } else {
                    setError(`No analysis found for "${resolvedBrandName}".`);
                }
            } catch (err: any) {
                console.error("Fetch results error:", err);
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchLatestSession();
    }, [brandName, isAuthenticated]);

    const analyzedPromptsSet = useMemo(() => {
        const set = new Set<string>();
        if (analysisResults?.llm_responses) {
            analysisResults.llm_responses.forEach(r => {
                if (r.prompt) set.add(r.prompt);
            });
        }
        return set;
    }, [analysisResults]);

    const displayCohorts = useMemo(() => {
        if (analysisResults?.cohorts && Array.isArray(analysisResults.cohorts) && analysisResults.cohorts.length > 0) {
            return analysisResults.cohorts;
        }
        if (analysisResults?.research_data?.cohorts) {
            return analysisResults.research_data.cohorts;
        }
        return [];
    }, [analysisResults]);

    const handleDashboardReanalyze = async (selectedPrompts: string[], selectedLLMs: string[]) => {
        if (!sessionId) return;
        setIsReanalyzing(true);
        try {
            const token = localStorage.getItem("token");
            const response = await fetch(`${API_BASE_URL}/analysis/fork-session?parent_session_id=${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ prompts: selectedPrompts, llms: selectedLLMs })
            });

            if (!response.ok) throw new Error("Failed to start new analysis");
            const data = await response.json();

            // Redirect to the results/progress page for the new session
            router.push(`/dashboard/results/${data.new_session_id}`);

        } catch (e) {
            console.error("Reanalysis failed", e);
            alert("Failed to start reanalysis. Please try again.");
            setIsReanalyzing(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500"></div>
            </div>
        );
    }

    if (error) {
        const isNotFoundError = error.includes("No analysis found");
        return (
            <div className="p-12 text-center bg-white rounded-2xl border border-gray-100 shadow-sm max-w-2xl mx-auto mt-12 animate-in fade-in zoom-in duration-500">
                <div className="w-20 h-20 bg-teal-50 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg className="w-10 h-10 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">No Analysis Data Yet</h2>
                <p className="text-gray-500 mb-8 px-4">
                    {isNotFoundError
                        ? `We haven't run any visibility analysis for ${decodeURIComponent(brandName)} yet. Let's get started with your first scan!`
                        : `There was a problem loading results: ${error}`}
                </p>

                {isNotFoundError ? (
                    <button
                        onClick={() => router.push("/dashboard/analysis")}
                        className="px-8 py-3 bg-teal-500 text-white rounded-xl font-bold hover:bg-teal-600 transition-all shadow-lg hover:scale-105"
                    >
                        Run Primary Analysis
                    </button>
                ) : (
                    <button
                        onClick={() => window.location.reload()}
                        className="px-6 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                    >
                        Try Again
                    </button>
                )}
            </div>
        );
    }

    return (
        <div className="animate-in fade-in duration-500">
            {tab === 'overview' && analysisResults && (
                <AnalysisResults
                    results={analysisResults}
                    onNewAnalysis={() => router.push("/dashboard/analysis")}
                    sessionId={sessionId!}
                    isAnalyzing={false}
                />
            )}

            {tab === 'prompts' && sessionId && (
                <DashboardPromptManager
                    sessionId={sessionId}
                    analyzedPrompts={analyzedPromptsSet}
                    onReanalyze={handleDashboardReanalyze}
                    isAnalyzing={isReanalyzing}
                    cohorts={displayCohorts}
                />
            )}

            {tab === 'competitors' && sessionId && analysisResults && (
                <div className="space-y-6">
                    <div className="flex items-center gap-3 border-b border-gray-100 pb-6">
                        <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                            <Users className="h-6 w-6" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Manage Competitors</h1>
                            <p className="text-gray-500">Add or remove competitors to recalculate Share of Voice.</p>
                        </div>
                    </div>

                    <CompetitorManager
                        sessionId={sessionId}
                        currentCompetitors={analysisResults.competitors || []}
                        onUpdate={() => window.location.reload()}
                    />
                </div>
            )}

            {tab === 'citations' && analysisResults && (
                <CitationAnalytics
                    sessionId={sessionId!}
                    brandName={analysisResults.brand_name}
                />
            )}
        </div>
    );
}
