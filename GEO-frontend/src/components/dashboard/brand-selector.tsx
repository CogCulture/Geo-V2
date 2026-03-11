import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Search, ChevronDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BrandSelectorProps {
  onBrandSelect: (brand: string) => void;
  selectedBrand: string | null;
}

export function BrandSelector({ onBrandSelect, selectedBrand }: BrandSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const { data: brandsData, isLoading } = useQuery({
    queryKey: ["brands"],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const response = await fetch(`${API_BASE_URL}/api/brands`, { headers, credentials: "include" });
      if (!response.ok) throw new Error("Failed to fetch brands");
      return response.json();
    },
    staleTime: 1000 * 60 * 5,
  });

  const filteredBrands = useMemo(() => {
    if (!brandsData?.brands) return [];
    return brandsData.brands.filter((brand: string) =>
      brand.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [brandsData?.brands, searchTerm]);

  return (
    <div className="w-full mb-4">
      <div className="relative">
        <Button
          variant="outline"
          className="w-full justify-between"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span className="truncate">
            {selectedBrand || "Select a brand..."}
          </span>
          <ChevronDown className="h-4 w-4" />
        </Button>

        {isOpen && (
          <Card className="absolute top-full left-0 right-0 mt-2 z-50 p-2">
            <div className="mb-2">
              <Input
                placeholder="Search brands..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-8"
              />
            </div>

            <div className="max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="p-2 text-sm text-gray-500">Loading brands...</div>
              ) : filteredBrands.length === 0 ? (
                <div className="p-2 text-sm text-gray-500">No brands found</div>
              ) : (
                filteredBrands.map((brand: string) => (
                  <button
                    key={brand}
                    onClick={() => {
                      onBrandSelect(brand);
                      setIsOpen(false);
                      setSearchTerm("");
                    }}
                    className={`w-full text-left px-2 py-2 rounded hover:bg-gray-100 transition ${
                      selectedBrand === brand ? "bg-blue-100" : ""
                    }`}
                  >
                    {brand}
                  </button>
                ))
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}