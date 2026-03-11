import { FileText, MessageCircle, TrendingUp, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

interface SummaryMetricsProps {
  totalPrompts: number;
  mentionCount: number;
  averagePosition: number;
  visibilityScore: number;
}

export function SummaryMetrics({
  totalPrompts,
  mentionCount,
  averagePosition,
  visibilityScore,
}: SummaryMetricsProps) {

  const metrics = [
    {
      label: "Analyzed Prompts",
      value: totalPrompts || 0,
      icon: FileText,
      description: "Total Prompts processed",
      accentClass: "metric-card-cyan",
    },
    {
      label: "Brand Mentions",
      value: mentionCount || 0,
      icon: MessageCircle,
      description: "Appearance in responses",
      accentClass: "metric-card-emerald",
    },
    {
      label: "Avg. Position",
      value: (averagePosition || 0).toFixed(1),
      icon: TrendingUp,
      description: "Rank in responses",
      accentClass: "metric-card-amber",
    },
    {
      label: "Visibility Score",
      value: `${(visibilityScore || 0).toFixed(1)}%`,
      icon: Trophy,
      description: "Overall brand presence",
      accentClass: "metric-card-blue",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      {metrics.map((metric, idx) => (
        <div key={idx} className={cn("metric-card py-3 px-4", metric.accentClass)}>
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
              {metric.label}
            </p>
            <div className="p-1 rounded-md bg-gray-50">
              <metric.icon className="h-3.5 w-3.5 text-gray-400" />
            </div>
          </div>
          <h3 className="text-2xl font-extrabold text-gray-900 tracking-tight leading-tight">
            {metric.value}
          </h3>
          <p className="text-[10px] text-gray-400 font-medium mt-0.5">
            {metric.description}
          </p>
        </div>
      ))}
    </div>
  );
}