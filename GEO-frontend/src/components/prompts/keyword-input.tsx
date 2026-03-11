import { useState } from "react";
import { X, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";

interface KeywordInputProps {
  keywords: string[];
  onChange: (keywords: string[]) => void;
  disabled?: boolean;
}

export function KeywordInput({ keywords, onChange, disabled = false }: KeywordInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleAddKeyword = () => {
    const trimmed = inputValue.trim();
    if (trimmed && !keywords.includes(trimmed) && keywords.length < 10) {
      onChange([...keywords, trimmed]);
      setInputValue("");
    }
  };

  const handleRemoveKeyword = (keyword: string) => {
    onChange(keywords.filter(k => k !== keyword));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddKeyword();
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs font-semibold text-gray-700">
          Custom Keywords <span className="font-normal text-gray-400">(optional, max 10)</span>
        </Label>
        <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
          {keywords.length}/10
        </Badge>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="e.g., affordable, premium..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={disabled || keywords.length >= 10}
          className="flex-1 h-9 text-sm"
        />
        <Button
          type="button"
          onClick={handleAddKeyword}
          disabled={!inputValue.trim() || keywords.length >= 10 || disabled}
          size="sm"
          variant="outline"
          className="h-9 px-3"
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 rounded-lg max-h-20 overflow-y-auto">
          {keywords.map((keyword) => (
            <Badge
              key={keyword}
              variant="default"
              className="flex items-center gap-1 px-2 py-0.5 text-xs"
            >
              {keyword}
              <button
                type="button"
                onClick={() => handleRemoveKeyword(keyword)}
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