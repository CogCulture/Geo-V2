import { useMemo } from "react";
import { SummaryMetrics } from "@/components/dashboard/summary-metrics";
import { PromptsTable } from "@/components/prompts/prompts-table";
import { DualVisibilityCharts } from "@/components/charts/dual-visibility-charts";
import { ShareOfVoiceChart } from "@/components/charts/share-of-voice-chart";
import { DomainCitationsTable } from "@/components/citations/domain-citations-table";
import { PDFReportButton } from "@/components/analysis/pdf-report-button";
import { AvgPositionRank } from "@/components/charts/avg-position-rank";
import type { AnalysisResults as AnalysisResultsType } from "@shared/schema";

interface AnalysisResultsProps {
  results: AnalysisResultsType;
  onNewAnalysis: (prompts: string[], llms: string[]) => void;
  isAnalyzing: boolean;
  sessionId: string;
}

export function AnalysisResults({
  results,
  onNewAnalysis,
  isAnalyzing,
  sessionId,
}: AnalysisResultsProps) {

  const uniqueShareOfVoice = useMemo(() => {
    if (!results.share_of_voice) return [];
    const uniqueMap = new Map();
    results.share_of_voice.forEach(item => {
      const key = item.brand.toLowerCase().trim();
      uniqueMap.set(key, item);
    });
    return Array.from(uniqueMap.values()).sort((a, b) => b.percentage - a.percentage);
  }, [results.share_of_voice]);

  const uniqueResponses = useMemo(() => {
    if (!results.llm_responses) return [];
    const uniqueMap = new Map();
    results.llm_responses.forEach(resp => {
      const key = `${resp.prompt}-${resp.llm_name}`;
      uniqueMap.set(key, resp);
    });
    return Array.from(uniqueMap.values());
  }, [results.llm_responses]);

  return (
    <div className="space-y-6 animate-in fade-in duration-700">

      {/* Header Row */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
          {results.brand_name} Analysis
        </h1>
        <PDFReportButton results={results} sessionId={sessionId} />
      </div>

      {/* Summary Metrics */}
      <SummaryMetrics
        totalPrompts={uniqueResponses.length || 0}
        mentionCount={results.average_mentions || 0}
        averagePosition={results.average_position || 0}
        visibilityScore={results.average_visibility_score || 0}
      />

      {/* Middle Row - 3 Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <PromptsTable responses={uniqueResponses} />
        </div>
        <div className="lg:col-span-3">
          <AvgPositionRank brandName={results.brand_name} brandScores={results.brand_scores || []} />
        </div>
        <div className="lg:col-span-4">
          <ShareOfVoiceChart shareOfVoice={uniqueShareOfVoice} />
        </div>
      </div>

      {/* Bottom Row - 3 Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <DomainCitationsTable citations={results.domain_citations || []} />
        <DualVisibilityCharts brandName={results.brand_name} productName={results.product_name} sessionId={sessionId} />
      </div>
    </div>
  );
}