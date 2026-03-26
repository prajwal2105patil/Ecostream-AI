import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-10 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <span className="text-xl">♻️</span>
              <span className="text-white font-bold text-lg">EcoStream AI</span>
            </div>
            <p className="text-sm">
              Software-only smart waste management platform for Indian cities.
              Powered by Computer Vision, LLMs, and Predictive Analytics.
            </p>
          </div>
          <div>
            <h3 className="text-white font-semibold mb-3">Quick Links</h3>
            <ul className="space-y-1 text-sm">
              <li><Link to="/scan" className="hover:text-white">Scan Waste</Link></li>
              <li><Link to="/about" className="hover:text-white">About the Project</Link></li>
              <li><Link to="/dashboard" className="hover:text-white">Government Dashboard</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-white font-semibold mb-3">Technology</h3>
            <ul className="space-y-1 text-sm">
              <li>YOLOv11 Instance Segmentation</li>
              <li>LangChain + ChromaDB RAG</li>
              <li>Gaussian KDE Heatmaps</li>
              <li>FastAPI + PostgreSQL</li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-gray-800 text-center text-xs">
          © {new Date().getFullYear()} EcoStream AI — PCL Project, Jain University. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
