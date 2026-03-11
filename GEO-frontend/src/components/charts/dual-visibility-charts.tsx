import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DualVisibilityChartsProps {
  brandName: string;
  productName?: string;
  sessionId: string;
}

interface ChartDataPoint {
  date: string;
  visibility: number;
  average_position: number | null;
  timestamp: string;
}

export function DualVisibilityCharts({ brandName, productName, sessionId }: DualVisibilityChartsProps) {
  const isProductSpecific = !!productName && productName.trim().length > 0;

  const { data: mainHistoryData } = useQuery({
    queryKey: ["main-visibility-history", brandName, productName, sessionId, isProductSpecific],
    queryFn: async () => {
      const token = localStorage.getItem("token");
      const endpoint = isProductSpecific
        ? `${API_BASE_URL}/api/visibility-history/brand-product/${encodeURIComponent(brandName)}/${encodeURIComponent(productName)}`
        : `${API_BASE_URL}/api/brand-history/${encodeURIComponent(brandName)}`;

      const response = await fetch(endpoint, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) {
        if (response.status === 404) return { history: [] };
        throw new Error("Failed");
      }
      return await response.json();
    },
    staleTime: 0,
    gcTime: 1000 * 60 * 5,
  });

  const mainHistory: ChartDataPoint[] = (mainHistoryData?.history || []).map((item: any) => ({
    date: item.date,
    visibility: Number(item.visibility || item.visibility_score || 0),
    average_position: item.average_position ? Number(item.average_position) : null,
    timestamp: item.timestamp
  }));

  const renderChart = (
    data: ChartDataPoint[],
    title: string,
    color: string,
    gradientId: string,
    subtitle: string,
    dataKey: keyof ChartDataPoint,
    reversed: boolean = false,
    yDomain: [number | string, number | string] = [0, 100]
  ) => (
    <div className="dashboard-card flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-1.5 uppercase tracking-wider">
          <TrendingUp className="h-3 w-3 text-gray-400" />
          {title}
        </h3>
        <p className="text-[10px] text-gray-400 mt-0.5">{subtitle}</p>
      </div>

      <div className="p-3 flex-1 min-h-[200px]">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400 text-xs">
            No historical data available yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(220, 13%, 93%)" />
              <XAxis dataKey="date" axisLine={false} tickLine={false}
                tick={{ fill: 'hsl(220, 9%, 46%)', fontSize: 9 }} dy={5} />
              <YAxis axisLine={false} tickLine={false}
                tick={{ fill: 'hsl(220, 9%, 46%)', fontSize: 9 }}
                domain={yDomain} reversed={reversed} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#ffffff",
                  border: "1px solid hsl(220, 13%, 91%)",
                  borderRadius: "8px",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
                  fontSize: "10px",
                  color: "hsl(222, 47%, 11%)"
                }}
                formatter={(value: number) => [
                  reversed ? `#${value.toFixed(1)}` : `${value.toFixed(1)}%`,
                  title
                ]}
              />
              <Area type="monotone" dataKey={dataKey as string}
                stroke={color} strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={{ fill: "#ffffff", stroke: color, strokeWidth: 2, r: 2.5 }}
                activeDot={{ r: 4, fill: color, stroke: "#ffffff", strokeWidth: 2 }}
                animationDuration={1500} connectNulls />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );

  return (
    <>
      {renderChart(mainHistory, "Overall Brand Trend", "hsl(174, 72%, 46%)", "visGrad",
        "Historical visibility across sessions", "visibility")}
      {renderChart(mainHistory, "Average Position Trend", "hsl(217, 91%, 60%)", "posGrad",
        "Historical average position", "average_position", true, [1, 'auto'])}
    </>
  );
}