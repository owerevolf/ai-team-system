"""
Web UI v2 - Flask приложение с SSE и Session Management
"""

import os
import sys
import json
import uuid
import queue
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, session
from flask_cors import CORS
import threading

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.system_scanner import SystemScanner
from core.model_router import ModelRouter
from core.main import AITeamSystem
from core.zip_export import ZipExporter
from core.security_scanner import SecurityScanner

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", str(uuid.uuid4()))
CORS(app)

sessions = {}


class SessionManager:
    def __init__(self):
        self.active = {}
    
    def create(self, profile="medium"):
        session_id = str(uuid.uuid4())
        system = AITeamSystem(profile=profile)
        event_queue = queue.Queue()
        
        def on_event(event_type, data):
            event = {"type": event_type, "data": data, "time": datetime.now().isoformat()}
            event_queue.put(event)
        
        system.agent_manager.set_event_callback(on_event)
        
        self.active[session_id] = {
            "system": system,
            "events": event_queue,
            "created": datetime.now(),
            "status": "idle"
        }
        
        return session_id
    
    def get(self, session_id):
        return self.active.get(session_id)
    
    def get_events(self, session_id, timeout=0.1):
        sess = self.get(session_id)
        if not sess:
            return []
        
        events = []
        try:
            while True:
                event = sess["events"].get_nowait()
                events.append(event)
        except queue.Empty:
            pass
        
        return events
    
    def cleanup(self, session_id):
        if session_id in self.active:
            del self.active[session_id]


session_manager = SessionManager()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pipeline")
def pipeline():
    return render_template("pipeline.html")


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
    for p in sorted(projects_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_dir():
            projects.append({
                "name": p.name,
                "path": str(p),
                "created": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
            })
    
    return jsonify(projects)


@app.route("/api/session/create", methods=["POST"])
def create_session():
    data = request.json or {}
    profile = data.get("profile", "medium")
    
    session_id = session_manager.create(profile)
    
    return jsonify({
        "session_id": session_id,
        "status": "created"
    })


@app.route("/api/session/<session_id>/events")
def session_events(session_id):
    def generate():
        last_event_id = 0
        while True:
            events = session_manager.get_events(session_id)
            for i, event in enumerate(events):
                last_event_id += 1
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            sess = session_manager.get(session_id)
            if sess and sess["status"] == "completed":
                yield f"data: {json.dumps({'type': 'complete', 'data': {}, 'time': datetime.now().isoformat()})}\n\n"
                break
            
            import time
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route("/api/session/<session_id>/status")
def session_status(session_id):
    sess = session_manager.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "status": sess["status"],
        "created": sess["created"].isoformat(),
        "events_count": sess["events"].qsize()
    })


@app.route("/api/project/create", methods=["POST"])
def create_project():
    data = request.json
    project_name = data.get("name", "untitled")
    requirements = data.get("requirements", "")
    profile = data.get("profile", "medium")
    session_id = data.get("session_id")
    
    if session_id:
        sess = session_manager.get(session_id)
        if sess:
            sess["status"] = "running"
            
            def run_async():
                try:
                    sess["system"].run_full_pipeline(project_name, requirements)
                    sess["status"] = "completed"
                except Exception as e:
                    sess["status"] = "error"
                    sess["system"].agent_manager.emit_event("error", {"error": str(e)})
            
            thread = threading.Thread(target=run_async)
            thread.start()
            
            return jsonify({
                "status": "started",
                "session_id": session_id,
                "message": f"Проект {project_name} запущен"
            })
    
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


@app.route("/api/project/<path:project_name>/report")
def project_report(project_name):
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    report_file = project_path / "report.json"
    
    if not report_file.exists():
        return jsonify({"error": "Report not found"}), 404
    
    return jsonify(json.loads(report_file.read_text()))


@app.route("/api/project/<path:project_name>/export")
def project_export(project_name):
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        return jsonify({"error": "Project not found"}), 404
    
    exporter = ZipExporter(project_path)
    output_path = exporter.export()
    
    return jsonify({"path": str(output_path), "size_mb": exporter.get_size_info()["total_size_mb"]})


@app.route("/api/project/<path:project_name>/security")
def project_security(project_name):
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        return jsonify({"error": "Project not found"}), 404
    
    scanner = SecurityScanner(project_path)
    results = scanner.scan()
    
    return jsonify(results)


if __name__ == "__main__":
    print("🚀 AI Team System Web UI")
    print("   http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
