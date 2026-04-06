"""
Web UI - Flask приложение
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import threading

from core.system_scanner import SystemScanner
from core.model_router import ModelRouter
from core.main import AITeamSystem

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

system = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/report")
def report():
    return render_template("report.html")


@app.route("/api/system/info")
def system_info():
    scanner = SystemScanner()
    return jsonify(scanner.get_info())


@app.route("/api/models")
def models():
    router = ModelRouter()
    return jsonify(router.list_models())


@app.route("/api/profile/recommend")
def recommend_profile():
    scanner = SystemScanner()
    profile = scanner.recommend_profile()
    return jsonify({"profile": profile})


@app.route("/api/projects")
def list_projects():
    projects_dir = Path.home() / "projects"
    if not projects_dir.exists():
        return jsonify([])
    
    projects = []
    for p in projects_dir.iterdir():
        if p.is_dir():
            projects.append({
                "name": p.name,
                "path": str(p),
                "created": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
            })
    
    return jsonify(sorted(projects, key=lambda x: x["created"], reverse=True))


@app.route("/api/project/create", methods=["POST"])
def create_project():
    global system
    
    data = request.json
    project_name = data.get("name", "untitled")
    requirements = data.get("requirements", "")
    profile = data.get("profile", "medium")
    
    system = AITeamSystem(profile=profile)
    
    def run_async():
        try:
            system.run_full_pipeline(project_name, requirements)
        except Exception as e:
            print(f"Error: {e}")
    
    thread = threading.Thread(target=run_async)
    thread.start()
    
    return jsonify({
        "status": "started",
        "message": f"Проект {project_name} запущен"
    })


@app.route("/api/project/<path:project_name>/logs")
def project_logs(project_name):
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        return jsonify({"error": "Project not found"}), 404
    
    logs_dir = project_path / ".logs"
    if not logs_dir.exists():
        return jsonify([])
    
    logs = []
    for log_file in logs_dir.glob("*.log"):
        logs.append({
            "name": log_file.name,
            "content": log_file.read_text()
        })
    
    return jsonify(logs)


@app.route("/api/project/<path:project_name>/files")
def project_files(project_name):
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        return jsonify({"error": "Project not found"}), 404
    
    files = []
    for f in project_path.rglob("*"):
        if f.is_file():
            files.append(str(f.relative_to(project_path)))
    
    return jsonify(files)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
