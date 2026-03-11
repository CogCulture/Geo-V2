import { useState, useEffect } from "react";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AnalysisProgressProps {
  sessionId: string;
  onComplete: (sessionId: string) => void;
  onPromptSelectionReady: (sessionId: string) => void;
}

export function AnalysisProgress({ sessionId, onComplete, onPromptSelectionReady }: AnalysisProgressProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("Initializing...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const token = localStorage.getItem("token");
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/api/analysis/status/${sessionId}`, { headers });
        
        // ✅ FIXED: Graceful error handling instead of throw
        if (!response.ok) {
           console.warn("Status polling failed, retrying...");
           return; 
        }

        const data = await response.json();
        
        // Handle the response - backend returns progress object directly
        const progressData = data.data || data;
        const { progress: currentProgress, current_step, status: currentStatus, error: apiError } = progressData;

        setProgress(currentProgress);
        setStatus(current_step);

        if (apiError) {
          setError(apiError);
          clearInterval(intervalId);
        } else if (currentStatus === "pending_selection") {
           clearInterval(intervalId);
           onPromptSelectionReady(sessionId);
        } else if (currentStatus === "completed" || currentProgress === 100) {
          clearInterval(intervalId);
          setTimeout(() => onComplete(sessionId), 1000);
        }
      } catch (err) {
        console.error("Polling error:", err);
        // Don't set error state immediately to avoid flashing error UI on single failed poll
      }
    };

    intervalId = setInterval(pollStatus, 2000); // Poll every 2 seconds
    return () => clearInterval(intervalId);
  }, [sessionId, onComplete, onPromptSelectionReady]);

  if (error) {
    return (
      <Card className="max-w-md mx-auto mt-20 p-6 text-center border-red-200 bg-red-50">
        <AlertCircle className="h-10 w-10 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-red-900 mb-2">Analysis Failed</h3>
        <p className="text-sm text-red-700">{error}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-xl mx-auto text-center px-4">
      <div className="mb-8 relative">
        <div className="h-16 w-16 rounded-full bg-blue-50 flex items-center justify-center">
            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
        </div>
      </div>
      
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Analyzing Brand Visibility</h2>
      <p className="text-gray-500 mb-8 max-w-md">
        {status || "Please wait while our AI agents research your brand..."}
      </p>

      <div className="w-full space-y-2">
        <Progress value={progress} className="h-2" />
        <div className="flex justify-between text-xs text-gray-400 font-medium uppercase tracking-wide">
            <span>Start</span>
            <span>{progress}%</span>
        </div>
      </div>
    </div>
  );
}