import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, LayoutGrid } from "lucide-react";
import type { AnalysisSession } from "@shared/schema";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserBrandSelectorProps {
  currentBrand: string | null;
  onBrandChange: (brandName: string) => void;
}

export function UserBrandSelector({ currentBrand, onBrandChange }: UserBrandSelectorProps) {
  // Fetch both analyses and projects to get all unique brands
  const { data: analysesData, isLoading: isLoadingAnalyses } = useQuery<{ analyses: AnalysisSession[] }>({
    queryKey: ["/api/recent-analyses"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/recent-analyses`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch recent analyses");
      return response.json();
    }
  });

  const { data: projectsData, isLoading: isLoadingProjects } = useQuery<{ projects: any[] }>({
    queryKey: ["/api/projects"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/projects`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch projects");
      return response.json();
    }
  });

  // Extract unique brands from both history and projects
  const uniqueBrands = useMemo(() => {
    const brands = new Set<string>();

    if (analysesData?.analyses) {
      analysesData.analyses.forEach(a => brands.add(a.brand_name));
    }

    if (projectsData?.projects) {
      projectsData.projects.forEach(p => brands.add(p.name));
    }

    return Array.from(brands).sort();
  }, [analysesData, projectsData]);

  const isLoading = isLoadingAnalyses || isLoadingProjects;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 border rounded-md bg-gray-50 opacity-50 w-[200px]">
        <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
        <span className="text-sm text-gray-400">Loading brands...</span>
      </div>
    );
  }

  if (uniqueBrands.length === 0) {
    return null; // Don't show if user has no history
  }

  return (
    <div className="flex items-center gap-3">
      <div className="hidden md:flex items-center justify-center h-8 w-8 rounded-md bg-blue-50 text-blue-600">
        <LayoutGrid className="h-4 w-4" />
      </div>
      <div className="flex flex-col">
        <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Active Brand</span>
        <Select
          value={currentBrand || uniqueBrands[0]}
          onValueChange={onBrandChange}
        >
          <SelectTrigger className="w-[180px] h-8 border-none shadow-none p-0 focus:ring-0 font-bold text-gray-900 bg-transparent hover:bg-transparent">
            <SelectValue placeholder="Select Brand" />
          </SelectTrigger>
          <SelectContent>
            {uniqueBrands.map((brand) => (
              <SelectItem key={brand} value={brand} className="font-medium cursor-pointer">
                {brand}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}