import React from "react";

export default function LoadingSpinner({ size = "md", label = "Loading..." }) {
  const sizes = { sm: "h-5 w-5", md: "h-8 w-8", lg: "h-12 w-12" };
  return (
    <div className="flex flex-col items-center justify-center py-8 space-y-2">
      <div className={`${sizes[size]} animate-spin rounded-full border-4 border-green-200 border-t-green-600`} />
      {label && <span className="text-sm text-gray-500">{label}</span>}
    </div>
  );
}
