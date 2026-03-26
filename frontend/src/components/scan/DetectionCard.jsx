import React from "react";

const GROUP_COLORS = {
  dry: "bg-blue-100 text-blue-800 border-blue-200",
  wet: "bg-green-100 text-green-800 border-green-200",
  hazardous: "bg-red-100 text-red-800 border-red-200",
  "e-waste": "bg-orange-100 text-orange-800 border-orange-200",
  mixed: "bg-gray-100 text-gray-800 border-gray-200",
};

const BIN_LABELS = {
  dry: "🔵 Blue Bin (Dry)",
  wet: "🟢 Green Bin (Wet)",
  hazardous: "🔴 Red Bin (Hazardous)",
  "e-waste": "🟠 E-Waste Center",
  mixed: "⚪ Check Guidelines",
};

export default function DetectionCard({ detection }) {
  const group = detection.category_group || "mixed";
  const colorClass = GROUP_COLORS[group] || GROUP_COLORS.mixed;
  const pct = Math.round(detection.confidence * 100);

  return (
    <div className={`rounded-xl border p-4 ${colorClass}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold capitalize">
          {detection.class_name?.replace(/_/g, " ")}
        </span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white bg-opacity-60">
          {pct}%
        </span>
      </div>
      <div className="text-xs opacity-80">
        {BIN_LABELS[group] || BIN_LABELS.mixed}
      </div>
      {detection.mask_area > 0 && (
        <div className="text-xs opacity-60 mt-1">
          Area: {Math.round(detection.mask_area).toLocaleString()} px²
        </div>
      )}
    </div>
  );
}
