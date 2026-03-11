import type { DomainCitation } from "@shared/schema";
import { ExternalLink } from "lucide-react";

interface DomainCitationsTableProps {
  citations: DomainCitation[];
}

export function DomainCitationsTable({ citations }: DomainCitationsTableProps) {
  const sortedCitations = [...citations].sort((a, b) => (b.citation_count || 0) - (a.citation_count || 0)).slice(0, 10);
  const maxPercentage = sortedCitations.length > 0 ? Math.max(...sortedCitations.map(c => c.percentage)) : 100;

  return (
    <div className="dashboard-card flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <ExternalLink className="h-3.5 w-3.5 text-gray-400" />
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Top Cited Domains</h3>
        </div>
        <p className="text-[10px] text-gray-400 mt-0.5">Most referenced sources in AI responses</p>
      </div>

      <div className="flex-1 overflow-auto">
        {sortedCitations.length === 0 ? (
          <div className="flex items-center justify-center h-full p-4">
            <div className="text-center space-y-1">
              <ExternalLink className="h-8 w-8 mx-auto text-gray-300" />
              <p className="text-xs text-gray-400">No citation data available</p>
            </div>
          </div>
        ) : (
          <div className="px-4 py-2 space-y-1.5">
            {sortedCitations.map((citation, index) => (
              <div key={index} className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <span className="text-[9px] text-gray-400 font-mono w-3">{index + 1}</span>
                  <span className="text-xs text-gray-700 font-medium truncate">{citation.domain}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <div className="w-12 h-1 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-teal-400 to-blue-500"
                      style={{ width: `${(citation.percentage / maxPercentage) * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-semibold text-gray-500 min-w-[32px] text-right">
                    {citation.percentage.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}