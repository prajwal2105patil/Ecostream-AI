import React from "react";

const team = [
  {
    emoji: "👁️",
    role: "Member 1 — AI/Vision Lead",
    name: "The Eyes",
    focus: "YOLOv11-seg model training, Indian waste dataset curation, mask overlay generation, GAN synthetic data",
    tools: "Python · PyTorch · Ultralytics · OpenCV · Roboflow",
  },
  {
    emoji: "🧠",
    role: "Member 2 — LLM & NLP Lead",
    name: "The Expert",
    focus: "RAG pipeline, ChromaDB vector store, LangChain, Indian municipal law ingestion, prompt engineering",
    tools: "LangChain · ChromaDB · HuggingFace · OpenAI · sentence-transformers",
  },
  {
    emoji: "🦴",
    role: "Member 3 — Backend Architect",
    name: "The Spine",
    focus: "FastAPI, PostgreSQL schema, async scan pipeline, Docker Compose, JWT authentication",
    tools: "FastAPI · SQLAlchemy · Alembic · PostgreSQL · Docker",
  },
  {
    emoji: "📱",
    role: "Member 4 — Frontend Developer",
    name: "The Face",
    focus: "React.js web app, Tailwind UI, Leaflet heatmaps, Recharts, image canvas overlays, SSE streaming",
    tools: "React 19 · Vite · Tailwind 4 · Recharts · React-Leaflet",
  },
  {
    emoji: "📊",
    role: "Member 5 — Research & Analytics",
    name: "The Scientist",
    focus: "Literature review (30 papers), Gaussian KDE heatmap, GradientBoosting hotspot predictor, IEEE paper",
    tools: "Scikit-learn · SciPy · LaTeX · Pandas · Matplotlib",
  },
];

const techStack = [
  { category: "AI / Vision", items: ["YOLOv11-seg", "PyTorch", "OpenCV", "Albumentations"] },
  { category: "LLM / RAG", items: ["LangChain", "ChromaDB", "HuggingFace", "OpenAI API / Ollama"] },
  { category: "Backend", items: ["FastAPI", "PostgreSQL", "SQLAlchemy", "Docker"] },
  { category: "Frontend", items: ["React 19", "Vite", "Tailwind CSS 4", "Recharts", "React-Leaflet"] },
  { category: "Analytics", items: ["Scikit-learn", "SciPy KDE", "Pandas", "Gaussian Processes"] },
];

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <span className="text-5xl">♻️</span>
        <h1 className="text-4xl font-extrabold text-gray-800 mt-3 mb-3">About EcoStream AI</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          A 12-week PCL (Project Centric Learning) project by 5 software engineers at Jain University.
          A software-only approach to India's urban waste management crisis.
        </p>
      </div>

      {/* Concept */}
      <section className="bg-green-50 rounded-2xl p-8 mb-10 border border-green-100">
        <h2 className="text-2xl font-bold text-green-800 mb-3">The Core Idea</h2>
        <p className="text-gray-700 leading-relaxed">
          <strong>EcoStream AI</strong> replaces expensive IoT "Smart Bins" with a{" "}
          <em>Software-as-a-Sensor</em> model. Using smartphones already in citizens' pockets,
          we classify mixed Indian waste via <strong>Computer Vision</strong> (YOLOv11 instance segmentation),
          provide context-aware disposal advice through an <strong>LLM + RAG pipeline</strong> grounded in
          Indian municipal laws, and generate <strong>predictive heatmaps</strong> to help municipalities
          optimize truck collection routes.
        </p>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center text-sm">
          {[
            { label: "Zero Hardware Cost", icon: "💰" },
            { label: "Indian Context-Aware AI", icon: "🇮🇳" },
            { label: "Publication-Ready Research", icon: "📄" },
          ].map((x) => (
            <div key={x.label} className="bg-white rounded-xl p-4 shadow-sm">
              <div className="text-2xl mb-1">{x.icon}</div>
              <div className="font-semibold text-gray-700">{x.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Team */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">The Team</h2>
        <div className="space-y-4">
          {team.map((m) => (
            <div key={m.role} className="flex space-x-4 p-5 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <div className="text-3xl">{m.emoji}</div>
              <div>
                <div className="font-bold text-gray-800">{m.role}</div>
                <div className="text-green-700 font-medium text-sm mb-1">{m.name}</div>
                <p className="text-gray-600 text-sm mb-1">{m.focus}</p>
                <p className="text-xs text-gray-400">{m.tools}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="mb-10">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Technology Stack</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {techStack.map((t) => (
            <div key={t.category} className="bg-gray-50 rounded-xl p-4 border border-gray-100">
              <h3 className="font-semibold text-gray-700 mb-2">{t.category}</h3>
              <ul className="space-y-1">
                {t.items.map((item) => (
                  <li key={item} className="text-sm text-gray-600 flex items-center space-x-1">
                    <span className="text-green-500">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* IEEE Paper */}
      <section className="bg-blue-50 rounded-2xl p-8 border border-blue-100">
        <h2 className="text-2xl font-bold text-blue-800 mb-3">IEEE Research Paper</h2>
        <p className="text-gray-700 mb-4 text-sm">
          This project culminates in an 8-page IEEE format research paper analyzing 20–30 existing
          studies and presenting our novel contribution: a software-only framework for mixed
          Indian waste classification using LLM-RAG and YOLOv11 instance segmentation.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          {[
            "Abstract: Software-only approach with key results",
            "Introduction: Global waste crisis & India's challenge",
            "Literature Review: 25+ papers, gap analysis",
            "Methodology: Vision + RAG + Analytics pipeline",
            "Results: mAP, F1 scores, LLM accuracy metrics",
            "Conclusion: Scalability without hardware costs",
          ].map((s) => (
            <div key={s} className="flex items-start space-x-2 text-gray-700">
              <span className="text-blue-500 mt-0.5">📋</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
