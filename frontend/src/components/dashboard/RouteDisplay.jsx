import React, { useState } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { generateRoute } from "../../api/analyticsApi";

const CITY_CENTERS = {
  Bangalore: [12.9716, 77.5946],
  Delhi: [28.6139, 77.209],
  Mumbai: [19.076, 72.8777],
};

export default function RouteDisplay({ city = "Bangalore" }) {
  const [route, setRoute] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    setGenerating(true);
    setError("");
    try {
      const today = new Date().toISOString().slice(0, 10);
      const result = await generateRoute(city, today);
      setRoute(result);
    } catch (err) {
      setError("Failed to generate route");
    } finally {
      setGenerating(false);
    }
  }

  const center = CITY_CENTERS[city] || [12.9716, 77.5946];
  const positions = route?.waypoints?.map((w) => [w.lat, w.lon]) || [];

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-gray-700">Smart Truck Route</h3>
          {route && (
            <p className="text-xs text-gray-400 mt-0.5">
              {route.total_distance_km?.toFixed(1)} km · ~{route.estimated_duration_min} min · {route.waypoints?.length} stops
            </p>
          )}
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-xl disabled:opacity-50 font-medium"
        >
          {generating ? "Generating..." : "Generate Route"}
        </button>
      </div>
      {error && <div className="px-5 py-2 text-red-500 text-sm">{error}</div>}
      <div className="h-72">
        <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {positions.length > 1 && (
            <Polyline positions={positions} color="#16a34a" weight={3} dashArray="8 4" />
          )}
          {route?.waypoints?.map((w, i) => (
            <Marker key={i} position={[w.lat, w.lon]}>
              <Popup>
                Stop #{i + 1}<br />
                Ward: {w.address || "—"}<br />
                Priority: {w.priority}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
