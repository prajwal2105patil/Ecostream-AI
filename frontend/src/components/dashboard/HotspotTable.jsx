import React from "react";

const LEVEL_BADGE = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-green-100 text-green-700 border-green-200",
};

export default function HotspotTable({ hotspots = [], loading }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-bold text-gray-700">Predicted Hotspots (Next 24h)</h3>
      </div>
      {loading ? (
        <div className="p-8 text-center text-gray-400 text-sm">Loading predictions...</div>
      ) : hotspots.length === 0 ? (
        <div className="p-8 text-center text-gray-400 text-sm">No hotspot data available</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="px-5 py-3 text-left">Ward</th>
              <th className="px-5 py-3 text-right">Predicted Scans</th>
              <th className="px-5 py-3 text-center">Priority</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {hotspots.map((h, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-800">{h.ward_number}</td>
                <td className="px-5 py-3 text-right text-gray-600">{h.predicted_count}</td>
                <td className="px-5 py-3 text-center">
                  <span className={`inline-block px-2 py-0.5 text-xs rounded-full border font-medium ${LEVEL_BADGE[h.urgency_level] || LEVEL_BADGE.low}`}>
                    {h.urgency_level}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
