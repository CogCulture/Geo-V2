import { Button } from "@/components/ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ReanalyzeButtonProps {
  sessionId: string;
  onReanalyzeStart?: () => void;
}

export function ReanalyzeButton({
  sessionId,
  onReanalyzeStart,
}: ReanalyzeButtonProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const reanalyzeMutation = useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_BASE_URL}/api/reanalyze-with-same-prompts/${sessionId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
        }
      );
      if (!response.ok) {
        throw new Error("Failed to start re-analysis");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Re-analysis started",
        description: `New session: ${data.new_session_id.substring(0, 8)}...`,
      });
      onReanalyzeStart?.();
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["same-prompts-history"] });
      queryClient.invalidateQueries({ queryKey: ["recent-analyses"] });
      queryClient.invalidateQueries({ queryKey: ["visibility-history"] });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start re-analysis",
        variant: "destructive",
      });
    },
  });

  return (
    <Button
      onClick={() => reanalyzeMutation.mutate()}
      disabled={reanalyzeMutation.isPending}
      variant="outline"
      size="sm"
      className="w-full"
    >
      {reanalyzeMutation.isPending ? (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Re-analyzing...
        </>
      ) : (
        <>
          <RefreshCw className="h-4 w-4 mr-2" />
          Re-analyze with Same Prompts
        </>
      )}
    </Button>
  );
}