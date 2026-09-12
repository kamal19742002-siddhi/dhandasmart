import os
import sys
import json
import csv
import shutil
import threading
import webbrowser
import socket
from datetime import datetime, date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

# Safe imports for Linux Server (Render)
try:
    from flask import Flask, request, session, redirect, url_for
except ImportError:
    Flask = None

try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, filedialog, ttk
except (ImportError, ModuleNotFoundError):
    tk = None
    messagebox = None
    simpledialog = None
    filedialog = None
    ttk = None

DATA_FILE = "dhanda_data.json"
VALID_STATUSES = ["New", "Contacted", "Follow-up", "Converted", "Lost"]
VALID_PRIORITIES = ["High", "Medium", "Low"]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            data.setdefault("business_name", "")
            data.setdefault("business_type", "")
            data.setdefault("leads", [])
            data.setdefault("audit", {})
            data.setdefault("content_history", [])
            data.setdefault("campaigns", [])
            for lead in data["leads"]:
                lead.setdefault("source", "Unknown")
                lead.setdefault("loan_amount", 0)
                lead.setdefault("priority", "Medium")
                lead.setdefault("notes", "")
                lead.setdefault("followup_date", "")
                lead.setdefault("date", datetime.now().strftime("%d-%m-%Y"))
                lead.setdefault("history", [])
                lead.setdefault("last_contacted", "")
            return data
        except Exception:
            pass
    return {
        "business_name": "",
        "business_type": "",
        "leads": [],
        "audit": {},
        "content_history": [],
        "campaigns": []
    }

data = load_data()

def save_data(current_data=None):
    target = current_data if current_data is not None else data
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(target, file, indent=4, ensure_ascii=False)

def normalize_status(status):
    if not status:
        return "New"
    status = str(status).strip().lower()
    mapping = {
        "new": "New", "contacted": "Contacted", "contact": "Contacted",
        "follow-up": "Follow-up", "follow up": "Follow-up", "followup": "Follow-up",
        "converted": "Converted", "convert": "Converted", "lost": "Lost"
    }
    return mapping.get(status, "New")

def normalize_priority(priority):
    if not priority:
        return "Medium"
    priority = str(priority).strip().lower()
    if priority == "high":
        return "High"
    if priority == "low":
        return "Low"
    return "Medium"

def safe_amount(value):
    try:
        value = str(value).replace(",", "").replace("₹", "").strip()
        return float(value)
    except Exception:
        return 0

def parse_followup_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%d-%m-%Y").date()
    except Exception:
        return None

def followup_category(value):
    d = parse_followup_date(value)
    if not d:
        return "No Date"
    today = date.today()
    if d < today:
        return "Overdue"
    elif d == today:
        return "Due Today"
    elif d <= today + timedelta(days=7):
        return "Upcoming"
    else:
        return "Future"

def lead_status_counts(leads=None):
    counts = {status: 0 for status in VALID_STATUSES}
    if leads is None:
        leads = data.get("leads", [])
    for lead in leads:
        status = normalize_status(lead.get("status"))
        if status in counts:
            counts[status] += 1
    return counts

def lead_pipeline_value(leads=None):
    total = 0
    if leads is None:
        leads = data.get("leads", [])
    for lead in leads:
        if normalize_status(lead.get("status")) in ["New", "Contacted", "Follow-up"]:
            total += safe_amount(lead.get("loan_amount", 0))
    return total

def converted_value(leads=None):
    total = 0
    if leads is None:
        leads = data.get("leads", [])
    for lead in leads:
        if normalize_status(lead.get("status")) == "Converted":
            total += safe_amount(lead.get("loan_amount", 0))
    return total

# =========================
# ONLINE DEMO WEB MODE (7 DAYS VALIDITY)
# =========================

def run_online_demo():
    if Flask is None:
        raise RuntimeError("Flask is not installed. Please add 'flask' to requirements.txt")

    app = Flask(__name__)
    app.secret_key = os.environ.get("DHANDASMART_SECRET_KEY", "change-this-demo-secret")
    demo_user = os.environ.get("DHANDASMART_DEMO_USER", "demo")
    demo_password = os.environ.get("DHANDASMART_DEMO_PASSWORD", "demo123")
    demo_data_file = os.environ.get("DHANDASMART_DATA_FILE", "demo_data.json")

    TRIAL_DAYS = 7

    def demo_load():
        nonlocal demo_data_file
        d = {}
        if os.path.exists(demo_data_file):
            try:
                with open(demo_data_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                d = {}

        if "trial_start_date" not in d:
            d["trial_start_date"] = datetime.now().strftime("%Y-%m-%d")

        d.setdefault("business_name", "DhandaSmart Demo")
        d.setdefault("business_type", "Demo Business")
        d.setdefault("leads", [
            {"name":"Rahul Sharma","phone":"98XXXXXX01","service":"Home Loan","status":"New","priority":"High","source":"Website","loan_amount":2500000,"followup_date":"","notes":"Demo lead","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""},
            {"name":"Amit Verma","phone":"98XXXXXX02","service":"Business Loan","status":"Follow-up","priority":"Medium","source":"Referral","loan_amount":1200000,"followup_date":"","notes":"Demo follow-up","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""},
            {"name":"Neha Gupta","phone":"98XXXXXX03","service":"Insurance","status":"Converted","priority":"Low","source":"Facebook","loan_amount":750000,"followup_date":"","notes":"Demo converted lead","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""}
        ])
        d.setdefault("audit", {})
        d.setdefault("content_history", [])
        d.setdefault("campaigns", [])

        for lead in d["leads"]:
            lead.setdefault("source", "Demo")
            lead.setdefault("loan_amount", 0)
            lead.setdefault("priority", "Medium")
            lead.setdefault("notes", "")
            lead.setdefault("followup_date", "")
            lead.setdefault("date", datetime.now().strftime("%d-%m-%Y"))
            lead.setdefault("history", [])
            lead.setdefault("last_contacted", "")
        return d

    def demo_save(d):
        with open(demo_data_file, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4, ensure_ascii=False)

    def check_validity():
        d = demo_load()
        start_str = d.get("trial_start_date", datetime.now().strftime("%Y-%m-%d"))
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except Exception:
            start_date = date.today()

        days_passed = (date.today() - start_date).days
        days_left = max(0, TRIAL_DAYS - days_passed)
        is_expired = days_passed >= TRIAL_DAYS
        return is_expired, days_left

    def expired_html():
        return """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
        <title>Demo Expired</title><style>body{font-family:Arial;background:#f8fafc;margin:0;display:grid;place-items:center;min-height:100vh;color:#1e293b}.box{background:#fff;padding:36px;border-radius:14px;width:min(90%,420px);box-shadow:0 10px 30px rgba(0,0,0,0.08);text-align:center}h1{color:#dc2626;margin:0 0 10px}p{color:#64748b;line-height:1.5}.badge{background:#fee2e2;color:#991b1b;padding:6px 12px;border-radius:20px;font-size:13px;font-weight:bold;display:inline-block;margin-bottom:15px}.btn{display:inline-block;margin-top:20px;background:#16a34a;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold}</style></head>
        <body><div class='box'><span class='badge'>TRIAL PERIOD ENDED</span><h1>Demo Access Expired</h1><p>Aapka 7-day free demo period complete ho chuka hai.<br>Full software access ke liye contact karein.</p><a class='btn' href='https://wa.me/91XXXXXXXXXX?text=Hi%2C%20I%20want%20to%20buy%20DhandaSmart' target='_blank'>Contact on WhatsApp</a></div></body></html>"""

    def login_required():
        return session.get("demo_logged_in") is True

    @app.route("/login", methods=["GET", "POST"])
    def login():
        is_expired, _ = check_validity()
        if is_expired:
            return expired_html()

        error = ""
        if request.method == "POST":
            if request.form.get("username", "") == demo_user and request.form.get("password", "") == demo_password:
                session["demo_logged_in"] = True
                return redirect(url_for("home"))
            error = "Invalid demo login"
        error_html = f"<div class='err'>{error}</div>" if error else ""
        return f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
        <title>DhandaSmart Demo Login</title><style>body{{font-family:Arial;background:#eef2f7;margin:0;display:grid;place-items:center;min-height:100vh}}.box{{background:#fff;padding:28px;border-radius:14px;width:min(90%,360px);box-shadow:0 8px 30px #0001}}h1{{margin:0 0 6px}}p{{color:#64748b}}input,button{{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:8px;border:1px solid #cbd5e1;font-size:16px}}button{{background:#172033;color:white;font-weight:bold;cursor:pointer}}.err{{color:#b91c1c}}</style></head><body><div class='box'><h1>DHANDASMART</h1><p>Secure Demo Login (7 Days Free Trial)</p>{error_html}<form method='post'><input name='username' placeholder='Demo username' required><input name='password' type='password' placeholder='Password' required><button>LOGIN TO DEMO</button></form></div></body></html>"""

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/", methods=["GET"])
    def home():
        is_expired, days_left = check_validity()
        if is_expired:
            return expired_html()

        if not login_required():
            return redirect(url_for("login"))

        d = demo_load()
        leads = d.get("leads", [])
        active = sum(1 for x in leads if normalize_status(x.get("status")) not in ("Converted", "Lost"))
        converted = sum(1 for x in leads if normalize_status(x.get("status")) == "Converted")
        conversion = converted / len(leads) * 100 if leads else 0
        pipeline = sum(safe_amount(x.get("loan_amount", 0)) for x in leads if normalize_status(x.get("status")) in ("New","Contacted","Follow-up"))
        rows = "".join(f"<tr><td>{str(x.get('name',''))}</td><td>{str(x.get('phone',''))}</td><td>{str(x.get('service',''))}</td><td>{normalize_status(x.get('status'))}</td><td>{normalize_priority(x.get('priority'))}</td><td>₹{safe_amount(x.get('loan_amount',0)):,.0f}</td><td>{str(x.get('followup_date',''))}</td></tr>" for x in leads)
        
        trial_banner = f"<div style='background:#fef3c7;color:#92400e;padding:10px 14px;border-radius:8px;margin-bottom:14px;font-weight:bold;display:flex;justify-content:space-between;'><span>⏳ Demo Trial Active</span><span>{days_left} Days Remaining</span></div>"

        html = f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>DhandaSmart Demo</title><style>
        *{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:#eef2f7;color:#111827}}header{{background:#172033;color:white;padding:18px}}.wrap{{max-width:1100px;margin:auto;padding:0 14px}}header h1{{margin:0;font-size:24px}}header p{{margin:4px 0 0;color:#cbd5e1}}.top{{display:flex;justify-content:space-between;align-items:center;gap:10px}}a{{color:inherit}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding-top:10px}}.card,.section{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px}}.value{{font-size:23px;font-weight:bold;margin-top:5px}}.label{{font-size:11px;color:#64748b;font-weight:bold}}.section{{margin-top:16px}}.tablebox{{overflow-x:auto}}table{{width:100%;min-width:760px;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #e2e8f0;text-align:left;font-size:13px}}th{{background:#f8fafc}}form{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}input,select,textarea,button{{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:7px;font:inherit}}textarea{{min-height:80px}}.full{{grid-column:1/-1}}button{{background:#172033;color:white;font-weight:bold;border:0}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}form{{grid-template-columns:1fr}}.full{{grid-column:auto}}header h1{{font-size:21px}}}}
        </style></head><body><header><div class='wrap top'><div><h1>DHANDASMART</h1><p>Manage. Market. Grow. — DEMO</p></div><a href='/logout'>Logout</a></div></header><main class='wrap' style='padding-top:14px;'>{trial_banner}<div class='grid'><div class='card'><div class='label'>TOTAL LEADS</div><div class='value'>{len(leads)}</div></div><div class='card'><div class='label'>ACTIVE LEADS</div><div class='value'>{active}</div></div><div class='card'><div class='label'>CONVERSION</div><div class='value'>{conversion:.1f}%</div></div><div class='card'><div class='label'>PIPELINE</div><div class='value'>₹{pipeline:,.0f}</div></div></div><div class='section'><h2>📊 Lead CRM</h2><div class='tablebox'><table><thead><tr><th>Name</th><th>Phone</th><th>Service</th><th>Status</th><th>Priority</th><th>Amount</th><th>Follow-up</th></tr></thead><tbody>{rows}</tbody></table></div></div><div class='section'><h2>➕ Add New Demo Lead</h2><form method='post' action='/add'><input name='name' placeholder='Customer name' required><input name='phone' placeholder='Phone'><input name='service' placeholder='Interested service'><select name='status'><option>New</option><option>Contacted</option><option>Follow-up</option><option>Converted</option><option>Lost</option></select><select name='priority'><option>High</option><option selected>Medium</option><option>Low</option></select><input name='source' placeholder='Lead source'><input name='amount' placeholder='Expected amount'><input name='followup_date' placeholder='Follow-up DD-MM-YYYY'><textarea class='full' name='notes' placeholder='Notes'></textarea><button class='full'>SAVE DEMO LEAD</button></form></div></main></body></html>"""
        return html

    @app.route("/add", methods=["POST"])
    def add():
        is_expired, _ = check_validity()
        if is_expired:
            return expired_html()

        if not login_required():
            return redirect(url_for("login"))
        d = demo_load()
        form = request.form
        d.setdefault("leads", []).append({
            "name": form.get("name", "").strip(), "phone": form.get("phone", "").strip(),
            "service": form.get("service", "").strip(), "status": normalize_status(form.get("status", "New")),
            "priority": normalize_priority(form.get("priority", "Medium")), "source": form.get("source", "Demo").strip() or "Demo",
            "loan_amount": safe_amount(form.get("amount", "0")), "followup_date": form.get("followup_date", "").strip(),
            "notes": form.get("notes", "").strip(), "date": datetime.now().strftime("%d-%m-%Y"), "history": [], "last_contacted": ""
        })
        demo_save(d)
        return redirect(url_for("home"))

    demo_save(demo_load())
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)

# Entry point logic
if __name__ == "__main__":
    if "--web-demo" in sys.argv:
        run_online_demo()
        sys.exit(0)

    # Local desktop UI (fallback)
    if tk is None:
        print("Tkinter is not supported in this environment. Run with --web-demo for Flask web mode.")
        sys.exit(1)
