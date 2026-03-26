import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const features = [
  {
    icon: "👁️",
    title: "Vision Engine",
    desc: "YOLOv11 instance segmentation identifies 20 Indian waste types — even in cluttered, mixed-waste scenarios.",
  },
  {
    icon: "🧠",
    title: "AI Disposal Expert",
    desc: "LLM powered by RAG answers complex questions about recycling laws, bin types, and disposal facilities in your city.",
  },
  {
    icon: "🗺️",
    title: "Waste Heatmaps",
    desc: "Gaussian KDE heatmaps show municipalities exactly where waste is accumulating in real-time.",
  },
  {
    icon: "🚛",
    title: "Smart Routing",
    desc: "ML-predicted hotspots feed a greedy route optimizer — reducing truck fuel consumption by up to 20%.",
  },
];

export default function Home() {
  const { user } = useAuth();

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-green-800 to-green-600 text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="text-6xl mb-4">♻️</div>
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 leading-tight">
            AI-Powered Waste Intelligence
            <br />
            <span className="text-green-200">for Smart Indian Cities</span>
          </h1>
          <p className="text-lg text-green-100 mb-8 max-w-2xl mx-auto">
            EcoStream AI replaces expensive IoT sensors with mobile Computer Vision and
            LLMs — giving citizens instant recycling guidance and municipalities
            data-driven collection routes.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/scan"
              className="bg-white text-green-800 font-bold px-8 py-3 rounded-xl hover:bg-green-50 text-lg transition-colors shadow-lg"
            >
              Scan Waste Now →
            </Link>
            {user?.role === "admin" || user?.role === "government" ? (
              <Link
                to="/dashboard"
                className="border-2 border-white text-white px-8 py-3 rounded-xl hover:bg-green-700 text-lg transition-colors"
              >
                Open Dashboard
              </Link>
            ) : (
              <Link
                to="/login"
                className="border-2 border-white text-white px-8 py-3 rounded-xl hover:bg-green-700 text-lg transition-colors"
              >
                Government Login
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="bg-green-900 text-white py-6">
        <div className="max-w-5xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { n: "20", label: "Waste Classes" },
            { n: "3", label: "AI Engines" },
            { n: "4", label: "Indian Cities" },
            { n: "100%", label: "Software-Only" },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-3xl font-extrabold text-green-300">{s.n}</div>
              <div className="text-sm text-green-200">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-10">
            Three-Engine Architecture
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((f) => (
              <div
                key={f.title}
                className="flex space-x-4 p-6 bg-gray-50 rounded-2xl border border-gray-100 hover:shadow-md transition-shadow"
              >
                <div className="text-4xl flex-shrink-0">{f.icon}</div>
                <div>
                  <h3 className="font-bold text-lg text-gray-800 mb-1">{f.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-800 mb-12">How It Works</h2>
          <div className="flex flex-col md:flex-row items-center justify-center gap-4">
            {[
              { step: "1", label: "Upload photo of waste" },
              { step: "→", label: "" },
              { step: "2", label: "AI identifies all materials" },
              { step: "→", label: "" },
              { step: "3", label: "Get disposal instructions" },
              { step: "→", label: "" },
              { step: "4", label: "Data feeds city heatmap" },
            ].map((s, i) =>
              s.step === "→" ? (
                <div key={i} className="text-green-500 font-bold text-2xl hidden md:block">→</div>
              ) : (
                <div key={i} className="flex flex-col items-center p-6 bg-white rounded-2xl shadow-sm w-36">
                  <div className="w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold mb-2">
                    {s.step}
                  </div>
                  <p className="text-sm text-gray-600 text-center">{s.label}</p>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-green-700 text-white text-center">
        <h2 className="text-2xl font-bold mb-4">Ready to make smarter waste decisions?</h2>
        <Link
          to="/scan"
          className="inline-block bg-white text-green-800 font-bold px-10 py-3 rounded-xl hover:bg-green-50 text-lg"
        >
          Start Scanning →
        </Link>
      </section>
    </div>
  );
}
