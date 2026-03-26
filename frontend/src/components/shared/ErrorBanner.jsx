import React from "react";

export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="flex items-start justify-between bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="ml-3 text-red-500 hover:text-red-700 font-bold">
          ✕
        </button>
      )}
    </div>
  );
}
