"use client";

import {
    TrendingUp,
    TrendingDown,
    Minus,
    HelpCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface BrandScore {
    brand: string;
    average_position: number;
    prev_average_position?: number;
    visibility_score: number;
    mention_rate: number;
    rank: number;
}

interface AvgPositionRankProps {
    brandName: string;
    brandScores: BrandScore[];
}

const DOT_COLORS = [
    "bg-teal-500",
    "bg-blue-500",
    "bg-amber-500",
    "bg-purple-500",
    "bg-rose-500",
    "bg-emerald-500",
    "bg-orange-500",
    "bg-cyan-500",
    "bg-violet-500",
    "bg-red-500",
];

export function AvgPositionRank({ brandName, brandScores }: AvgPositionRankProps) {
    // Deduplicate: backend sends one entry per LLM per brand — merge them
    const deduplicatedScores = Object.values(
        brandScores.reduce<Record<string, { brand: string; positions: number[]; visibilities: number[]; mention_rates: number[]; prev_positions: number[]; min_rank: number }>>((acc, score) => {
            const key = score.brand.toLowerCase();
            if (!acc[key]) {
                acc[key] = { brand: score.brand, positions: [], visibilities: [], mention_rates: [], prev_positions: [], min_rank: score.rank };
            }
            if (score.average_position > 0) acc[key].positions.push(score.average_position);
            acc[key].visibilities.push(score.visibility_score);
            acc[key].mention_rates.push(score.mention_rate);
            if (score.prev_average_position && score.prev_average_position > 0) acc[key].prev_positions.push(score.prev_average_position);
            acc[key].min_rank = Math.min(acc[key].min_rank, score.rank);
            return acc;
        }, {})
    ).map(entry => ({
        brand: entry.brand,
        average_position: entry.positions.length ? entry.positions.reduce((s, v) => s + v, 0) / entry.positions.length : 0,
        prev_average_position: entry.prev_positions.length ? entry.prev_positions.reduce((s, v) => s + v, 0) / entry.prev_positions.length : undefined,
        visibility_score: entry.visibilities.reduce((s, v) => s + v, 0) / entry.visibilities.length,
        mention_rate: entry.mention_rates.reduce((s, v) => s + v, 0) / entry.mention_rates.length,
        rank: entry.min_rank,
    }));

    // Cap positions to total tracked brands (rank can never exceed N brands)
    const totalBrands = deduplicatedScores.length;
    const cappedScores = deduplicatedScores.map(s => ({
        ...s,
        average_position: s.average_position > 0 ? Math.min(s.average_position, totalBrands) : 0,
        prev_average_position: s.prev_average_position && s.prev_average_position > 0
            ? Math.min(s.prev_average_position, totalBrands) : s.prev_average_position,
    }));

    const sortedScores = [...cappedScores].sort((a, b) => {
        if (a.average_position === 0) return 1;
        if (b.average_position === 0) return -1;
        return a.average_position - b.average_position;
    });

    const mainBrandData = cappedScores.find(b => b.brand.toLowerCase() === brandName.toLowerCase());
    const mainBrandRank = mainBrandData ? (sortedScores.findIndex(s => s.brand.toLowerCase() === brandName.toLowerCase()) + 1) : 0;


    const calculateDelta = (current: number, previous: number | undefined) => {
        if (!previous || previous === 0 || current === 0) return null;
        return previous - current;
    };

    return (
        <div className="dashboard-card flex flex-col h-full">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                        Average Position Rank
                    </h3>
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger>
                                <HelpCircle className="h-3 w-3 text-gray-400" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-[200px] bg-white border-gray-200 text-gray-700 text-xs shadow-lg">
                                Your rank based on Average Position compared to competitors.
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
                <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-3xl font-black text-gray-900 leading-none">
                        #{mainBrandRank || '-'}
                    </span>
                    <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Overall rank</span>
                </div>
            </div>

            {/* Column headers */}
            <div className="px-4 py-1.5 flex items-center justify-between text-[9px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100">
                <span>Domain</span>
                <span>Avg Position</span>
            </div>

            {/* Rankings list */}
            <div className="flex-1 px-4 overflow-y-auto max-h-[300px]">
                <div className="divide-y divide-gray-50">
                    {sortedScores.slice(0, 10).map((brand, idx) => {
                        const isMainBrand = brand.brand === brandName;
                        const delta = calculateDelta(brand.average_position, brand.prev_average_position);

                        return (
                            <div key={idx} className="py-2 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className={cn("h-2 w-2 rounded-full flex-shrink-0", DOT_COLORS[idx % DOT_COLORS.length])} />
                                    <span className={cn("text-xs", isMainBrand ? "font-bold text-gray-900" : "text-gray-600 font-medium")}>
                                        {brand.brand}
                                    </span>
                                </div>

                                <div className="flex items-center gap-2">
                                    <div className="text-right">
                                        <span className={cn("text-xs font-bold", isMainBrand ? "text-gray-900" : "text-gray-700")}>
                                            {brand.average_position > 0 ? brand.average_position.toFixed(1) : '-'}
                                        </span>
                                    </div>
                                    {delta !== null && delta !== 0 && (
                                        <div className={cn("text-[9px] font-bold flex items-center", delta > 0 ? "text-emerald-600" : "text-rose-500")}>
                                            {delta > 0 ? <TrendingUp className="h-2 w-2 mr-0.5" /> : <TrendingDown className="h-2 w-2 mr-0.5" />}
                                            {Math.abs(delta).toFixed(1)}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
