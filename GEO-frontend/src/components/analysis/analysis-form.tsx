import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { KeywordInput } from "@/components/prompts/keyword-input";
import { CompetitorInput } from "@/components/prompts/competitor-input";
import { BrandAliasInput } from "@/components/analysis/brand-alias-input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api-client";
import { analysisRequestSchema, type AnalysisRequest } from "@shared/schema";
import { Loader2, ArrowRight, Globe, Sparkles, CheckCircle2, Search, Lock } from "lucide-react";

interface AnalysisFormProps {
  onAnalysisStart: (sessionId: string) => void;
}

export function AnalysisForm({ onAnalysisStart }: AnalysisFormProps) {
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState(1);
  const [brandLocked, setBrandLocked] = useState(false);
  const [suggestedCompetitors, setSuggestedCompetitors] = useState<string[]>([]);
  const [inferredIndustry, setInferredIndustry] = useState<string>("");

  const form = useForm({
    resolver: zodResolver(analysisRequestSchema),
    defaultValues: {
      brand_name: "",
      product_name: "", // Removed from UI
      industry: "", // Removed from UI
      website_url: "",
      num_prompts: 10,
      selected_llms: [],
      custom_keywords: [],
      custom_competitors: [],
      brand_aliases: [],
    },
  });

  const researchMutation = useMutation({
    mutationFn: async (data: { brand_name: string; website_url?: string }) => {
      const response = await apiRequest("POST", "/api/analysis/research", data);
      return await response.json();
    },
    onSuccess: (result) => {
      if (result.status === "success" && result.data) {
        const competitors = result.data.competitors || [];
        if (competitors.length > 0) {
          form.setValue("custom_competitors", competitors);
          setSuggestedCompetitors(competitors);
        }
        if (result.data.industry) {
          setInferredIndustry(result.data.industry);
          form.setValue("industry", result.data.industry);
        }
        setBrandLocked(true);
        setCurrentStep(2);
        toast({
          title: "Research Complete",
          description: `Found ${competitors.length} potential competitors.`,
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: "Research Failed",
        description: error.message || "Failed to conduct initial research.",
        variant: "destructive",
      });
    }
  });

  const startAnalysisMutation = useMutation({
    mutationFn: async (data: AnalysisRequest) => {
      let projectId = null;
      try {
        const token = localStorage.getItem("token");
        const projectResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            name: data.brand_name,
            website_url: data.website_url,
            industry: data.industry || inferredIndustry,
            initial_prompts: data.custom_keywords,
            initial_competitors: data.custom_competitors
          })
        });

        if (projectResponse.ok) {
          const projectResult = await projectResponse.json();
          if (projectResult.project?.id) projectId = projectResult.project.id;
        } else if (projectResponse.status === 403) {
          // Plan limit reached
          const errorData = await projectResponse.json();
          throw new Error(errorData.detail || "You have reached the project limit for your plan.");
        }
      } catch (e: any) {
        console.error("Background project creation failed", e);
        // If it was a plan limit error (403), stop here and show the toast
        if (e.message?.includes("limit reached")) {
          throw e;
        }
      }

      const analysisPayload = {
        ...data,
        industry: data.industry || inferredIndustry, // Ensure industry is passed
        project_id: projectId
      };

      const response = await apiRequest("POST", "/api/analysis/run", analysisPayload);
      return await response.json();
    },
    onSuccess: (data: { session_id: string }) => {
      onAnalysisStart(data.session_id);
    },
    onError: (error: Error) => {
      toast({
        title: "Analysis Failed",
        description: error.message || "Failed to start analysis.",
        variant: "destructive",
      });
    },
  });

  const handleNextStep = async () => {
    if (currentStep === 1) {
      // If research already ran (fields locked), skip the API call
      if (brandLocked) {
        setCurrentStep(2);
        return;
      }
      const brand = form.getValues("brand_name");
      const url = form.getValues("website_url");
      if (!brand) {
        form.trigger("brand_name");
        return;
      }
      researchMutation.mutate({ brand_name: brand, website_url: url });
    } else if (currentStep === 2) {
      setCurrentStep(3);
    } else {
      // Final submit
      form.handleSubmit((data) => startAnalysisMutation.mutate(data))();
    }
  };

  const brandName = form.watch("brand_name");
  const isStep1Valid = !!brandName;

  // Render helpers
  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-4 gap-2">
      {[1, 2, 3].map((step) => (
        <div key={step} className={`h-2 rounded-full transition-all duration-300 ${step <= currentStep ? 'w-8 bg-black' : 'w-2 bg-gray-200'}`} />
      ))}
    </div>
  );

  return (
    <div className="w-full max-w-xl mx-auto lg:mx-0 animate-in fade-in duration-500">
      <div className="mb-4">
        <p className="text-xs font-medium text-gray-500 mb-2 tracking-wider uppercase">
          {currentStep === 1 && "Step 1: Brand Details"}
          {currentStep === 2 && "Step 2: Competitor Analysis"}
          {currentStep === 3 && "Step 3: Fine-tuning"}
        </p>
        <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-gray-900 mb-3">
          {currentStep === 1 && "Start Research"}
          {currentStep === 2 && "Review Competitors"}
          {currentStep === 3 && "Final Details"}
        </h1>
        {renderStepIndicator()}
      </div>

      <Form {...form}>
        <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>

          {/* STEP 1 */}
          {currentStep === 1 && (
            <div className="space-y-4 animate-in slide-in-from-right-4 duration-300">
              <div className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-all duration-200">
                <FormField
                  control={form.control}
                  name="brand_name"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-gray-100 rounded-md">
                          <Sparkles className="h-4 w-4 text-gray-700" />
                        </div>
                        <FormLabel className="text-sm font-bold text-gray-900">Brand Name <span className="text-red-500">*</span></FormLabel>
                        {brandLocked && <Lock className="h-3.5 w-3.5 text-gray-400 ml-auto" />}
                      </div>
                      <FormControl>
                        <Input
                          placeholder="Enter your brand name"
                          {...field}
                          disabled={brandLocked}
                          className="h-10 border-gray-200 focus:border-black rounded-lg text-sm disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-all duration-200">
                <FormField
                  control={form.control}
                  name="website_url"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-gray-100 rounded-md">
                          <Globe className="h-4 w-4 text-gray-700" />
                        </div>
                        <FormLabel className="text-sm font-bold text-gray-900">Brand URL</FormLabel>
                        {brandLocked && <Lock className="h-3.5 w-3.5 text-gray-400 ml-auto" />}
                      </div>
                      <FormControl>
                        <Input
                          placeholder="https://example.com"
                          {...field}
                          disabled={brandLocked}
                          className="h-10 border-gray-200 focus:border-black rounded-lg text-sm disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
          )}

          {/* STEP 2 */}
          {currentStep === 2 && (
            <div className="space-y-3 animate-in slide-in-from-right-4 duration-300">
              {/* Slim research-complete strip */}
              <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-100 rounded-lg">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
                <p className="text-xs text-emerald-800 font-medium">
                  Found <strong>{suggestedCompetitors.length}</strong> competitors
                  {inferredIndustry && <span> · Industry: <strong>{inferredIndustry}</strong></span>}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-3 bg-white shadow-sm">
                <FormField
                  control={form.control}
                  name="custom_competitors"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <CompetitorInput
                          competitors={field.value || []}
                          onChange={field.onChange}
                          disabled={false}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
          )}

          {/* STEP 3 */}
          {currentStep === 3 && (
            <div className="space-y-4 animate-in slide-in-from-right-4 duration-300">
              <div className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-all duration-200">
                <FormField
                  control={form.control}
                  name="brand_aliases"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <BrandAliasInput
                          aliases={field.value || []}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-all duration-200">
                <FormField
                  control={form.control}
                  name="custom_keywords"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <KeywordInput
                          keywords={field.value || []}
                          onChange={field.onChange}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
          )}

          <div className="pt-4 flex flex-col items-center">
            <Button
              type="button"
              onClick={handleNextStep}
              size="lg"
              className="w-full max-w-md h-11 text-base font-medium bg-black hover:bg-gray-800 text-white transition-all shadow-lg shadow-gray-200 hover:shadow-xl hover:shadow-gray-300 flex items-center justify-center gap-2 rounded-full"
              disabled={
                (currentStep === 1 && (!isStep1Valid || researchMutation.isPending)) ||
                (currentStep === 3 && startAnalysisMutation.isPending)
              }
            >
              {researchMutation.isPending || startAnalysisMutation.isPending ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  {currentStep === 1 ? "Researching..." : "Starting Analysis..."}
                </>
              ) : (
                <>
                  {currentStep === 3 ? "Start Analysis" : "Next Step"}
                  {currentStep !== 3 && <ArrowRight className="h-5 w-5" />}
                </>
              )}
            </Button>
            {currentStep > 1 && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 text-gray-500 hover:text-black"
                onClick={() => setCurrentStep(prev => prev - 1)}
                disabled={startAnalysisMutation.isPending}
              >
                Back to previous step
              </Button>
            )}
          </div>

        </form>
      </Form>
    </div>
  );
}