import { useState } from "react";
import { X, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";

interface BrandAliasInputProps {
    aliases: string[];
    onChange: (aliases: string[]) => void;
    disabled?: boolean;
}

export function BrandAliasInput({ aliases, onChange, disabled = false }: BrandAliasInputProps) {
    const [inputValue, setInputValue] = useState("");

    const handleAddAlias = () => {
        const trimmed = inputValue.trim();
        if (trimmed && !aliases.includes(trimmed) && aliases.length < 5) {
            onChange([...aliases, trimmed]);
            setInputValue("");
        }
    };

    const handleRemoveAlias = (alias: string) => {
        onChange(aliases.filter(a => a !== alias));
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            e.preventDefault();
            handleAddAlias();
        }
    };

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold text-gray-700">
                    Brand Aliases <span className="font-normal text-gray-400">(optional, max 5)</span>
                </Label>
                <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                    {aliases.length}/5
                </Badge>
            </div>

            <div className="flex gap-2">
                <Input
                    placeholder="e.g., KFC, Kentucky Fried..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={disabled || aliases.length >= 5}
                    className="flex-1 h-9 text-sm"
                />
                <Button
                    type="button"
                    onClick={handleAddAlias}
                    disabled={!inputValue.trim() || aliases.length >= 5 || disabled}
                    size="sm"
                    variant="outline"
                    className="h-9 px-3"
                >
                    <Plus className="h-3.5 w-3.5" />
                </Button>
            </div>

            {aliases.length > 0 && (
                <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 rounded-lg max-h-20 overflow-y-auto">
                    {aliases.map((alias) => (
                        <Badge
                            key={alias}
                            variant="default"
                            className="flex items-center gap-1 px-2 py-0.5 text-xs"
                        >
                            {alias}
                            <button
                                type="button"
                                onClick={() => handleRemoveAlias(alias)}
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
