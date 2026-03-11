import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { ShareOfVoice } from "@shared/schema";

interface ShareOfVoiceChartProps {
  shareOfVoice: ShareOfVoice[];
}

const COLORS = [
  "hsl(174, 72%, 46%)",
  "hsl(217, 91%, 60%)",
  "hsl(38, 92%, 50%)",
  "hsl(262, 52%, 55%)",
  "hsl(340, 82%, 55%)",
  "hsl(160, 84%, 40%)",
];

export function ShareOfVoiceChart({ shareOfVoice }: ShareOfVoiceChartProps) {
  const chartData = (shareOfVoice || [])
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      name: item.brand || "Unknown",
      value: Number(item.percentage) || 0,
    }))
    .filter((item) => item.value > 0);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="dashboard-card p-4 flex flex-col h-full">
        <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Share of Voice</h3>
        <div className="flex-1 flex items-center justify-center text-gray-400 text-xs">
          No share of voice data available yet
        </div>
      </div>
    );
  }

  const renderCustomLabel = ({ cx, cy, midAngle, outerRadius, payload }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius + 20;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text x={x} y={y} fill="hsl(220, 9%, 46%)" textAnchor={x > cx ? "start" : "end"} dominantBaseline="central"
        style={{ fontSize: "10px", fontWeight: "600" }}>
        {`${payload.value.toFixed(1)}%`}
      </text>
    );
  };

  return (
    <div className="dashboard-card flex flex-col h-full" id="sov-chart-container">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Share of Voice</h3>
      </div>
      <div className="flex-1 p-1">
        <ResponsiveContainer width="100%" height={340}>
          <PieChart>
            <Pie data={chartData} cx="50%" cy="42%"
              labelLine={{ stroke: "hsl(220, 13%, 78%)", strokeWidth: 1 }}
              label={renderCustomLabel}
              outerRadius={80} innerRadius={40}
              fill="hsl(var(--primary))" dataKey="value" paddingAngle={3}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#ffffff" strokeWidth={3} />
              ))}
            </Pie>
            <Legend verticalAlign="bottom" align="center" layout="horizontal"
              wrapperStyle={{ paddingTop: "8px", fontSize: "10px", lineHeight: "16px" }}
              iconType="circle" iconSize={6}
              formatter={(value: string, entry: any) => {
                const percentage = entry.payload.value.toFixed(1);
                const displayName = value.length > 15 ? `${value.substring(0, 13)}...` : value;
                return <span style={{ color: 'hsl(220, 9%, 46%)', fontSize: '10px' }}>{displayName} ({percentage}%)</span>;
              }} />
            <Tooltip
              formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
              contentStyle={{
                backgroundColor: "#ffffff",
                border: "1px solid hsl(220, 13%, 91%)",
                borderRadius: "8px",
                padding: "6px 10px",
                boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
              }}
              itemStyle={{ color: "hsl(222, 47%, 11%)", fontSize: "11px", padding: "1px 0" }}
              labelStyle={{ color: "hsl(222, 47%, 11%)", fontWeight: "600", marginBottom: "2px", fontSize: "11px" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}