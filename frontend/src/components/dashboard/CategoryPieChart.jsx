import React from "react";
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend,
} from "recharts";

const FALLBACK_COLORS = [
  "#16a34a", "#2563eb", "#dc2626", "#d97706",
  "#7c3aed", "#0891b2", "#be185d", "#6b7280",
];

export default function CategoryPieChart({ data = [], title = "Waste by Category" }) {
  const chartData = data.map((d) => ({ name: d.category, value: d.count }));

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <h3 className="font-bold text-gray-700 mb-4">{title}</h3>
      {chartData.length === 0 ? (
        <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
          No category data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              outerRadius={80}
              dataKey="value"
              label={({ name, percent }) => `${name.replace(/_/g, " ")} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={data[i]?.color_hex || FALLBACK_COLORS[i % FALLBACK_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(val) => [val, "Scans"]}
              contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb" }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
