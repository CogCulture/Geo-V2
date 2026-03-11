import { useState, useMemo } from "react";
import React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LLMResponse } from "@shared/schema";
import {
  ChevronLeft,
  ChevronRight,
  Search,
} from "lucide-react";

interface PromptsTableProps {
  responses: LLMResponse[];
}

const ITEMS_PER_PAGE = 6;

const isBrandMentioned = (response: LLMResponse): boolean => {
  return (response.visibility_score !== undefined &&
    response.visibility_score !== null &&
    response.visibility_score > 0);
};

export function PromptsTable({ responses }: PromptsTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedResponse, setSelectedResponse] = useState<LLMResponse | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [filterMentioned, setFilterMentioned] = useState<string>("all");

  const filteredResponses = useMemo(() => {
    let result = responses;
    if (filterMentioned === "mentioned") {
      result = result.filter(r => isBrandMentioned(r));
    } else if (filterMentioned === "not_mentioned") {
      result = result.filter(r => !isBrandMentioned(r));
    }
    if (!searchTerm) return result;
    const term = searchTerm.toLowerCase();
    return result.filter(
      (r) => r.prompt?.toLowerCase().includes(term) || r.llm_name?.toLowerCase().includes(term) || r.llm_model?.toLowerCase().includes(term) || r.model_name?.toLowerCase().includes(term) || r.response?.toLowerCase().includes(term)
    );
  }, [responses, searchTerm, filterMentioned]);

  const totalPages = Math.ceil(filteredResponses.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const currentResponses = filteredResponses.slice(startIndex, endIndex);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(Math.max(1, Math.min(newPage, totalPages)));
  };

  const sanitizeOverviewText = (text: string | undefined | null) => {
    if (!text) return "";
    const patterns = [
      /An AI Overview is not available for this search/gi,
      /Can(?:'t| not) generate an AI overview right now(?:\.|)\s*Try again later(?:\.|)/gi,
      /AI Overview/gi, /Listen\s*Pause/gi, /सुनें\s*रोकें/gi,
      /Error translating content(?:\.|).*?Please try again later(?:\.|)/gi,
      /Can't generate an right now/gi, /हिन्दी/gi
    ];
    let cleaned = text;
    for (const p of patterns) cleaned = cleaned.replace(p, "");
    cleaned = cleaned.replace(/\s+/g, " ").trim();
    return cleaned || text;
  };

  const openResponseDialog = (response: LLMResponse) => {
    const cloned: LLMResponse = { ...response };
    cloned.response = sanitizeOverviewText(cloned.response);
    setSelectedResponse(cloned);
    setDialogOpen(true);
  };

  const getCitations = (response: LLMResponse): string[] => {
    if (!response.citations) return [];
    if (typeof response.citations === "string") {
      try { return JSON.parse(response.citations); } catch { return []; }
    }
    if (Array.isArray(response.citations)) {
      return response.citations.filter(c => c && typeof c === "string");
    }
    return [];
  };


  const getLLMShortName = (name: string) => {
    const n = name?.toLowerCase() || "";
    if (n.includes("chatgpt")) return "ChatGPT";
    if (n.includes("gemini")) return "Gemini";
    if (n.includes("claude")) return "Claude";
    if (n.includes("perplexity")) return "Perplexity";
    if (n.includes("copilot") || n.includes("bing")) return "Copilot";
    if (n.includes("google") && n.includes("overview")) return "Google AI Overview";
    return name || "Unknown";
  };

  return (
    <div className="dashboard-card flex flex-col h-full">
      {/* Header with title, search, and filter inline */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-3 flex-wrap">
        <h3 className="text-sm font-bold text-gray-900 whitespace-nowrap">Analyzed Prompts Table</h3>
        <div className="relative flex-1 min-w-[120px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400" />
          <Input
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="pl-7 h-7 text-xs bg-gray-50 border-gray-200 text-gray-900 placeholder:text-gray-400 focus:border-teal-400"
          />
        </div>
        <Select value={filterMentioned} onValueChange={(value) => { setFilterMentioned(value); setCurrentPage(1); }}>
          <SelectTrigger className="w-[100px] h-7 text-xs bg-gray-50 border-gray-200 text-gray-600">
            <SelectValue placeholder="Filters" />
          </SelectTrigger>
          <SelectContent className="bg-white border-gray-200">
            <SelectItem value="all">Filters</SelectItem>
            <SelectItem value="mentioned">Mentioned</SelectItem>
            <SelectItem value="not_mentioned">Not Mentioned</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table header row */}
      <div className="px-4 py-2 grid grid-cols-[1fr_auto_auto_auto] gap-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100">
        <span>Prompt Text</span>
        <span className="w-[90px] text-center">Source LLM</span>
        <span className="w-[55px] text-center">Citations</span>
        <span className="w-[90px] text-center">Brand Mentioned</span>
      </div>

      {/* Table body */}
      <div className="flex-1 overflow-y-auto max-h-[340px]">
        {currentResponses.length === 0 ? (
          <div className="text-center py-6 text-gray-400 text-xs">
            {searchTerm || filterMentioned !== "all" ? "No results found" : "No prompts analyzed yet"}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {currentResponses.map((response, index) => {
              const globalIndex = startIndex + index;
              const mentioned = isBrandMentioned(response);
              const citations = getCitations(response);

              return (
                <div key={globalIndex}
                  className="px-4 py-2.5 grid grid-cols-[1fr_auto_auto_auto] gap-2 items-center hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => openResponseDialog(response)}>

                  {/* Prompt Text */}
                  <span className="text-xs text-gray-700 truncate pr-2 leading-snug">
                    {response.prompt || "—"}
                  </span>

                  {/* Source LLM */}
                  <div className="w-[90px] flex items-center gap-1.5 justify-center">
                    
                    <span className="text-[11px] text-gray-500 font-medium truncate">{getLLMShortName(response.llm_name || "")}</span>
                  </div>

                  {/* Citations count */}
                  <div className="w-[55px] text-center">
                    <span className="text-xs text-gray-500 font-medium">{citations.length}</span>
                  </div>

                  {/* Brand Mentioned */}
                  <div className="w-[90px] flex justify-center">
                    {mentioned ? (
                      <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-3 py-0.5 rounded-md border border-emerald-200">YES</span>
                    ) : (
                      <span className="text-[10px] font-bold text-red-500 bg-red-50 px-3 py-0.5 rounded-md border border-red-200">NO</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setSelectedResponse(null); setDialogOpen(open); }}>
        <DialogContent className="max-w-5xl w-[90%] p-0 bg-white border-gray-200">
          <div className="flex w-full">
            <div className="w-80 bg-gray-50 p-5 border-r border-gray-200 overflow-y-auto max-h-[70vh]">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-base text-gray-900">Sources</h4>
                <span className="inline-block bg-teal-500 text-white text-xs px-2 py-0.5 rounded-full">{selectedResponse ? getCitations(selectedResponse).length : 0}</span>
              </div>
              <div className="space-y-2">
                {selectedResponse && getCitations(selectedResponse).length > 0 ? (
                  getCitations(selectedResponse).map((c, i) => (
                    <div key={i} className="rounded-md border border-gray-200 p-2.5 bg-white">
                      <a href={c} target="_blank" rel="noreferrer" className="text-xs text-teal-600 underline break-all">{c}</a>
                      <div className="mt-1.5 flex gap-1.5">
                        <Button size="sm" variant="outline" className="h-6 text-[10px] border-gray-200 text-gray-600 hover:bg-gray-100" onClick={() => window.open(c, "_blank")}>Open</Button>
                        <Button size="sm" variant="ghost" className="h-6 text-[10px] text-gray-500 hover:text-gray-900" onClick={() => { navigator.clipboard?.writeText(c); }}>Copy</Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-400">No sources available.</div>
                )}
              </div>
            </div>
            <div className="flex-1 p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <DialogTitle className="text-lg text-gray-900">{selectedResponse?.prompt ?? "Response Details"}</DialogTitle>
                  <DialogDescription className="text-xs text-gray-500">Response from {selectedResponse?.llm_name ?? "LLM"}</DialogDescription>
                </div>
                <Button size="sm" variant="outline" className="h-7 text-xs border-gray-200 text-gray-600 hover:bg-gray-100" onClick={() => { if (selectedResponse) navigator.clipboard?.writeText(selectedResponse.response || ""); }}>
                  Copy
                </Button>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed max-h-[60vh] overflow-y-auto pr-2">
                  {selectedResponse?.response ? sanitizeOverviewText(selectedResponse.response) : "No response available."}
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-2 border-t border-gray-200 flex items-center justify-between">
          <span className="text-[10px] text-gray-400">{currentPage}/{totalPages}</span>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" className="h-6 w-6 p-0 border-gray-200 text-gray-500 bg-white hover:bg-gray-50" onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <Button variant="outline" size="sm" className="h-6 w-6 p-0 border-gray-200 text-gray-500 bg-white hover:bg-gray-50" onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}