import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Package, Globe, Clock } from "lucide-react";
import { Loader2 } from "lucide-react";

interface RecentAnalysesListProps {
  onAnalysisSelect: (sessionId: string, brandName: string) => void;
}

interface AnalysisSession {
  session_id: string;
  brand_name: string;
  timestamp: string;
  product_name?: string;
  website_url?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"; // ✅ FIX

export function RecentAnalysesList({ onAnalysisSelect }: RecentAnalysesListProps) {
  const { data, isLoading, error } = useQuery<{ total: number; analyses: AnalysisSession[] }>({
    queryKey: ["/api/recent-analyses"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/recent-analyses`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      }); // ✅ FIX: Use absolute URL
      if (!response.ok) {
        throw new Error(`Failed to fetch recent analyses: ${response.status}`);
      }
      return response.json();
    },
    staleTime: 1000 * 60 * 5,
    retry: 2, // ✅ Add retry logic
  });

  if (isLoading) {
    return (
      <Card className="p-6 text-center">
        <Loader2 className="animate-spin mx-auto mb-2" />
        Loading recent analyses...
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 text-center text-red-600">
        <p>Error loading recent analyses.</p>
        <p className="text-sm mt-2">Ensure backend is running on {API_BASE_URL}</p>
      </Card>
    );
  }

  if (!data || data.total === 0) {
    return (
      <Card className="p-6 text-center text-muted-foreground">
        No previous analyses found.
        <br />
        Start a new analysis to get results.
      </Card>
    );
  }

  return (
    <div className="space-y-4 max-h-[500px] overflow-y-auto p-2">
      {data.analyses.map((analysis) => (
        <Card
          key={analysis.session_id}
          className="p-4 hover:bg-muted cursor-pointer transition"
          onClick={() => onAnalysisSelect(analysis.session_id, analysis.brand_name)}
        >
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-lg">{analysis.brand_name}</h4>
            <time dateTime={analysis.timestamp} className="text-sm text-muted-foreground">
              <Clock className="inline-block w-4 h-4 mr-1" />
              {new Date(analysis.timestamp).toLocaleString()}
            </time>
          </div>
          {analysis.product_name && (
            <p className="text-sm text-muted-foreground truncate">
              <Package className="inline w-4 h-4 mr-1" />
              {analysis.product_name}
            </p>
          )}
          {analysis.website_url && (
            <p className="text-sm text-muted-foreground truncate">
              <Globe className="inline w-4 h-4 mr-1" />
              <a
                href={analysis.website_url}
                target="_blank"
                rel="noreferrer"
                className="underline"
                onClick={(e) => e.stopPropagation()}
              >
                {analysis.website_url}
              </a>
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={(e) => {
              e.stopPropagation();
              onAnalysisSelect(analysis.session_id, analysis.brand_name);
            }}
          >
            View Results
          </Button>
        </Card>
      ))}
    </div>
  );
}