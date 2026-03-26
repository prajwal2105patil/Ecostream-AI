import React, { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { uploadScan, getScan, scanImageUrl } from "../api/scanApi";
import ImageUploader from "../components/scan/ImageUploader";
import DetectionCard from "../components/scan/DetectionCard";
import ChatPanel from "../components/scan/ChatPanel";
import LoadingSpinner from "../components/shared/LoadingSpinner";
import ErrorBanner from "../components/shared/ErrorBanner";

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 30;

export default function ScanChat() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [scanId, setScanId] = useState(null);
  const [scan, setScan] = useState(null);
  const [error, setError] = useState("");
  const [pollCount, setPollCount] = useState(0);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!user) navigate("/login");
  }, [user, navigate]);

  // Poll for scan result
  useEffect(() => {
    if (!scanId || scan?.scan_status === "done" || scan?.scan_status === "failed") return;
    if (pollCount >= MAX_POLLS) {
      setError("Processing timed out. Please try again.");
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const result = await getScan(scanId);
        setScan(result);
        setPollCount((c) => c + 1);
      } catch (err) {
        setError("Failed to fetch scan result.");
      }
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [scanId, scan, pollCount]);

  const handleFileSelected = useCallback((f) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setScanId(null);
    setScan(null);
    setError("");
    setPollCount(0);
  }, []);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      let lat = null, lon = null;
      try {
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 3000 })
        );
        lat = pos.coords.latitude;
        lon = pos.coords.longitude;
      } catch {}
      const result = await uploadScan(file, lat, lon);
      setScanId(result.scan_id);
      setScan({ scan_status: "pending" });
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const isProcessing = scan && !["done", "failed"].includes(scan.scan_status);
  const isDone = scan?.scan_status === "done";
  const detections = scan?.detected_classes || [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Scan Waste</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Upload a photo of waste — our AI will identify the materials and tell you exactly how to dispose of them.
      </p>

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-4">
        {/* Left: Image panel */}
        <div className="space-y-4">
          {!preview ? (
            <ImageUploader onFileSelected={handleFileSelected} disabled={uploading} />
          ) : (
            <div className="relative">
              <img
                src={isDone && scanId ? scanImageUrl(scanId) : preview}
                alt="Waste scan"
                className="w-full rounded-2xl object-cover max-h-80 border border-gray-200"
                onError={(e) => { e.target.src = preview; }}
              />
              {isDone && (
                <span className="absolute top-2 right-2 bg-green-500 text-white text-xs px-3 py-1 rounded-full font-medium">
                  ✓ Annotated
                </span>
              )}
            </div>
          )}

          {preview && !scanId && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-xl disabled:opacity-50 transition-colors"
            >
              {uploading ? "Uploading..." : "Analyze This Image"}
            </button>
          )}

          {preview && (
            <button
              onClick={() => {
                setFile(null);
                setPreview(null);
                setScanId(null);
                setScan(null);
                setError("");
              }}
              className="w-full text-gray-500 text-sm hover:text-gray-700 py-2"
            >
              ↩ Upload different image
            </button>
          )}
        </div>

        {/* Right: Results panel */}
        <div className="space-y-4">
          {isProcessing && (
            <div className="bg-blue-50 rounded-2xl p-6 border border-blue-100">
              <LoadingSpinner label="AI is analyzing your waste..." />
              <p className="text-center text-blue-600 text-sm mt-2">
                Running YOLOv11 instance segmentation + RAG lookup...
              </p>
            </div>
          )}

          {isDone && (
            <>
              {/* Detections */}
              {detections.length > 0 ? (
                <div>
                  <h2 className="font-bold text-gray-700 mb-2 text-sm uppercase tracking-wide">
                    Detected Materials ({detections.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {detections.map((d, i) => (
                      <DetectionCard key={i} detection={d} />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-700">
                  No waste items detected. Try a clearer photo with better lighting.
                </div>
              )}

              {/* Urgency */}
              {scan.urgency_score > 0 && (
                <div className="flex items-center space-x-3 bg-gray-50 rounded-xl p-3 border">
                  <span className="text-sm text-gray-600">Urgency Score:</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-orange-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(scan.urgency_score * 10, 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {scan.urgency_score.toFixed(2)}
                  </span>
                </div>
              )}
            </>
          )}

          {scan?.scan_status === "failed" && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              Processing failed: {scan.rag_response || "Unknown error"}
            </div>
          )}
        </div>
      </div>

      {/* Chat panel - full width below */}
      {isDone && scanId && (
        <div className="mt-8 bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center space-x-2 mb-4">
            <span className="text-2xl">🤖</span>
            <h2 className="text-lg font-bold text-gray-800">Eco Disposal Assistant</h2>
          </div>
          <ChatPanel
            scanId={scanId}
            initialAdvice={scan?.rag_response}
            initialSources={scan?.rag_sources}
          />
        </div>
      )}
    </div>
  );
}
