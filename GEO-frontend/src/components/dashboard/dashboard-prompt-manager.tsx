import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Loader2,
  Layers,
  ChevronDown,
  ChevronRight,
  Check,
  Plus,
  Sparkles,
  Trash2,
  ListTodo,
  Play,
  CheckCircle2,
  Search,
  LayoutList
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

import { useAuth } from "@/contexts/AuthContext";

const FRONTEND_PROMPT_LIMITS: Record<string, { max_prompts_per_project: number }> = {
  "free": { max_prompts_per_project: 2 },
  "lite plan": { max_prompts_per_project: 5 },
  "growth plan": { max_prompts_per_project: 10 },
  "custom plan": { max_prompts_per_project: 10 },
  "pro plan": { max_prompts_per_project: 10 },
};

const AVAILABLE_LLMS = [
  { id: "Perplexity", name: "Perplexity" },
  { id: "Claude", name: "Claude 3.5 Sonnet" },
  { id: "Google AI Overview", name: "Google AI Overview" },
  { id: "ChatGPT", name: "ChatGPT-4o" },
  { id: "Gemini", name: "Gemini Pro" }
];

interface DashboardPromptManagerProps {
  sessionId: string;
  analyzedPrompts: Set<string>;
  onReanalyze: (selectedPrompts: string[], selectedLLMs: string[]) => void;
  isAnalyzing: boolean;
  cohorts?: any[];
}

export function DashboardPromptManager({
  sessionId,
  analyzedPrompts,
  onReanalyze,
  isAnalyzing,
  cohorts: initialCohorts
}: DashboardPromptManagerProps) {
  const { toast } = useToast();
  const { subscription } = useAuth();

  const planName = subscription.subscription_plan?.toLowerCase() || "free";
  const limits = FRONTEND_PROMPT_LIMITS[planName] || FRONTEND_PROMPT_LIMITS["free"];

  // Per cohort limit
  const maxPromptsPerCohort = limits.max_prompts_per_project;
  // Global max across 5 cohorts
  const MAX_SELECTION = maxPromptsPerCohort * 5;

  // State
  const [selectedPrompts, setSelectedPrompts] = useState<Set<string>>(new Set());
  const [customPrompt, setCustomPrompt] = useState("");
  const [expandedCohorts, setExpandedCohorts] = useState<Record<string, boolean>>({});
  const [selectedLLMs, setSelectedLLMs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState("active");
  const [cohorts, setCohorts] = useState<any[]>(initialCohorts || []);
  const [loadingCohorts, setLoadingCohorts] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch cohorts if not provided
  useEffect(() => {
    if (initialCohorts && initialCohorts.length > 0) {
      setCohorts(initialCohorts);
      return;
    }

    const fetchCohorts = async () => {
      setLoadingCohorts(true);
      try {
        const token = localStorage.getItem("token");
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${API_BASE_URL}/api/analysis/cohorts/${sessionId}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          setCohorts(data.cohorts || []);
        } else if (response.status === 404) {
          console.warn("No cohorts found yet, analysis may still be processing");
          setCohorts([]);
        } else {
          console.error("Failed to fetch cohorts:", response.status);
          setCohorts([]);
        }
      } catch (error) {
        console.error("Error fetching cohorts:", error);
        setCohorts([]);
      } finally {
        setLoadingCohorts(false);
      }
    };

    fetchCohorts();
  }, [sessionId, initialCohorts]);

  // Sync analyzed prompts to selected prompts on load
  useEffect(() => {
    if (analyzedPrompts.size > 0) {
      setSelectedPrompts(prev => {
        const newSet = new Set(prev);
        analyzedPrompts.forEach(p => newSet.add(p));
        return newSet;
      });
    }
  }, [analyzedPrompts]);

  const toggleCohort = (cohortName: string) => {
    setExpandedCohorts(prev => ({
      ...prev,
      [cohortName]: !prev[cohortName]
    }));
  };

  const togglePrompt = (promptText: string) => {
    const newSelected = new Set(selectedPrompts);
    if (newSelected.has(promptText)) {
      newSelected.delete(promptText);
    } else {
      // Check Global Limit
      if (newSelected.size >= MAX_SELECTION) {
        toast({
          id: "limit-reached",
          title: "Total selection limit reached",
          description: `Your ${planName.toUpperCase()} allows up to ${MAX_SELECTION} prompts in total.`,
          variant: "destructive"
        });
        return;
      }

      newSelected.add(promptText);
    }
    setSelectedPrompts(newSelected);
  };

  const addCustomPrompt = () => {
    if (!customPrompt.trim()) return;
    togglePrompt(customPrompt.trim());
    setCustomPrompt("");
    setActiveTab("active");
  };

  const toggleLLM = (llmId: string) => {
    setSelectedLLMs(prev =>
      prev.includes(llmId)
        ? prev.filter(id => id !== llmId)
        : [...prev, llmId]
    );
  };

  const handleRunAnalysis = () => {
    if (selectedPrompts.size === 0) {
      toast({
        id: "no-prompts",
        title: "No prompts selected",
        variant: "destructive"
      });
      return;
    }
    if (selectedLLMs.length === 0) {
      toast({
        id: "no-llm",
        title: "No AI Platform selected",
        variant: "destructive"
      });
      return;
    }
    onReanalyze(Array.from(selectedPrompts), selectedLLMs);
  };

  // Count stats
  const totalSuggestedPrompts = cohorts.reduce((sum, c) => sum + (c.prompts?.length || 0), 0);
  const analyzedCount = Array.from(selectedPrompts).filter(p => analyzedPrompts.has(p)).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <LayoutList className="h-5 w-5 text-teal-600" />
            Prompt Manager
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">Select queries to analyze your brand visibility on AI platforms.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
        {/* Main Content */}
        <div className="md:col-span-8">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full focus-visible:outline-none">
            <TabsList className="grid w-full grid-cols-2 mb-5 h-10 p-1 bg-gray-100 rounded-lg">
              <TabsTrigger
                value="suggested"
                className="flex items-center gap-1.5 text-xs font-semibold data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md h-full transition-all"
              >
                <Layers className="h-3.5 w-3.5" />
                Suggested
                {totalSuggestedPrompts > 0 && (
                  <Badge variant="secondary" className="ml-1 bg-gray-200 text-gray-600 h-4 px-1 text-[10px] min-w-[16px] justify-center border-none">
                    {totalSuggestedPrompts}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="active"
                className="flex items-center gap-1.5 text-xs font-semibold data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md h-full transition-all relative"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Active
                {selectedPrompts.size > 0 && (
                  <Badge variant="secondary" className="ml-1 bg-teal-100 text-teal-700 h-4 px-1 text-[10px] min-w-[16px] justify-center border-none">
                    {selectedPrompts.size}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* --- TAB 1: SUGGESTED PROMPTS --- */}
            <TabsContent value="suggested" className="space-y-4 animate-in fade-in-50 focus-visible:outline-none outline-none">
              {/* Search + Add Custom */}
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                  <Input
                    placeholder="Search prompts or type a custom question..."
                    value={searchQuery || customPrompt}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setCustomPrompt(e.target.value);
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && addCustomPrompt()}
                    className="pl-9 h-9 text-sm shadow-sm border-gray-200 focus:border-teal-400"
                  />
                </div>
                <Button onClick={addCustomPrompt} size="sm" className="bg-teal-500 hover:bg-teal-600 text-white h-9 px-3 text-xs shadow-sm">
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add
                </Button>
              </div>

              {/* Cohorts */}
              <div className="space-y-3">
                {cohorts && cohorts.length > 0 ? (
                  cohorts.map((cohort, idx) => {
                    const filteredPrompts = searchQuery
                      ? (cohort.prompts || []).filter((p: any) =>
                        p.prompt_text.toLowerCase().includes(searchQuery.toLowerCase())
                      )
                      : (cohort.prompts || []);

                    if (searchQuery && filteredPrompts.length === 0) return null;

                    return (
                      <div key={idx} className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm hover:border-gray-300 transition-all">
                        <div
                          className="px-4 py-3 flex items-center justify-between cursor-pointer select-none hover:bg-gray-50/50 transition-colors"
                          onClick={() => toggleCohort(cohort.name)}
                        >
                          <div className="flex items-center gap-3">
                            <div className="p-1.5 bg-teal-50 rounded-lg text-teal-600">
                              <ListTodo className="h-4 w-4" />
                            </div>
                            <div>
                              <span className="font-semibold text-gray-900 text-sm block">{cohort.name}</span>
                              <span className="text-[11px] text-gray-400">{filteredPrompts.length} prompts</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {filteredPrompts.some((p: any) => selectedPrompts.has(p.prompt_text)) && (
                              <Badge variant="secondary" className="bg-teal-50 text-teal-600 text-[10px] h-5 border-none">
                                {filteredPrompts.filter((p: any) => selectedPrompts.has(p.prompt_text)).length} selected
                              </Badge>
                            )}
                            {expandedCohorts[cohort.name]
                              ? <ChevronDown className="h-4 w-4 text-gray-400" />
                              : <ChevronRight className="h-4 w-4 text-gray-400" />
                            }
                          </div>
                        </div>

                        {expandedCohorts[cohort.name] && (
                          <div className="border-t border-gray-100 bg-gray-50/30 px-2 py-1.5 space-y-1">
                            {filteredPrompts.map((prompt: any, pIdx: number) => {
                              const isSelected = selectedPrompts.has(prompt.prompt_text);
                              const isAnalyzed = analyzedPrompts.has(prompt.prompt_text);

                              return (
                                <div
                                  key={pIdx}
                                  className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all cursor-pointer text-sm",
                                    isSelected
                                      ? "bg-teal-50/80 border border-teal-100"
                                      : "hover:bg-white border border-transparent hover:border-gray-100"
                                  )}
                                  onClick={() => togglePrompt(prompt.prompt_text)}
                                >
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={() => togglePrompt(prompt.prompt_text)}
                                    className={cn("flex-shrink-0", isSelected && "data-[state=checked]:bg-teal-600 data-[state=checked]:border-teal-600")}
                                  />
                                  <p className={cn(
                                    "flex-1 leading-snug text-xs",
                                    isSelected ? "text-teal-900 font-medium" : "text-gray-600"
                                  )}>
                                    {prompt.prompt_text}
                                  </p>
                                  {isAnalyzed && (
                                    <Badge variant="outline" className="text-[9px] bg-emerald-50 text-emerald-600 border-emerald-200 h-4 px-1.5 whitespace-nowrap flex-shrink-0">
                                      <Check className="w-2.5 h-2.5 mr-0.5" /> Analyzed
                                    </Badge>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : loadingCohorts ? (
                  <div className="text-center py-16 text-gray-400 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                    <Loader2 className="h-8 w-8 mx-auto mb-3 animate-spin text-teal-400" />
                    <p className="font-medium text-sm">Curating suggested prompts...</p>
                  </div>
                ) : (
                  <div className="text-center py-16 text-gray-400 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                    <Layers className="h-8 w-8 mx-auto mb-3 text-gray-300" />
                    <p className="font-medium text-sm">No suggestions available</p>
                    <p className="text-xs text-gray-400 mt-1">Add custom prompts using the input above.</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* --- TAB 2: ACTIVE PROMPTS --- */}
            <TabsContent value="active" className="space-y-4 animate-in fade-in-50 focus-visible:outline-none">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-teal-600" />
                    Selected for Analysis
                    <span className="text-gray-400 font-normal">({selectedPrompts.size})</span>
                  </h3>
                  {selectedPrompts.size > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedPrompts(new Set())}
                      className="text-red-500 hover:text-red-600 hover:bg-red-50 h-7 text-xs font-medium"
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      Remove All
                    </Button>
                  )}
                </div>

                {selectedPrompts.size === 0 ? (
                  <div className="text-center py-16 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
                    <CheckCircle2 className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                    <h4 className="text-gray-900 font-semibold text-sm">No prompts selected</h4>
                    <p className="text-gray-400 text-xs mt-1 mb-5 max-w-xs mx-auto">Browse suggested prompts and select the ones you want to analyze.</p>
                    <Button variant="outline" size="sm" onClick={() => setActiveTab("suggested")} className="border-gray-200 text-gray-600 text-xs h-8">
                      <Layers className="h-3.5 w-3.5 mr-1.5" />
                      Browse Suggestions
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                    {Array.from(selectedPrompts).map((prompt, idx) => {
                      const isAnalyzed = analyzedPrompts.has(prompt);
                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between gap-3 px-4 py-3 bg-white rounded-lg border border-gray-100 hover:border-gray-200 transition-all group"
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div className="flex-shrink-0">
                              {isAnalyzed ? (
                                <div className="h-5 w-5 rounded-full bg-emerald-50 flex items-center justify-center border border-emerald-200">
                                  <Check className="h-3 w-3 text-emerald-600" />
                                </div>
                              ) : (
                                <div className="h-5 w-5 rounded-full bg-teal-50 text-teal-600 flex items-center justify-center text-[9px] font-bold border border-teal-200">
                                  {idx + 1}
                                </div>
                              )}
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs text-gray-900 leading-snug font-medium truncate">{prompt}</p>
                              {isAnalyzed && (
                                <span className="text-[9px] text-emerald-600 font-semibold flex items-center gap-1 mt-0.5">
                                  <span className="h-1 w-1 rounded-full bg-emerald-500" />
                                  Already Analyzed
                                </span>
                              )}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => { e.stopPropagation(); togglePrompt(prompt); }}
                            className="h-7 w-7 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* --- CONFIGURATION PANEL (Right Side) --- */}
        <div className="md:col-span-4 sticky top-8 space-y-4">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-500" />
              AI Platforms
            </h3>
            <div className="space-y-2">
              {AVAILABLE_LLMS.map((llm) => {
                const isSelected = selectedLLMs.includes(llm.id);
                return (
                  <div
                    key={llm.id}
                    onClick={() => toggleLLM(llm.id)}
                    className={cn(
                      "cursor-pointer px-3 py-2.5 rounded-lg border transition-all flex items-center gap-3 text-xs font-semibold",
                      isSelected
                        ? "bg-gray-900 text-white border-gray-900 shadow-md"
                        : "bg-white border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50"
                    )}
                  >
                    <div className={cn(
                      "w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all flex-shrink-0",
                      isSelected ? "border-white bg-white/20" : "border-gray-300"
                    )}>
                      {isSelected && <Check className="h-2.5 w-2.5 text-white" />}
                    </div>
                    <span className="truncate">{llm.name}</span>
                  </div>
                )
              })}
            </div>

            <div className="mt-5 pt-4 border-t border-gray-100 space-y-3">
              <Button
                size="lg"
                onClick={handleRunAnalysis}
                disabled={isAnalyzing || selectedPrompts.size === 0 || selectedLLMs.length === 0}
                className="w-full h-12 text-sm font-bold bg-teal-500 hover:bg-teal-600 shadow-md transition-all rounded-xl group"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2 fill-current group-hover:scale-110 transition-transform" />
                    Run Visibility Check
                  </>
                )}
              </Button>

              {/* Analysis Loading Bar */}
              {isAnalyzing && (
                <div className="w-full">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[10px] font-medium text-gray-500">Querying AI platforms...</p>
                    <p className="text-[10px] text-gray-400">May take a few minutes</p>
                  </div>
                  <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-teal-500 rounded-full"
                      style={{
                        width: "40%",
                        animation: "dash-progress 1.6s ease-in-out infinite",
                      }}
                    />
                  </div>
                  <style>{`
                    @keyframes dash-progress {
                      0%   { transform: translateX(-150%); width: 40%; }
                      50%  { transform: translateX(100%);  width: 60%; }
                      100% { transform: translateX(350%);  width: 40%; }
                    }
                  `}</style>
                </div>
              )}

              {!isAnalyzing && (
                <p className="text-[10px] text-center text-gray-400 px-2">
                  Analyzes {selectedPrompts.size}/{MAX_SELECTION} prompts across {selectedLLMs.length} platforms
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}