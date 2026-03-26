import React, { useCallback, useState } from "react";

export default function ImageUploader({ onFileSelected, disabled }) {
  const [dragging, setDragging] = useState(false);

  const handle = useCallback(
    (file) => {
      if (!file || !file.type.startsWith("image/")) return;
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handle(e.dataTransfer.files[0]);
  };

  return (
    <label
      onDrop={onDrop}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      className={`flex flex-col items-center justify-center w-full h-56 border-2 border-dashed rounded-2xl cursor-pointer transition-all ${
        dragging
          ? "border-green-500 bg-green-50"
          : "border-gray-300 bg-gray-50 hover:bg-gray-100"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <div className="text-5xl mb-3">📷</div>
      <p className="text-gray-600 font-medium">Drag & drop a waste photo</p>
      <p className="text-gray-400 text-sm mt-1">or click to browse (JPEG/PNG/WebP)</p>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        disabled={disabled}
        onChange={(e) => handle(e.target.files[0])}
      />
    </label>
  );
}
