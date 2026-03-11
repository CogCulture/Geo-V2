import { Card } from "@/components/ui/card";
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface HistoryData {
  date: string;
  timestamp: string;
  visibility_score: number;
  session_id: string;
  brand_name: string;
}

interface VisibilityChartProps {
  brandName?: string;
  mainBrandName?: string;
  chartId?: string; // NEW: Allow custom ID for PDF capture
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function VisibilityChart({
  brandName,
  mainBrandName,
  chartId = "visibility-chart-1", // NEW: Default ID
}: VisibilityChartProps) {
  const [historyData, setHistoryData] = useState<HistoryData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const displayBrandName = brandName || mainBrandName;

  useEffect(() => {
    if (!displayBrandName) return;

    setLoading(true);
    setError(null);

    const fetchBrandHistory = async () => {
      try {
        console.log(`Fetching brand history for: ${displayBrandName}`);

        const token = localStorage.getItem("token");
        const response = await fetch(
          `${API_BASE_URL}/api/brand-history/${encodeURIComponent(displayBrandName)}`,
          {
            headers: {
              "Authorization": `Bearer ${token}`
            }
          }
        );

        console.log(`Response status: ${response.status}`);

        if (!response.ok) {
          if (response.status === 404) {
            console.log("No history found for this brand (404)");
            setHistoryData([]);
            setError(null);
            return;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        let data;
        try {
          data = await response.json();
          console.log("Successfully parsed JSON response:", data);
        } catch (parseError) {
          console.error("Failed to parse response as JSON:", parseError);
          throw new Error(
            "Server returned invalid JSON response. Check browser Network tab for actual response."
          );
        }

        if (!data.history || !Array.isArray(data.history)) {
          console.warn("Response data missing history array:", data);
          setHistoryData([]);
          return;
        }

        console.log(`Setting history data with ${data.history.length} items`);
        setHistoryData(data.history);
        setError(null);
      } catch (err) {
        console.error("Error fetching brand history:", err);
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load history";
        setError(errorMessage);
        setHistoryData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchBrandHistory();
  }, [displayBrandName]);

  const chartData = historyData.map((item) => ({
    date: item.date,
    visibility: Number(item.visibility_score) || 0,
    fullDate: new Date(item.timestamp).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    }),
  }));

  if (loading) {
    return (
      <Card className="p-6" id={chartId}>
        <h3 className="text-lg font-semibold mb-4">
          {displayBrandName
            ? `${displayBrandName} Visibility Over Time`
            : "Brand Visibility"}
        </h3>
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
            Loading historical data...
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6" id={chartId}>
        <h3 className="text-lg font-semibold mb-4">
          {displayBrandName
            ? `${displayBrandName} Visibility Over Time`
            : "Brand Visibility"}
        </h3>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <p className="text-red-500 font-semibold mb-2">Error Loading Data</p>
            <p className="text-sm text-gray-600 mb-2">{error}</p>
            <p className="text-xs text-gray-500">
              Check browser console (F12) and Network tab for more details
            </p>
            <p className="text-xs text-blue-600 mt-2">
              Make sure backend API endpoint /api/brand-history/{displayBrandName} exists
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <Card className="p-6" id={chartId}>
        <h3 className="text-lg font-semibold mb-4">
          {displayBrandName
            ? `${displayBrandName} Visibility Over Time`
            : "Brand Visibility"}
        </h3>
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <p className="font-semibold mb-2">No Historical Data Available</p>
            <p className="text-sm">
              Run analyses on different dates to see the trend for{" "}
              {displayBrandName || "this brand"}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6" id={chartId}>
      <h3 className="text-lg font-semibold mb-2">
        {displayBrandName
          ? `${displayBrandName} Visibility Over Time`
          : "Brand Visibility Over Time"}
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        {chartData.length} analysis{chartData.length !== 1 ? "s" : ""} found
      </p>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="fullDate"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={[0, 100]}
            label={{
              value: "Visibility Score (%)",
              angle: -90,
              position: "insideLeft",
            }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number) => `${Number(value).toFixed(2)}%`}
            contentStyle={{
              backgroundColor: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: "4px",
            }}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend wrapperStyle={{ paddingTop: "20px" }} />
          <Line
            type="monotone"
            dataKey="visibility"
            stroke="hsl(var(--primary))"
            name={`${displayBrandName || "Brand"} Visibility`}
            strokeWidth={2}
            dot={{ fill: "hsl(var(--primary))", r: 5 }}
            activeDot={{ r: 7 }}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Historical Data Table */}
      <div className="mt-6">
        <h4 className="text-sm font-semibold mb-3">Historical Data</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left py-2 px-3 font-semibold">Date</th>
                <th className="text-left py-2 px-3 font-semibold">
                  Visibility Score
                </th>
                <th className="text-left py-2 px-3 font-semibold">Session ID</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((item, idx) => {
                const originalData = historyData[idx];
                return (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-3">{item.fullDate}</td>
                    <td className="py-2 px-3">
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">
                        {item.visibility.toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs text-gray-500 font-mono overflow-hidden text-ellipsis">
                      {originalData?.session_id?.substring(0, 20)}...
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}