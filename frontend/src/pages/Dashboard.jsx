import { useState, useEffect, Component } from "react";
import { useAuth } from "../context/AuthContext";
import WasteHeatmap from "../components/dashboard/WasteHeatmap";
import TrendChart from "../components/dashboard/TrendChart";
import CategoryPieChart from "../components/dashboard/CategoryPieChart";
import HotspotTable from "../components/dashboard/HotspotTable";
import RouteDisplay from "../components/dashboard/RouteDisplay";
import { getHeatmapData, getHeatmapSummary } from "../api/heatmapApi";
import { getTrends, getCategories, getHotspots } from "../api/analyticsApi";

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, msg: "" }; }
  static getDerivedStateFromError(e) { return { hasError: true, msg: e.message }; }
  render() {
    if (this.state.hasError)
      return <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-red-600 text-sm">Failed to load: {this.state.msg}</div>;
    return this.props.children;
  }
}

const CITIES = ["Bangalore", "Delhi", "Mumbai", "Chennai"];

export default function Dashboard() {
  const { user } = useAuth();
  const [city, setCity] = useState(user?.city || "Bangalore");
  const [days, setDays] = useState(7);

  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [categories, setCategories] = useState([]);
  const [hotspots, setHotspots] = useState([]);

  const [loadingHeatmap, setLoadingHeatmap] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  async function fetchData() {
    setLoadingHeatmap(true);
    setLoadingAnalytics(true);
    try {
      const [hm, sum] = await Promise.all([
        getHeatmapData(city, days),
        getHeatmapSummary(city, days),
      ]);
      setHeatmapPoints(hm.points || []);
      setSummary(sum);
    } catch {}
    setLoadingHeatmap(false);

    try {
      const [t, c, h] = await Promise.all([
        getTrends(city, days),
        getCategories(days),
        getHotspots(city),
      ]);
      setTrends(t);
      setCategories(c);
      setHotspots(h);
    } catch {}
    setLoadingAnalytics(false);
  }

  useEffect(() => {
    fetchData();
  }, [city, days]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Government Command Center</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time waste intelligence for {city}</p>
        </div>
        {/* Controls */}
        <div className="flex items-center space-x-3">
          <select
            value={city}
            onChange={(e) => {
              setHeatmapPoints([]);
              setSummary(null);
              setCity(e.target.value);
            }}
            className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
          >
            {CITIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <select
            value={days}
            onChange={(e) => {
              setHeatmapPoints([]);
              setSummary(null);
              setDays(Number(e.target.value));
            }}
            className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
          >
            <option value={1}>Last 24h</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <button
            onClick={fetchData}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats row */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Scans", value: summary.total_scans, icon: "📷" },
            { label: "Avg Urgency", value: summary.avg_urgency?.toFixed(2), icon: "⚡" },
            { label: "Hotspot Wards", value: hotspots.filter(h => h.urgency_level === "high" || h.urgency_level === "critical").length, icon: "🔥" },
            { label: "Days Analyzed", value: days, icon: "📅" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 text-center">
              <div className="text-2xl mb-1">{s.icon}</div>
              <div className="text-2xl font-extrabold text-gray-800">{s.value ?? "—"}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Heatmap */}
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-700 mb-3">Waste Density Heatmap</h2>
        <ErrorBoundary>
          <WasteHeatmap points={heatmapPoints} city={city} loading={loadingHeatmap} />
        </ErrorBoundary>
        <p className="text-xs text-gray-400 mt-2">
          Heatmap uses weighted Gaussian KDE with time decay. Red = high urgency accumulation.
        </p>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <ErrorBoundary><TrendChart data={trends} title={`Daily Scans — ${city}`} /></ErrorBoundary>
        <ErrorBoundary><CategoryPieChart data={categories} title="Waste Category Distribution" /></ErrorBoundary>
      </div>

      {/* Hotspots + Route */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ErrorBoundary><HotspotTable hotspots={hotspots} loading={loadingAnalytics} /></ErrorBoundary>
        <ErrorBoundary><RouteDisplay city={city} /></ErrorBoundary>
      </div>
    </div>
  );
}
