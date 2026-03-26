import React, { useEffect, useRef } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

function HeatLayer({ points }) {
  const map = useMap();
  const layerRef = useRef(null);

  useEffect(() => {
    if (!L.heatLayer || !points?.length) return;
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }
    layerRef.current = L.heatLayer(points, {
      radius: 25,
      blur: 20,
      maxZoom: 17,
      gradient: { 0.2: "blue", 0.4: "lime", 0.6: "yellow", 0.8: "orange", 1.0: "red" },
    });
    layerRef.current.addTo(map);
    return () => {
      if (layerRef.current) map.removeLayer(layerRef.current);
    };
  }, [map, points]);

  return null;
}

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points?.length > 0) {
      const lats = points.map((p) => p[0]);
      const lons = points.map((p) => p[1]);
      map.fitBounds(
        [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]],
        { padding: [30, 30] }
      );
    }
  }, [map, points]);
  return null;
}

const CITY_CENTERS = {
  Bangalore: [12.9716, 77.5946],
  Delhi: [28.6139, 77.209],
  Mumbai: [19.076, 72.8777],
  Chennai: [13.0827, 80.2707],
};

export default function WasteHeatmap({ points = [], city = "Bangalore", loading }) {
  const center = CITY_CENTERS[city] || [12.9716, 77.5946];

  return (
    <div className="relative w-full h-96 rounded-2xl overflow-hidden border border-gray-200">
      {loading && (
        <div className="absolute inset-0 z-10 bg-white bg-opacity-70 flex items-center justify-center">
          <div className="text-sm text-gray-500">Loading heatmap...</div>
        </div>
      )}
      <MapContainer
        center={center}
        zoom={12}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.length > 0 && (
          <>
            <HeatLayer points={points} />
            <FitBounds points={points} />
          </>
        )}
      </MapContainer>
      {points.length === 0 && !loading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-white bg-opacity-80 text-gray-500 text-sm px-4 py-2 rounded-lg">
            No scan data for selected period
          </div>
        </div>
      )}
    </div>
  );
}
