import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, ArrowRight, Layers, AlertCircle, ChevronDown, ChevronUp, Check, Plus, Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { AVAILABLE_LLMS } from "@shared/schema";

import { useAuth } from "@/contexts/AuthContext";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FRONTEND_PROMPT_LIMITS: Record<string, { max_prompts_per_project: number }> = {
  "free": { max_prompts_per_project: 2 },
  "lite plan": { max_prompts_per_project: 5 },
  "growth plan": { max_prompts_per_project: 10 },
  "custom plan": { max_prompts_per_project: 10 },
  "pro plan": { max_prompts_per_project: 10 },
};

interface CohortPromptSelectorProps {
  sessionId: string;
  onExecute: (selectedIndices: number[], selectedLLMs: string[]) => void;
}

interface Prompt {
  prompt_text: string;
  category?: string;
}

interface CohortData {
  cohorts: {
    id: string; // Added cohort ID
    name: string;
    description?: string;
    prompts: Prompt[];
  }[];
}

// Interface for locally added custom prompts
interface CustomPrompt {
  id: string;
  text: string;
  isSelected: boolean;
}

export function CohortPromptSelector({
  sessionId,
  onExecute,
}: CohortPromptSelectorProps) {
  const { subscription } = useAuth();
  const queryClient = useQueryClient();

  const planName = subscription.subscription_plan?.toLowerCase() || "free";
  const limits = FRONTEND_PROMPT_LIMITS[planName] || FRONTEND_PROMPT_LIMITS["free"];

  // Global project-wide limit (e.g., 5 total for Lite Plan)
  const MAX_SELECTION = limits.max_prompts_per_project;

  // Existing State
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [openCohortIndices, setOpenCohortIndices] = useState<number[]>([]);
  const [selectedLLMs, setSelectedLLMs] = useState<string[]>([]);

  // Custom Cohort Generation State
  const [customTopic, setCustomTopic] = useState("");
  const [customDescription, setCustomDescription] = useState("");
  const [isAddingCustom, setIsAddingCustom] = useState(false);

  // New State for Per-Cohort Custom Prompts
  // Map: cohortIndex -> Array of CustomPrompt objects
  const [cohortCustomPrompts, setCohortCustomPrompts] = useState<Record<number, CustomPrompt[]>>({});
  // Map: cohortIndex -> Current input value
  const [promptInputs, setPromptInputs] = useState<Record<number, string>>({});

  const { data, isLoading, error } = useQuery<CohortData>({
    queryKey: ["cohorts", sessionId],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      console.log("🔐 Fetching cohorts with token:", token ? "✅ Present" : "❌ Missing");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      console.log("📤 Request headers:", headers);
      const response = await fetch(`${API_BASE_URL}/api/analysis/cohorts/${sessionId}`, {
        headers,
        credentials: "include"
      });
      console.log("📥 Cohorts response status:", response.status);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error("❌ Cohorts fetch error:", errorData);
        throw new Error(`Failed to fetch prompts: ${response.status} ${response.statusText}`);
      }
      const jsonData = await response.json();
      console.log("✅ Cohorts data received:", jsonData);
      console.log(`📊 Received ${jsonData.cohorts?.length || 0} cohorts with ${jsonData.total_prompts || 0} total prompts`);
      return jsonData;
    },
  });

  const allGeneratedPrompts = data?.cohorts.flatMap((c) => c.prompts) || [];

  // --- Calculations ---

  const selectedCustomCount = Object.values(cohortCustomPrompts)
    .flat()
    .filter(p => p.isSelected).length;

  const totalSelectedCount = selectedIndices.length + selectedCustomCount;
  const totalAvailableCount = allGeneratedPrompts.length + Object.values(cohortCustomPrompts).flat().length;

  // --- Handlers for Custom Prompts inside Cohorts ---

  const handleAddCustomPromptToCohort = (cohortIndex: number) => {
    const text = promptInputs[cohortIndex]?.trim();
    if (!text) return;

    if (totalSelectedCount >= MAX_SELECTION) {
      return;
    }

    const newPrompt: CustomPrompt = {
      id: `custom-${Date.now()}-${Math.random()}`,
      text: text,
      isSelected: true // Auto-select when adding
    };

    setCohortCustomPrompts(prev => ({
      ...prev,
      [cohortIndex]: [...(prev[cohortIndex] || []), newPrompt]
    }));

    // Clear input
    setPromptInputs(prev => ({ ...prev, [cohortIndex]: "" }));
  };

  const toggleCustomPromptSelection = (cohortIndex: number, promptId: string) => {
    // Check if we are trying to select or deselect
    const currentList = cohortCustomPrompts[cohortIndex] || [];
    const targetPrompt = currentList.find(p => p.id === promptId);

    if (targetPrompt && !targetPrompt.isSelected) {
      // Check limits before selecting
      if (totalSelectedCount >= MAX_SELECTION) {
        return;
      }
    }

    setCohortCustomPrompts(prev => ({
      ...prev,
      [cohortIndex]: prev[cohortIndex].map(p =>
        p.id === promptId ? { ...p, isSelected: !p.isSelected } : p
      )
    }));
  };

  const removeCustomPrompt = (cohortIndex: number, promptId: string) => {
    setCohortCustomPrompts(prev => ({
      ...prev,
      [cohortIndex]: prev[cohortIndex].filter(p => p.id !== promptId)
    }));
  };

  // --- Backend Execution ---

  const generateCustomMutation = useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const response = await fetch(`${API_BASE_URL}/api/analysis/generate-custom-cohort-prompts/${sessionId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          cohort_name: customTopic,
          cohort_description: customDescription
        }),
        credentials: "include"
      });
      if (!response.ok) throw new Error("Failed to generate custom prompts");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cohorts", sessionId] });
      setCustomTopic("");
      setCustomDescription("");
      setIsAddingCustom(false);
    }
  });

  const executeMutation = useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const payload = {
        indices: selectedIndices,
        selected_cohorts: constructBackendPayload(data?.cohorts || [], selectedIndices),
        selected_llms: selectedLLMs
      };

      const response = await fetch(`${API_BASE_URL}/api/analysis/execute-selected-prompts/${sessionId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        credentials: "include"
      });
      if (!response.ok) throw new Error("Failed to start execution");
      return response.json();
    },
    onSuccess: () => {
      onExecute(selectedIndices, selectedLLMs);
    }
  });

  const constructBackendPayload = (cohorts: any[], indices: number[]) => {
    let globalIndex = 0;
    const selected_cohorts = [];

    for (let i = 0; i < cohorts.length; i++) {
      const cohort = cohorts[i];
      const cohortSelectedIndices = [];

      // 1. Get generated prompt indices
      for (let j = 0; j < cohort.prompts.length; j++) {
        if (indices.includes(globalIndex)) {
          cohortSelectedIndices.push(j);
        }
        globalIndex++;
      }

      // 2. Get custom prompts for this cohort
      const customPromptsForCohort = cohortCustomPrompts[i] || [];
      const selectedCustomTexts = customPromptsForCohort
        .filter(p => p.isSelected)
        .map(p => p.text);

      // 3. Add to payload if anything selected
      if (cohortSelectedIndices.length > 0 || selectedCustomTexts.length > 0) {
        selected_cohorts.push({
          cohort_index: i,
          selected_prompt_indices: cohortSelectedIndices,
          custom_prompts: selectedCustomTexts // Backend expects this
        });
      }
    }
    return selected_cohorts;
  };

  // --- Selection Logic ---

  const togglePrompt = (index: number) => {
    const isCurrentlySelected = selectedIndices.includes(index);

    if (!isCurrentlySelected) {
      if (totalSelectedCount >= MAX_SELECTION) {
        return;
      }
    }

    setSelectedIndices((prev) =>
      prev.includes(index)
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    );
  };

  const toggleSelectAll = () => {
    if (totalSelectedCount > 0) {
      // Deselect Everything
      setSelectedIndices([]);

      const newCustomState: Record<number, CustomPrompt[]> = {};
      Object.keys(cohortCustomPrompts).forEach(key => {
        const idx = parseInt(key);
        newCustomState[idx] = cohortCustomPrompts[idx].map(p => ({ ...p, isSelected: false }));
      });
      setCohortCustomPrompts(newCustomState);
    } else {
      // Select according to plan limits (MAX_SELECTION total)
      if (!data) return;

      const newSelectedIndices: number[] = [];
      const newCohortCustomState: Record<number, CustomPrompt[]> = { ...cohortCustomPrompts };

      let currentGlobalIdx = 0;
      let totalSelected = 0;

      data.cohorts.forEach((cohort, cIdx) => {
        // Select generated prompts until global limit
        for (let j = 0; j < cohort.prompts.length; j++) {
          if (totalSelected < MAX_SELECTION) {
            newSelectedIndices.push(currentGlobalIdx);
            totalSelected++;
          }
          currentGlobalIdx++;
        }

        // Select custom prompts until global limit
        if (totalSelected < MAX_SELECTION && newCohortCustomState[cIdx]) {
          newCohortCustomState[cIdx] = newCohortCustomState[cIdx].map(p => {
            if (totalSelected < MAX_SELECTION && !p.isSelected) {
              totalSelected++;
              return { ...p, isSelected: true };
            }
            return p;
          });
        }
      });

      setSelectedIndices(newSelectedIndices);
      setCohortCustomPrompts(newCohortCustomState);
    }
  };

  const toggleCohort = (index: number) => {
    setOpenCohortIndices(prev =>
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const toggleLLM = (llm: string) => {
    setSelectedLLMs(prev =>
      prev.includes(llm) ? prev.filter(l => l !== llm) : [...prev, llm]
    );
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="relative">
          <div className="absolute inset-0 bg-gray-100 rounded-full animate-ping opacity-75"></div>
          <Loader2 className="h-10 w-10 animate-spin text-black relative z-10" />
        </div>
        <h3 className="text-xl font-semibold mt-6 text-gray-900">Generating Strategy...</h3>
        <p className="text-gray-500 mt-2">Creating user cohorts and search prompts</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8">
        <div className="bg-red-50 p-4 rounded-full mb-4">
          <AlertCircle className="h-8 w-8 text-red-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Unable to Load Cohorts</h3>
        <p className="text-gray-500 mt-2 max-w-md">We encountered an error while generating the research cohorts. Please try again.</p>
        <Button variant="outline" className="mt-6" onClick={() => window.location.reload()}>
          Retry Generation
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto p-4 lg:p-8 animate-in fade-in duration-500">

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8 border-b pb-6">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2 tracking-wider uppercase">Step 3/4</p>
          <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-900 mb-2">Cohorts & Prompts</h1>
          <p className="text-gray-500 text-lg">
            We've generated 5 user cohorts for your brand. Customize by adding your own cohorts & prompts.
          </p>
        </div>

        <div className="flex items-center gap-4 bg-gray-50 px-4 py-2 rounded-lg border border-gray-100">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-gray-900">Total Selected</span>
            <span className={cn("text-xs", totalSelectedCount >= MAX_SELECTION ? "text-amber-600 font-bold" : "text-gray-500")}>
              {totalSelectedCount} / {MAX_SELECTION} limit
            </span>
          </div>
          <div className="h-8 w-px bg-gray-200 mx-2"></div>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSelectAll}
            className="text-gray-600 hover:text-black hover:bg-white"
          >
            {totalSelectedCount > 0 ? "Deselect All" : `Select Max (${MAX_SELECTION})`}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 mb-4">
        <Badge variant="outline" className="w-fit text-teal-600 border-teal-200 bg-teal-50">
          Your {planName.toUpperCase()} Limit: {MAX_SELECTION} total prompts across all topics
        </Badge>
      </div>

      {/* Cohorts List */}
      <div className="space-y-4 mb-10">
        {data?.cohorts.map((cohort, cohortIdx) => {
          const isOpen = openCohortIndices.includes(cohortIdx);
          const customPrompts = cohortCustomPrompts[cohortIdx] || [];
          const totalPromptsInCohort = cohort.prompts.length + customPrompts.length;

          return (
            <Card key={cohortIdx} className="overflow-hidden border-gray-200 shadow-sm transition-all duration-200">
              {/* Cohort Header */}
              <div
                onClick={() => toggleCohort(cohortIdx)}
                className="bg-gray-50/80 hover:bg-gray-100 cursor-pointer border-b border-gray-100 px-6 py-4 flex items-center justify-between transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded-md border border-gray-200 shadow-sm">
                    <Layers className="h-4 w-4 text-black" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">{cohort.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {cohort.description || "Targeting specific user intent"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge
                    variant="secondary"
                    className="bg-white border-gray-200 text-gray-600"
                  >
                    {totalPromptsInCohort} Prompts
                  </Badge>
                  {isOpen ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                </div>
              </div>

              {/* Prompts List */}
              {isOpen && (
                <div className="divide-y divide-gray-100 bg-white animate-in slide-in-from-top-2 duration-200">

                  {/* Generated Prompts */}
                  {cohort.prompts.map((prompt, promptIdx) => {
                    const globalIndex = data.cohorts
                      .slice(0, cohortIdx)
                      .reduce((acc, c) => acc + c.prompts.length, 0) + promptIdx;

                    const isSelected = selectedIndices.includes(globalIndex);

                    return (
                      <div
                        key={`gen-${promptIdx}`}
                        onClick={() => togglePrompt(globalIndex)}
                        className={cn(
                          "flex items-start gap-4 p-4 lg:px-6 hover:bg-gray-50 transition-all duration-200 cursor-pointer group border-l-4",
                          isSelected
                            ? "bg-blue-50/10 border-l-black"
                            : "border-l-transparent"
                        )}
                      >
                        <div className="pt-0.5">
                          <Checkbox
                            checked={isSelected}
                            className={cn(
                              "transition-all data-[state=checked]:bg-black data-[state=checked]:border-black",
                              isSelected ? "opacity-100" : "opacity-40 group-hover:opacity-100"
                            )}
                          />
                        </div>
                        <div className="flex-1">
                          <p className={cn(
                            "text-sm leading-relaxed transition-colors",
                            isSelected ? "text-gray-900 font-medium" : "text-gray-600"
                          )}>
                            {prompt.prompt_text}
                          </p>
                        </div>
                      </div>
                    );
                  })}

                  {/* Custom Prompts for this Cohort */}
                  {customPrompts.map((prompt) => (
                    <div
                      key={prompt.id}
                      className={cn(
                        "flex items-start gap-4 p-4 lg:px-6 hover:bg-gray-50 transition-all duration-200 group border-l-4 bg-purple-50/30",
                        prompt.isSelected
                          ? "border-l-purple-600"
                          : "border-l-transparent"
                      )}
                    >
                      <div className="pt-0.5">
                        <Checkbox
                          checked={prompt.isSelected}
                          onCheckedChange={() => toggleCustomPromptSelection(cohortIdx, prompt.id)}
                          className="data-[state=checked]:bg-purple-600 data-[state=checked]:border-purple-600"
                        />
                      </div>
                      <div className="flex-1 flex justify-between items-start gap-2">
                        <div>
                          <p className={cn(
                            "text-sm leading-relaxed transition-colors",
                            prompt.isSelected ? "text-gray-900 font-medium" : "text-gray-600"
                          )}>
                            {prompt.text}
                          </p>
                          <span className="inline-flex items-center rounded-md bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800 ring-1 ring-inset ring-purple-600/20 mt-1">
                            Custom
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeCustomPrompt(cohortIdx, prompt.id);
                          }}
                          className="text-gray-400 hover:text-red-500 transition-colors p-1"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}

                  {/* Input Field for New Prompt */}
                  <div className="p-4 lg:px-6 bg-gray-50 border-t border-gray-100">
                    <div className="flex gap-3">
                      <Input
                        placeholder="Add a custom prompt for this topic..."
                        value={promptInputs[cohortIdx] || ""}
                        onChange={(e) => setPromptInputs(prev => ({ ...prev, [cohortIdx]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddCustomPromptToCohort(cohortIdx);
                          }
                        }}
                        disabled={totalSelectedCount >= MAX_SELECTION}
                        className="bg-white"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAddCustomPromptToCohort(cohortIdx)}
                        disabled={totalSelectedCount >= MAX_SELECTION}
                        className="shrink-0"
                      >
                        <Plus className="h-4 w-4 mr-1" /> Add
                      </Button>
                    </div>
                  </div>

                </div>
              )}
            </Card>
          );
        })}

        {/* Custom Cohort Creation Card */}
        <Card className="overflow-hidden border-dashed border-2 border-gray-200 bg-gray-50/50 shadow-none hover:border-gray-300 transition-colors">
          {!isAddingCustom ? (
            <button
              onClick={() => setIsAddingCustom(true)}
              className="w-full flex items-center justify-center gap-2 p-6 text-gray-500 hover:text-black hover:bg-white transition-all"
            >
              <div className="p-2 bg-white rounded-full border shadow-sm">
                <Plus className="h-4 w-4" />
              </div>
              <span className="font-medium text-sm">Add Custom cohorts</span>
            </button>
          ) : (
            <div className="p-6 bg-white animate-in slide-in-from-bottom-2">
              <div className="flex items-center gap-2 mb-4 text-black">
                <Sparkles className="h-4 w-4" />
                <h3 className="font-bold text-sm">Create Custom Analysis Topic</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-gray-500 mb-1.5 block">Topic Name</label>
                  <Input
                    value={customTopic}
                    onChange={(e) => setCustomTopic(e.target.value)}
                    placeholder="e.g., Holiday Sales, Specific Competitor Comparison..."
                    className="bg-white border-gray-200"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-500 mb-1.5 block">Context / Description</label>
                  <Textarea
                    value={customDescription}
                    onChange={(e) => setCustomDescription(e.target.value)}
                    placeholder="Describe what kind of prompts you want to generate for this topic..."
                    className="bg-white border-gray-200 min-h-[80px]"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsAddingCustom(false)}
                    disabled={generateCustomMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => generateCustomMutation.mutate()}
                    disabled={!customTopic || generateCustomMutation.isPending}
                    className="bg-black hover:bg-gray-800"
                  >
                    {generateCustomMutation.isPending ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3 mr-2" />
                        Generate Prompts
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Platform Selection Section */}
      <div className="border-t pt-8 pb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Platforms to Analyze</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {AVAILABLE_LLMS.map((llm) => {
            const isSelected = selectedLLMs.includes(llm);
            return (
              <div
                key={llm}
                onClick={() => toggleLLM(llm)}
                className={cn(
                  "cursor-pointer relative flex items-center justify-between p-3 rounded-lg border transition-all",
                  isSelected
                    ? "border-black bg-gray-50 shadow-sm"
                    : "border-gray-200 hover:border-gray-300 bg-white"
                )}
              >
                <span className="font-medium text-sm">{llm}</span>
                {isSelected && (
                  <div className="h-4 w-4 bg-black rounded-full flex items-center justify-center">
                    <Check className="h-2.5 w-2.5 text-white" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer Action */}
        <div className="flex flex-col items-center">
          <Button
            size="lg"
            onClick={() => executeMutation.mutate()}
            disabled={(totalSelectedCount === 0) || selectedLLMs.length === 0 || executeMutation.isPending}
            className="w-full max-w-md h-12 text-base font-medium bg-black hover:bg-gray-800 text-white transition-all shadow-lg shadow-gray-200 hover:shadow-xl hover:shadow-gray-300 flex items-center justify-center gap-2 rounded-full"
          >
            {executeMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Processing Analysis...
              </>
            ) : (
              <>
                Run Analysis ({totalSelectedCount})
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </Button>

          {/* Analysis Loading Bar */}
          {executeMutation.isPending && (
            <div className="w-full max-w-md mt-4">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-medium text-gray-600">Sending prompts to AI platforms...</p>
                <p className="text-xs text-gray-400">This may take a few minutes</p>
              </div>
              <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-black rounded-full"
                  style={{
                    width: "40%",
                    animation: "indeterminate-progress 1.5s ease-in-out infinite",
                  }}
                />
              </div>
              <style>{`
                  @keyframes indeterminate-progress {
                    0%   { transform: translateX(-100%); width: 40%; }
                    50%  { transform: translateX(150%); width: 60%; }
                    100% { transform: translateX(300%); width: 40%; }
                  }
                `}</style>
            </div>
          )}

          <div className="flex gap-4 mt-2 text-sm items-center">
            {selectedLLMs.length === 0 && (
              <p className="text-red-500">Please select at least one AI platform</p>
            )}
            {totalSelectedCount >= MAX_SELECTION && (
              <p className="text-amber-600 font-medium bg-amber-50 px-3 py-1 rounded-full border border-amber-200">
                Max limit of {MAX_SELECTION} prompts reached
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}