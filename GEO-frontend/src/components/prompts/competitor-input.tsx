import { useState } from "react";
import { X, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";

interface CompetitorInputProps {
  competitors: string[];
  onChange: (competitors: string[]) => void;
  disabled?: boolean;
}

export function CompetitorInput({ competitors, onChange, disabled = false }: CompetitorInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleAddCompetitor = () => {
    const trimmed = inputValue.trim();
    if (trimmed && !competitors.includes(trimmed) && competitors.length < 10) {
      onChange([...competitors, trimmed]);
      setInputValue("");
    }
  };

  const handleRemoveCompetitor = (competitor: string) => {
    onChange(competitors.filter(c => c !== competitor));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddCompetitor();
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs font-semibold text-gray-700">
          Competitors <span className="font-normal text-gray-400">(optional, max 10)</span>
        </Label>
        <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
          {competitors.length}/10
        </Badge>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="e.g., Nike, Adidas..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={disabled || competitors.length >= 10}
          className="flex-1 h-9 text-sm"
        />
        <Button
          type="button"
          onClick={handleAddCompetitor}
          disabled={!inputValue.trim() || competitors.length >= 10 || disabled}
          size="sm"
          variant="outline"
          className="h-9 px-3"
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {competitors.length > 0 && (
        <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 rounded-lg max-h-24 overflow-y-auto">
          {competitors.map((competitor) => (
            <Badge
              key={competitor}
              variant="default"
              className="flex items-center gap-1 px-2 py-0.5 text-xs"
            >
              {competitor}
              <button
                type="button"
                onClick={() => handleRemoveCompetitor(competitor)}
                disabled={disabled}
                className="ml-0.5 hover:bg-white/20 rounded-full"
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}