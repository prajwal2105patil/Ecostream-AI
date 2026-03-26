#!/usr/bin/env python3
"""
EcoStream AI Read-Only Auditor Agent
100% READ-ONLY — Generates report only
Never modifies any file or code
March 2026 best practices
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

class EcoStreamReadOnlyAuditor:
    def __init__(self):
        self.root = Path.cwd()
        self.claude_md = self.root / "CLAUDE.md"
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "audit_type": "READ-ONLY",
            "missing_components": [],
            "rule_violations": [],
            "senior_ieee_reviewer_perspective": [],
            "r13_status": "Not yet run (will be checked if files exist)"
        }

    def _load_claude_md(self):
        if not self.claude_md.exists():
            self.report["missing_components"].append("CLAUDE.md is missing at root — critical violation")
            return {}
        return self.claude_md.read_text(encoding="utf-8")

    def _scan_repo(self):
        """Pure read-only scan"""
        files = {
            "vision": list(self.root.glob("ai-models/vision/*.py")),
            "rag": list(self.root.glob("ai-models/rag/*.py")),
            "backend": list(self.root.glob("backend/**/*.py")),
            "frontend": list(self.root.glob("frontend/**/*.jsx")) + list(self.root.glob("frontend/**/*.tsx"))
        }
        return files

    def _check_missing_components(self):
        content = self._load_claude_md()
        
        # R1 — Mock check
        if "mock" not in content.lower() or not any(f.name.startswith("mock") for f in self.root.glob("**/*mock*.py")):
            self.report["missing_components"].append("R1: Missing committed mock responses for YOLO output and /scan endpoint")

        # R8 — Instance segmentation
        vision_files = self._scan_repo()["vision"]
        if vision_files and not any("seg" in f.name.lower() for f in vision_files):
            self.report["missing_components"].append("R8: No YOLOv11-seg files detected — only classification may be present")

        # R4 — RAG fallback
        rag_chain = self.root / "ai-models/rag/rag_chain.py"
        if rag_chain.exists():
            text = rag_chain.read_text()
            if "0.65" not in text and "similarity" in text.lower():
                self.report["missing_components"].append("R4: rag_chain.py missing hardcoded fallback for similarity < 0.65")

        # R13 — Iteration readiness
        if not any("r13" in f.name.lower() or "iteration" in f.name.lower() for f in self.root.glob("**/*.py")):
            self.report["missing_components"].append("R13: No files implementing iterative problem detection & logging yet")

    def _check_rule_violations(self):
        # Simple read-only checks for obvious violations
        for py_file in self.root.rglob("*.py"):
            text = py_file.read_text(errors="ignore")
            if "gamification" in text.lower() or "notification" in text.lower() or "profile" in text.lower():
                self.report["rule_violations"].append(f"R2 violation in {py_file.relative_to(self.root)} — scope creep detected")

    def _generate_senior_reviewer_perspective(self):
        """Another person's (Senior IEEE Reviewer) unbiased view"""
        perspectives = []
        for issue in self.report["missing_components"]:
            perspectives.append({
                "issue": issue,
                "external_perspective": f"From a senior IEEE reviewer standpoint: This missing component weakens the novelty claim around clustered Indian waste handling. Adding it would directly support a stronger ablation study in the Results section and improve publication chances."
            })
        for violation in self.report["rule_violations"]:
            perspectives.append({
                "issue": violation,
                "external_perspective": "From a senior IEEE reviewer standpoint: This violates the strict three-engine scope (R2). It risks diluting the publication focus — recommend immediate removal to keep the paper clean and focused."
            })
        self.report["senior_ieee_reviewer_perspective"] = perspectives

    def run(self):
        print("🚀 EcoStream AI Read-Only Auditor started")
        print("   → 100% read-only | No changes made to any code")
        
        self._check_missing_components()
        self._check_rule_violations()
        self._generate_senior_reviewer_perspective()

        # Save report (only file ever written)
        report_path = self.root / f"research/auditor_report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        print(f"\n✅ Report generated — {len(self.report['missing_components'])} missing components found")
        print(f"📄 Saved to: {report_path.name}")
        print("\n📋 Senior IEEE Reviewer Perspectives included for publication insight.")

if __name__ == "__main__":
    auditor = EcoStreamReadOnlyAuditor()
    auditor.run()