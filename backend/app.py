"""
Flask server. Exposes the grade engine as a JSON API and serves the UI.

The server does NO grade logic. It validates shape, calls grade_engine.calculate,
and returns the result. Grading rules live in grade_engine.py only.

Routes
------
GET  /                     -> UI
POST /api/calculate        -> { policy } -> engine result
GET  /api/sample           -> the CCSC:MW 2026 sample policy as JSON
POST /api/save             -> { name, policy } -> saves to ./saved/<name>.json
GET  /api/saved            -> list of saved policy names
GET  /api/saved/<name>     -> load a saved policy
"""

import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from grade_engine import calculate

app = Flask(__name__)
SAVE_DIR = Path(__file__).parent / "saved"
SAVE_DIR.mkdir(exist_ok=True)

SAMPLE_POLICY = {
    "course_name": "Sample Course (CCSC:MW)",
    "categories": [
        {
            "name": "Quizzes", "weight": 15, "drop_lowest": 1, "drop_min_scores": 2,
            "curve_above": 90, "curve_to": 100,
            "items": [
                {"name": "Quiz 1", "score": 80, "status": "scored"},
                {"name": "Quiz 2", "score": 92, "status": "scored"},
                {"name": "Quiz 3", "score": 70, "status": "scored"},
                {"name": "Quiz 4", "score": None, "status": "pending"},
            ],
        },
        {
            "name": "Homework", "weight": 15, "drop_lowest": 2, "drop_min_scores": 3,
            "curve_above": None, "curve_to": None,
            "items": [
                {"name": "HW 1", "score": 100, "status": "scored"},
                {"name": "HW 2", "score": 90, "status": "scored"},
                {"name": "HW 3", "score": 80, "status": "scored"},
                {"name": "HW 4", "score": 50, "status": "scored"},
            ],
        },
        {
            "name": "Exams", "weight": 40, "drop_lowest": 0, "drop_min_scores": 0,
            "curve_above": None, "curve_to": None,
            "items": [
                {"name": "Exam 1", "score": 78, "status": "scored"},
                {"name": "Exam 2", "score": 88, "status": "scored"},
            ],
        },
        {
            "name": "Final", "weight": 25, "drop_lowest": 0, "drop_min_scores": 0,
            "curve_above": None, "curve_to": None,
            "items": [{"name": "Final Exam", "score": None, "status": "pending"}],
        },
    ],
    "attendance": {
        "weight": 5, "drop_fraction": 0.05,
        "marks": ["present"] * 19 + ["absent"],
    },
    "letter_cutoffs": {"A": 90, "B": 80, "C": 70, "D": 60},
    "final_category": "Final",
    "final_replaces": "Exams",
}


from validation import validate_policy as _validate_policy


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict): return jsonify(error="A policy object is required."),400
    policy = body.get("policy")
    try:
        _validate_policy(policy)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    try:
        return jsonify(calculate(policy))
    except Exception as e:  # safety net; surface the message to the UI
        return jsonify({"error": f"calculation failed: {e}"}), 500


@app.route("/api/sample")
def api_sample():
    return jsonify(SAMPLE_POLICY)


_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _safe_name(name):
    name = _SAFE.sub("_", (name or "").strip())
    return name[:64] or "untitled"


@app.route("/api/save", methods=["POST"])
def api_save():
    body = request.get_json(silent=True) or {}
    name = _safe_name(body.get("name") or body.get("policy", {}).get("course_name", "untitled"))
    policy = body.get("policy")
    try:
        _validate_policy(policy)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    path = SAVE_DIR / f"{name}.json"
    path.write_text(json.dumps(policy, indent=2))
    return jsonify({"name": name, "saved": True})


@app.route("/api/saved")
def api_list_saved():
    files = sorted(p.stem for p in SAVE_DIR.glob("*.json"))
    return jsonify({"saved": files})


@app.route("/api/saved/<name>")
def api_load_saved(name):
    name = _safe_name(name)
    path = SAVE_DIR / f"{name}.json"
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(path.read_text()))


@app.route("/api/saved/<name>", methods=["DELETE"])
def api_delete_saved(name):
    name = _safe_name(name)
    path = SAVE_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
    return jsonify({"deleted": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
