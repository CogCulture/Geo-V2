import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Trash2, Plus, RefreshCw, Users } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

// Helper function for API requests
async function apiRequest(method: string, url: string, body: any) {
  const token = localStorage.getItem("token");
  const res = await fetch(process.env.NEXT_PUBLIC_API_URL + url, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error("API Request failed");
  return res.json();
}

interface CompetitorManagerProps {
  sessionId: string;
  currentCompetitors: (string | { name: string })[];
  onUpdate: () => void;
}

export function CompetitorManager({ sessionId, currentCompetitors, onUpdate }: CompetitorManagerProps) {
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [newCompetitor, setNewCompetitor] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const { toast } = useToast();

  // ✅ FIXED: Sanitize input data to remove null/undefined values immediately
  useEffect(() => {
    if (currentCompetitors && Array.isArray(currentCompetitors)) {
      // Filter out null, undefined, or empty strings, handling both string and object formats
      const cleanList = currentCompetitors.map(c => {
        if (typeof c === 'string') return c;
        // @ts-ignore - Handle object case safely even if TS complains about strict type checks
        if (typeof c === 'object' && c !== null && 'name' in c) return c.name;
        return null;
      }).filter(c => c && typeof c === 'string' && c.trim() !== "");

      setCompetitors(Array.from(new Set(cleanList as string[])));
    }
  }, [currentCompetitors]);

  const handleAdd = () => {
    const val = newCompetitor.trim();
    if (!val) return;

    // ✅ FIXED: Safe check that ensures 'c' exists before calling toLowerCase()
    const exists = competitors.some(c => c && c.toLowerCase() === val.toLowerCase());

    if (exists) {
      toast({
        title: "Competitor already exists",
        description: `${val} is already in the list.`,
        variant: "destructive"
      });
      return;
    }

    setCompetitors([...competitors, val]);
    setNewCompetitor("");
  };

  const handleDelete = (indexToDelete: number) => {
    setCompetitors(competitors.filter((_, index) => index !== indexToDelete));
  };

  const handleSave = async () => {
    try {
      setIsUpdating(true);

      // ✅ FIXED: Ensure we send a clean list to the backend
      const cleanCompetitors = competitors.filter(c => c && c.trim());

      await apiRequest(
        "POST",
        `/api/analysis/${sessionId}/update-competitors`,
        { competitors: cleanCompetitors }
      );

      toast({
        title: "Analysis Updated",
        description: "Metrics and Share of Voice have been recalculated.",
      });

      onUpdate();

    } catch (error) {
      console.error(error);
      toast({
        title: "Update Failed",
        description: "Could not update competitors. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      <Card className="border border-gray-100 bg-white shadow-sm">
        <CardHeader className="pb-6">
          <CardTitle className="text-lg font-semibold text-gray-900">Current Competitors</CardTitle>
          <CardDescription>
            {competitors.length === 0 ? "No competitors tracked yet" : `${competitors.length} competitor${competitors.length !== 1 ? 's' : ''} in your analysis`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Add New Competitor Input */}
          <div className="flex gap-2">
            <Input
              placeholder="Enter competitor name (e.g., Adidas)"
              value={newCompetitor}
              onChange={(e) => setNewCompetitor(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              className="flex-1 bg-white border-gray-200 text-gray-900 placeholder:text-gray-400 focus:border-teal-400"
            />
            <Button
              onClick={handleAdd}
              variant="secondary"
              className="gap-2 bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <Plus className="h-4 w-4" /> Add
            </Button>
          </div>

          {/* Competitors Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {competitors.length === 0 && (
              <div className="col-span-full text-center py-8 text-gray-500 border border-dashed border-gray-200 rounded-lg">
                No competitors tracked. Add one to start comparing.
              </div>
            )}

            {competitors.map((comp, index) => {
              if (!comp) return null;
              return (
                <div
                  key={`${comp}-${index}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors"
                >
                  <span className="font-medium text-gray-900">{comp}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-gray-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 p-0"
                    onClick={() => handleDelete(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              );
            })}
          </div>

          {/* Save Button */}
          <div className="pt-4 border-t border-gray-100">
            <Button
              onClick={handleSave}
              disabled={isUpdating}
              className="w-full bg-teal-500 text-white hover:bg-teal-600 gap-2 shadow-md"
            >
              {isUpdating && <RefreshCw className="h-4 w-4 animate-spin" />}
              {isUpdating ? "Recalculating Metrics..." : "Save & Recalculate"}
            </Button>
            <p className="text-xs text-gray-500 text-center mt-3">
              Updates Share of Voice and Average Position instantly
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}