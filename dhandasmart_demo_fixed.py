try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, filedialog, ttk
except (ImportError, ModuleNotFoundError):
    tk = None
    messagebox = None
    simpledialog = None
    filedialog = None
    ttk = None

import json
import os
import csv
import shutil
import threading
import webbrowser
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import sys

try:
    from flask import Flask, request, session, redirect, url_for
except ImportError:
    Flask = None
from datetime import datetime, date, timedelta

DATA_FILE = "dhanda_data.json"

VALID_STATUSES = [
    "New",
    "Contacted",
    "Follow-up",
    "Converted",
    "Lost"
]

VALID_PRIORITIES = ["High", "Medium", "Low"]


# =========================
# DATA STORAGE
# =========================

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

            # Upgrade old leads automatically
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
        except:
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


# =========================
# HELPERS
# =========================

def normalize_status(status):
    if not status:
        return "New"

    status = str(status).strip().lower()

    mapping = {
        "new": "New",
        "contacted": "Contacted",
        "contact": "Contacted",
        "follow-up": "Follow-up",
        "follow up": "Follow-up",
        "followup": "Follow-up",
        "converted": "Converted",
        "convert": "Converted",
        "lost": "Lost"
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
    except:
        return 0


def parse_followup_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(
            str(value).strip(),
            "%d-%m-%Y"
        ).date()
    except:
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
        if normalize_status(lead.get("status")) in [
            "New", "Contacted", "Follow-up"
        ]:
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
# DHANDASMART V5 - DEMO + PC/MOBILE WEB APP
# =========================

WEB_SERVER = None
WEB_PORT = 8765


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def maximize_for_screen(win):
    """Make major application windows use the available screen safely."""
    try:
        if os.name == "nt":
            win.state("zoomed")
    except Exception:
        pass


def product_demo():
    win = tk.Toplevel(root)
    win.title("DhandaSmart - Product Demo")
    win.geometry("900x680")
    win.minsize(760, 580)
    maximize_for_screen(win)

    header = tk.Frame(win, bg="#172033", padx=24, pady=20)
    header.pack(fill="x")
    tk.Label(header, text="DHANDASMART", font=("Segoe UI", 25, "bold"),
             fg="white", bg="#172033").pack(anchor="w")
    tk.Label(header, text="Manage. Market. Grow.", font=("Segoe UI", 11),
             fg="#cbd5e1", bg="#172033").pack(anchor="w", pady=(3, 0))

    body = tk.Frame(win, bg="#eef2f7", padx=18, pady=18)
    body.pack(fill="both", expand=True)

    tk.Label(body, text="ALL-IN-ONE BUSINESS GROWTH SYSTEM",
             font=("Segoe UI", 15, "bold"), bg="#eef2f7", fg="#111827").pack(anchor="w")
    tk.Label(body, text="A professional demo view for showing business owners what the product can do.",
             font=("Segoe UI", 9), bg="#eef2f7", fg="#64748b").pack(anchor="w", pady=(2, 14))

    features_frame = tk.Frame(body, bg="#eef2f7")
    features_frame.pack(fill="x")
    features = [
        ("📊", "Lead CRM", "Track every lead from New to Converted"),
        ("📞", "Follow-up", "Never lose an important customer follow-up"),
        ("📝", "Marketing Content", "Organise business marketing content"),
        ("📈", "Reports", "Understand leads, conversion and pipeline"),
        ("💡", "Smart Recommendations", "Get practical marketing ideas"),
        ("📱", "PC + Mobile", "Use the web version on the same Wi-Fi")
    ]
    for i, (icon, title, desc) in enumerate(features):
        card = tk.Frame(features_frame, bg="white", bd=1, relief="solid", padx=12, pady=12)
        card.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
        tk.Label(card, text=f"{icon}  {title}", font=("Segoe UI", 11, "bold"),
                 bg="white", fg="#111827").pack(anchor="w")
        tk.Label(card, text=desc, font=("Segoe UI", 9), wraplength=330,
                 justify="left", bg="white", fg="#64748b").pack(anchor="w", pady=(5, 0))
    features_frame.columnconfigure(0, weight=1)
    features_frame.columnconfigure(1, weight=1)

    pricing = tk.Frame(body, bg="white", bd=1, relief="solid", padx=15, pady=12)
    pricing.pack(fill="x", pady=(16, 10))
    tk.Label(pricing, text="SAMPLE PLANS", font=("Segoe UI", 11, "bold"),
             bg="white", fg="#111827").pack(anchor="w")
    tk.Label(pricing, text="Starter ₹299/month   •   Business ₹599/month   •   Pro ₹999/month",
             font=("Segoe UI", 10, "bold"), bg="white", fg="#2563eb").pack(anchor="w", pady=(7, 2))
    tk.Label(pricing, text="Use these as starting prices; final pricing can be changed after customer feedback.",
             font=("Segoe UI", 8), bg="white", fg="#64748b").pack(anchor="w")

    tk.Button(win, text="CLOSE DEMO", command=win.destroy, font=("Segoe UI", 10, "bold"),
              bg="#172033", fg="white", relief="flat", padx=18, pady=9).pack(pady=(0, 14))


def _web_html():
    current = load_data()
    leads = current.get("leads", [])
    counts = lead_status_counts(leads)
    pipeline = lead_pipeline_value(leads)
    converted = converted_value(leads)
    active = sum(1 for x in leads if normalize_status(x.get("status")) not in ("Converted", "Lost"))
    conversion = (sum(1 for x in leads if normalize_status(x.get("status")) == "Converted") / len(leads) * 100) if leads else 0

    rows = []
    for lead in leads:
        rows.append(f"""<tr><td>{str(lead.get('name',''))}</td><td>{str(lead.get('phone',''))}</td><td>{str(lead.get('service',''))}</td><td>{normalize_status(lead.get('status'))}</td><td>{normalize_priority(lead.get('priority'))}</td><td>₹{safe_amount(lead.get('loan_amount',0)):,.0f}</td><td>{str(lead.get('followup_date',''))}</td></tr>""")
    table = "".join(rows) or '<tr><td colspan="7" class="empty">No leads yet</td></tr>'

    return f"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DhandaSmart</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:#f1f5f9;color:#111827}}
header{{background:#172033;color:white;padding:22px 18px}}header h1{{margin:0;font-size:25px}}header p{{margin:5px 0 0;color:#cbd5e1}}
.wrap{{max-width:1100px;margin:auto;padding:16px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
.card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:15px}}.label{{font-size:12px;color:#64748b;font-weight:bold}}.value{{font-size:24px;font-weight:bold;margin-top:6px}}
.section{{margin-top:16px}}h2{{font-size:18px}}.tablebox{{overflow:auto;background:white;border-radius:10px;border:1px solid #e2e8f0}}table{{width:100%;border-collapse:collapse;min-width:760px}}th,td{{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left;font-size:13px}}th{{background:#f8fafc}}
form{{background:white;padding:15px;border:1px solid #e2e8f0;border-radius:10px;display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}input,select,textarea{{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:7px;font:inherit}}textarea{{min-height:70px;resize:vertical}}.full{{grid-column:1/-1}}button{{background:#172033;color:white;border:0;border-radius:7px;padding:11px 15px;font-weight:bold;cursor:pointer}}.empty{{text-align:center;padding:25px;color:#64748b}}
@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}form{{grid-template-columns:1fr}}.full{{grid-column:auto}}header h1{{font-size:21px}}}}
</style></head><body>
<header><div class="wrap"><h1>DHANDASMART</h1><p>Manage. Market. Grow.</p></div></header>
<div class="wrap">
<div class="grid">
<div class="card"><div class="label">TOTAL LEADS</div><div class="value">{len(leads)}</div></div>
<div class="card"><div class="label">ACTIVE LEADS</div><div class="value">{active}</div></div>
<div class="card"><div class="label">CONVERSION</div><div class="value">{conversion:.1f}%</div></div>
<div class="card"><div class="label">PIPELINE</div><div class="value">₹{pipeline:,.0f}</div></div>
</div>
<div class="section"><h2>📊 Lead CRM</h2><div class="tablebox"><table><thead><tr><th>Name</th><th>Phone</th><th>Service</th><th>Status</th><th>Priority</th><th>Amount</th><th>Follow-up</th></tr></thead><tbody>{table}</tbody></table></div></div>
<div class="section"><h2>➕ Add New Lead</h2>
<form method="post" action="/add">
<input name="name" placeholder="Customer name" required><input name="phone" placeholder="Phone">
<input name="service" placeholder="Interested service"><select name="status"><option>New</option><option>Contacted</option><option>Follow-up</option><option>Converted</option><option>Lost</option></select>
<select name="priority"><option>High</option><option selected>Medium</option><option>Low</option></select><input name="source" placeholder="Lead source (Facebook / Referral / etc.)">
<input name="amount" placeholder="Expected amount"><input name="followup_date" placeholder="Follow-up DD-MM-YYYY">
<textarea class="full" name="notes" placeholder="Notes"></textarea><button class="full" type="submit">SAVE LEAD</button>
</form></div>
</div></body></html>"""


def mobile_web_app():
    global WEB_SERVER
    if WEB_SERVER is not None:
        messagebox.showinfo("Web App Running", f"DhandaSmart Web App is already running.\\n\\nPC: http://127.0.0.1:{WEB_PORT}\\nMobile: http://{get_local_ip()}:{WEB_PORT}", parent=root)
        return

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def send_html(self, html, status=200):
            payload = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                self.send_html(_web_html())
            else:
                self.send_html("<h1>404</h1>", 404)

        def do_POST(self):
            if self.path != "/add":
                self.send_html("<h1>404</h1>", 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                form = parse_qs(raw)
                current = load_data()
                lead = {
                    "name": form.get("name", [""])[0].strip(),
                    "phone": form.get("phone", [""])[0].strip(),
                    "service": form.get("service", [""])[0].strip(),
                    "status": normalize_status(form.get("status", ["New"])[0]),
                    "priority": normalize_priority(form.get("priority", ["Medium"])[0]),
                    "source": form.get("source", ["Web"])[0].strip() or "Web",
                    "loan_amount": safe_amount(form.get("amount", ["0"])[0]),
                    "followup_date": form.get("followup_date", [""])[0].strip(),
                    "notes": form.get("notes", [""])[0].strip(),
                    "date": datetime.now().strftime("%d-%m-%Y"),
                    "history": [],
                    "last_contacted": ""
                }
                current.setdefault("leads", []).append(lead)
                save_data(current)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
            except Exception as exc:
                self.send_html(f"<h1>Error</h1><p>{exc}</p>", 500)

    try:
        WEB_SERVER = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler)
        thread = threading.Thread(target=WEB_SERVER.serve_forever, daemon=True)
        thread.start()
        local_ip = get_local_ip()
        win = tk.Toplevel(root)
        win.title("DhandaSmart - PC + Mobile Web App")
        win.geometry("600x360")
        win.resizable(False, False)
        tk.Label(win, text="📱 PC + MOBILE WEB APP", font=("Segoe UI", 18, "bold")).pack(pady=(22, 8))
        tk.Label(win, text="PC Browser", font=("Segoe UI", 10, "bold")).pack()
        tk.Label(win, text=f"http://127.0.0.1:{WEB_PORT}", font=("Consolas", 11)).pack(pady=(2, 12))
        tk.Label(win, text="Mobile (same Wi-Fi)", font=("Segoe UI", 10, "bold")).pack()
        tk.Label(win, text=f"http://{local_ip}:{WEB_PORT}", font=("Consolas", 11)).pack(pady=(2, 14))
        tk.Label(win, text="Keep the PC software running. Open the Mobile URL on your phone connected to the same Wi-Fi.",
                 wraplength=520, justify="center", font=("Segoe UI", 9), fg="#475569").pack(pady=4)
        btns = tk.Frame(win)
        btns.pack(pady=18)
        tk.Button(btns, text="OPEN ON THIS PC", command=lambda: webbrowser.open(f"http://127.0.0.1:{WEB_PORT}"),
                  font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="left", padx=5)
        def stop_server():
            global WEB_SERVER
            try:
                if WEB_SERVER:
                    WEB_SERVER.shutdown()
                    WEB_SERVER.server_close()
            finally:
                WEB_SERVER = None
                win.destroy()
        tk.Button(btns, text="STOP WEB APP", command=stop_server, font=("Segoe UI", 10, "bold"),
                  padx=14, pady=8).pack(side="left", padx=5)
        tk.Button(win, text="CLOSE", command=win.destroy, padx=16, pady=6).pack()
    except OSError as exc:
        WEB_SERVER = None
        messagebox.showerror("Web App Error", f"Port {WEB_PORT} could not be opened.\\n\\n{exc}", parent=root)


# =========================
# ONLINE DEMO WEB MODE
# =========================

def run_online_demo():
    """Run a password-protected Flask demo site without starting the Tkinter desktop UI.
    Intended for a demo-only deployment with isolated demo data."""
    if Flask is None:
        raise RuntimeError("Flask is not installed. Run: pip install flask")

    app = Flask(__name__)
    app.secret_key = os.environ.get("DHANDASMART_SECRET_KEY", "change-this-demo-secret")
    demo_user = os.environ.get("DHANDASMART_DEMO_USER", "demo")
    demo_password = os.environ.get("DHANDASMART_DEMO_PASSWORD", "demo123")
    demo_data_file = os.environ.get("DHANDASMART_DATA_FILE", "demo_data.json")

    def demo_load():
        nonlocal demo_data_file
        if os.path.exists(demo_data_file):
            try:
                with open(demo_data_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                d.setdefault("business_name", "DhandaSmart Demo")
                d.setdefault("business_type", "Demo Business")
                d.setdefault("leads", [])
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
            except Exception:
                pass
        return {
            "business_name": "DhandaSmart Demo",
            "business_type": "Business Demo",
            "leads": [
                {"name":"Rahul Sharma","phone":"98XXXXXX01","service":"Home Loan","status":"New","priority":"High","source":"Website","loan_amount":2500000,"followup_date":"","notes":"Demo lead","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""},
                {"name":"Amit Verma","phone":"98XXXXXX02","service":"Business Loan","status":"Follow-up","priority":"Medium","source":"Referral","loan_amount":1200000,"followup_date":"","notes":"Demo follow-up","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""},
                {"name":"Neha Gupta","phone":"98XXXXXX03","service":"Insurance","status":"Converted","priority":"Low","source":"Facebook","loan_amount":750000,"followup_date":"","notes":"Demo converted lead","date":datetime.now().strftime("%d-%m-%Y"),"history":[],"last_contacted":""}
            ],
            "audit": {}, "content_history": [], "campaigns": []
        }

    def demo_save(d):
        with open(demo_data_file, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4, ensure_ascii=False)

    def login_required():
        return session.get("demo_logged_in") is True

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = ""
        if request.method == "POST":
            if request.form.get("username", "") == demo_user and request.form.get("password", "") == demo_password:
                session["demo_logged_in"] = True
                return redirect(url_for("home"))
            error = "Invalid demo login"
        error_html = f"<div class='err'>{error}</div>" if error else ""
        return f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
        <title>DhandaSmart Demo Login</title><style>body{{font-family:Arial;background:#eef2f7;margin:0;display:grid;place-items:center;min-height:100vh}}.box{{background:#fff;padding:28px;border-radius:14px;width:min(90%,360px);box-shadow:0 8px 30px #0001}}h1{{margin:0 0 6px}}p{{color:#64748b}}input,button{{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:8px;border:1px solid #cbd5e1;font-size:16px}}button{{background:#172033;color:white;font-weight:bold;cursor:pointer}}.err{{color:#b91c1c}}</style></head><body><div class='box'><h1>DHANDASMART</h1><p>Secure Demo Login</p>{error_html}<form method='post'><input name='username' placeholder='Demo username' required><input name='password' type='password' placeholder='Password' required><button>LOGIN TO DEMO</button></form></div></body></html>"""

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/", methods=["GET"])
    def home():
        if not login_required():
            return redirect(url_for("login"))
        d = demo_load()
        leads = d.get("leads", [])
        active = sum(1 for x in leads if normalize_status(x.get("status")) not in ("Converted", "Lost"))
        converted = sum(1 for x in leads if normalize_status(x.get("status")) == "Converted")
        conversion = converted / len(leads) * 100 if leads else 0
        pipeline = sum(safe_amount(x.get("loan_amount", 0)) for x in leads if normalize_status(x.get("status")) in ("New","Contacted","Follow-up"))
        rows = "".join(f"<tr><td>{str(x.get('name',''))}</td><td>{str(x.get('phone',''))}</td><td>{str(x.get('service',''))}</td><td>{normalize_status(x.get('status'))}</td><td>{normalize_priority(x.get('priority'))}</td><td>₹{safe_amount(x.get('loan_amount',0)):,.0f}</td><td>{str(x.get('followup_date',''))}</td></tr>" for x in leads)
        html = f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>DhandaSmart Demo</title><style>
        *{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:#eef2f7;color:#111827}}header{{background:#172033;color:white;padding:18px}}.wrap{{max-width:1100px;margin:auto;padding:0 14px}}header h1{{margin:0;font-size:24px}}header p{{margin:4px 0 0;color:#cbd5e1}}.top{{display:flex;justify-content:space-between;align-items:center;gap:10px}}a{{color:inherit}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding-top:16px}}.card,.section{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px}}.value{{font-size:23px;font-weight:bold;margin-top:5px}}.label{{font-size:11px;color:#64748b;font-weight:bold}}.section{{margin-top:16px}}.tablebox{{overflow-x:auto}}table{{width:100%;min-width:760px;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #e2e8f0;text-align:left;font-size:13px}}th{{background:#f8fafc}}form{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}input,select,textarea,button{{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:7px;font:inherit}}textarea{{min-height:80px}}.full{{grid-column:1/-1}}button{{background:#172033;color:white;font-weight:bold;border:0}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}form{{grid-template-columns:1fr}}.full{{grid-column:auto}}header h1{{font-size:21px}}}}
        </style></head><body><header><div class='wrap top'><div><h1>DHANDASMART</h1><p>Manage. Market. Grow. — DEMO</p></div><a href='/logout'>Logout</a></div></header><main class='wrap'><div class='grid'><div class='card'><div class='label'>TOTAL LEADS</div><div class='value'>{len(leads)}</div></div><div class='card'><div class='label'>ACTIVE LEADS</div><div class='value'>{active}</div></div><div class='card'><div class='label'>CONVERSION</div><div class='value'>{conversion:.1f}%</div></div><div class='card'><div class='label'>PIPELINE</div><div class='value'>₹{pipeline:,.0f}</div></div></div><div class='section'><h2>📊 Lead CRM</h2><div class='tablebox'><table><thead><tr><th>Name</th><th>Phone</th><th>Service</th><th>Status</th><th>Priority</th><th>Amount</th><th>Follow-up</th></tr></thead><tbody>{rows}</tbody></table></div></div><div class='section'><h2>➕ Add New Demo Lead</h2><form method='post' action='/add'><input name='name' placeholder='Customer name' required><input name='phone' placeholder='Phone'><input name='service' placeholder='Interested service'><select name='status'><option>New</option><option>Contacted</option><option>Follow-up</option><option>Converted</option><option>Lost</option></select><select name='priority'><option>High</option><option selected>Medium</option><option>Low</option></select><input name='source' placeholder='Lead source'><input name='amount' placeholder='Expected amount'><input name='followup_date' placeholder='Follow-up DD-MM-YYYY'><textarea class='full' name='notes' placeholder='Notes'></textarea><button class='full'>SAVE DEMO LEAD</button></form></div></main></body></html>"""
        return html

    @app.route("/add", methods=["POST"])
    def add():
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

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)


if "--web-demo" in sys.argv:
    run_online_demo()
    sys.exit(0)

# =========================
# MAIN WINDOW
# =========================

root = tk.Tk()
root.title("DhandaSmart - Business Marketing & CRM")
root.geometry("1150x720")
root.minsize(850, 600)
try:
    if os.name == "nt":
        root.state("zoomed")
except Exception:
    pass


# =========================
# OUTPUT
# =========================

def clear_output():
    output.delete("1.0", tk.END)


def show(text):
    clear_output()
    output.insert(tk.END, text)
    output.see("1.0")


# =========================
# PROFESSIONAL DASHBOARD
# =========================

def dashboard():
    data = load_data()
    leads = data.get("leads", [])

    total = len(leads)
    converted = sum(1 for x in leads if normalize_status(x.get("status")) == "Converted")
    active = sum(1 for x in leads if normalize_status(x.get("status")) not in ("Converted", "Lost"))
    conversion = (converted / total * 100) if total else 0

    audit = data.get("audit", {})
    score = audit.get("score", "Not calculated")

    pipeline = lead_pipeline_value(leads)
    converted_money = converted_value(leads)

    overdue = 0
    due_today = 0
    upcoming = 0
    today = date.today()

    for lead in leads:
        if normalize_status(lead.get("status")) in ("Converted", "Lost"):
            continue
        d = parse_followup_date(lead.get("followup_date", ""))
        if d:
            if d < today:
                overdue += 1
            elif d == today:
                due_today += 1
            elif d <= today + timedelta(days=7):
                upcoming += 1

    counts = lead_status_counts(leads)

    win = tk.Toplevel(root)
    win.title("DhandaSmart - Professional Dashboard")
    win.geometry("1000x720")
    win.minsize(900, 650)
    maximize_for_screen(win)

    header = tk.Frame(win, bg="#172033", padx=18, pady=14)
    header.pack(fill="x")

    tk.Label(
        header,
        text="DHANDASMART",
        font=("Segoe UI", 22, "bold"),
        fg="white",
        bg="#172033"
    ).pack(anchor="w")

    tk.Label(
        header,
        text="Manage. Market. Grow.",
        font=("Segoe UI", 10),
        fg="#cbd5e1",
        bg="#172033"
    ).pack(anchor="w")

    cards = tk.Frame(win, bg="#eef2f7", padx=14, pady=14)
    cards.pack(fill="x")

    def card(parent, title, value, subtitle):
        f = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=14, pady=10)
        f.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"),
                 fg="#64748b", bg="white").pack(anchor="w")
        tk.Label(f, text=str(value), font=("Segoe UI", 20, "bold"),
                 fg="#111827", bg="white").pack(anchor="w", pady=(4, 0))
        tk.Label(f, text=subtitle, font=("Segoe UI", 8),
                 fg="#64748b", bg="white").pack(anchor="w")
        return f

    score_text = f"{score}/100" if isinstance(score, (int, float)) else str(score)
    card(cards, "MARKETING SCORE", score_text, "Current audit")
    card(cards, "TOTAL LEADS", total, "All saved leads")
    card(cards, "ACTIVE LEADS", active, "Open pipeline")
    card(cards, "CONVERSION", f"{conversion:.1f}%", "Lead conversion rate")

    cards2 = tk.Frame(win, bg="#eef2f7", padx=14, pady=2)
    cards2.pack(fill="x")
    card(cards2, "PIPELINE VALUE", f"₹{pipeline:,.0f}", "Expected loan amount")
    card(cards2, "CONVERTED VALUE", f"₹{converted_money:,.0f}", "Converted business value")
    card(cards2, "OVERDUE", overdue, "Follow-ups overdue")
    card(cards2, "DUE TODAY", due_today, "Follow-ups today")

    body = tk.Frame(win, bg="#eef2f7", padx=20, pady=12)
    body.pack(fill="both", expand=True)

    left = tk.Frame(body, bg="white", bd=1, relief="solid", padx=15, pady=12)
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))

    tk.Label(left, text="LEAD PIPELINE", font=("Segoe UI", 12, "bold"),
             bg="white", fg="#111827").pack(anchor="w", pady=(0, 10))

    max_count = max(counts.values()) if counts else 1
    for status in VALID_STATUSES:
        row = tk.Frame(left, bg="white")
        row.pack(fill="x", pady=4)

        tk.Label(row, text=status, width=13, anchor="w",
                 font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")

        bar_bg = tk.Frame(row, bg="#e5e7eb", height=20)
        bar_bg.pack(side="left", fill="x", expand=True, padx=6)

        count = counts.get(status, 0)
        width = int((count / max_count) * 260) if max_count else 0
        bar = tk.Frame(bar_bg, bg="#2563eb", width=width, height=20)
        bar.place(x=0, y=0)

        tk.Label(row, text=str(count), width=5,
                 font=("Segoe UI", 9, "bold"), bg="white").pack(side="right")

    right = tk.Frame(body, bg="white", bd=1, relief="solid", padx=15, pady=12)
    right.pack(side="right", fill="both", expand=True, padx=(8, 0))

    tk.Label(right, text="QUICK ACTIONS", font=("Segoe UI", 12, "bold"),
             bg="white", fg="#111827").pack(anchor="w", pady=(0, 8))

    def action(text, command):
        tk.Button(
            right, text=text, command=command,
            font=("Segoe UI", 10, "bold"),
            bg="#f1f5f9", fg="#111827",
            relief="flat", padx=10, pady=8,
            cursor="hand2"
        ).pack(fill="x", pady=4)

    action("➕ Add New Lead", lead_management)
    action("📋 Open Lead CRM", lead_management)
    action("📞 Follow-up Task Center", followup_tasks)
    action("📝 Customer History", customer_followup_history)
    action("📊 Marketing Score", marketing_engine)
    action("💡 Smart Recommendations", smart_recommendations)
    action("📝 Marketing Report", marketing_report)
    action("🎯 Product Demo", product_demo)
    action("📱 PC + Mobile Web App", mobile_web_app)

    alert_text = (
        f"Follow-up alerts\n\n"
        f"Overdue: {overdue}\n"
        f"Today: {due_today}\n"
        f"Next 7 days: {upcoming}\n\n"
        f"Content items: {len(data.get('content_history', []))}\n"
        f"Campaigns: {len(data.get('campaigns', []))}"
    )

    tk.Label(
        right, text=alert_text, justify="left",
        font=("Segoe UI", 9), bg="white", fg="#475569"
    ).pack(anchor="w", pady=(14, 0))

    tk.Button(
        win, text="CLOSE DASHBOARD", command=win.destroy,
        font=("Segoe UI", 10, "bold"), bg="#172033", fg="white",
        relief="flat", padx=16, pady=8
    ).pack(pady=(0, 14))


def followup_tasks():
    data = load_data()
    leads = data.get("leads", [])

    win = tk.Toplevel(root)
    win.title("Dhanda AI - Follow-up Task Center")
    win.geometry("900x650")
    maximize_for_screen(win)

    tk.Label(
        win, text="FOLLOW-UP TASK CENTER",
        font=("Segoe UI", 18, "bold")
    ).pack(pady=(15, 2))

    tk.Label(
        win,
        text="Manage today's calls, overdue follow-ups and upcoming tasks",
        font=("Segoe UI", 9)
    ).pack(pady=(0, 12))

    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True, padx=15, pady=5)

    columns = ("Lead", "Phone", "Status", "Priority", "Follow-up", "Source", "Amount")
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    # ttk is imported below if available; otherwise use the fallback listbox.
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=110, anchor="w")
    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh():
        for item in tree.get_children():
            tree.delete(item)

        today = date.today()
        task_leads = []

        for idx, lead in enumerate(leads):
            status = normalize_status(lead.get("status"))
            if status in ("Converted", "Lost"):
                continue

            d = parse_followup_date(lead.get("followup_date", ""))
            if d:
                task_leads.append((d, idx, lead))

        task_leads.sort(key=lambda x: x[0])

        for d, idx, lead in task_leads:
            if d < today:
                label = "OVERDUE"
            elif d == today:
                label = "TODAY"
            else:
                label = d.strftime("%d-%m-%Y")

            tree.insert(
                "", "end", iid=str(idx),
                values=(
                    lead.get("name", ""),
                    lead.get("phone", ""),
                    normalize_status(lead.get("status")),
                    normalize_priority(lead.get("priority")),
                    label,
                    lead.get("source", "Unknown"),
                    f"₹{safe_amount(lead.get('loan_amount', 0)):,.0f}"
                )
            )

    def mark_contacted():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Lead", "Please select a lead first.")
            return

        idx = int(selected[0])
        leads[idx]["status"] = "Contacted"
        leads[idx]["last_contacted"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(data)
        refresh()
        messagebox.showinfo("Updated", "Lead marked as Contacted.")

    def set_followup():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Lead", "Please select a lead first.")
            return

        idx = int(selected[0])
        value = simpledialog.askstring(
            "Follow-up Date",
            "Enter date (YYYY-MM-DD):",
            initialvalue=leads[idx].get("followup_date", "")
        )
        if value is None:
            return

        if value and not parse_followup_date(value):
            messagebox.showerror("Invalid Date", "Use YYYY-MM-DD format.")
            return

        leads[idx]["followup_date"] = value
        leads[idx]["status"] = "Follow-up"
        save_data(data)
        refresh()

    def open_whatsapp():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Select Lead", "Please select a lead first.")
            return

        idx = int(selected[0])
        phone = "".join(ch for ch in str(leads[idx].get("phone", "")) if ch.isdigit())
        if len(phone) == 10:
            phone = "91" + phone

        if len(phone) < 10:
            messagebox.showwarning("Phone", "Valid phone number not available.")
            return

        webbrowser.open("https://wa.me/" + phone)

    buttons = tk.Frame(win)
    buttons.pack(fill="x", padx=15, pady=12)

    tk.Button(buttons, text="MARK CONTACTED", command=mark_contacted,
              font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left", padx=4)
    tk.Button(buttons, text="SET FOLLOW-UP", command=set_followup,
              font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left", padx=4)
    tk.Button(buttons, text="OPEN WHATSAPP", command=open_whatsapp,
              font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left", padx=4)
    tk.Button(buttons, text="REFRESH", command=refresh,
              font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="left", padx=4)
    tk.Button(buttons, text="CLOSE", command=win.destroy,
              font=("Segoe UI", 9, "bold"), padx=10, pady=7).pack(side="right", padx=4)

    refresh()



def customer_followup_history():
    data = load_data()
    leads = data.get("leads", [])

    win = tk.Toplevel(root)
    win.title("Dhanda AI - Customer Follow-up History")
    win.geometry("1050x700")
    maximize_for_screen(win)
    win.configure(bg="#f8fafc")

    tk.Label(
        win, text="CUSTOMER FOLLOW-UP HISTORY",
        font=("Segoe UI", 18, "bold"), bg="#f8fafc", fg="#111827"
    ).pack(pady=(15, 4))
    tk.Label(
        win, text="Track calls, WhatsApp, meetings, discussions and next follow-ups",
        font=("Segoe UI", 10), bg="#f8fafc", fg="#64748b"
    ).pack(pady=(0, 12))

    top = tk.Frame(win, bg="#f8fafc")
    top.pack(fill="x", padx=18)

    tk.Label(top, text="Customer:", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(side="left")
    customer_var = tk.StringVar()
    customer_box = ttk.Combobox(top, textvariable=customer_var, state="readonly", width=42)
    customer_box.pack(side="left", padx=8)

    selected = {"index": None}

    history_text = tk.Text(
        win, height=20, wrap="word", font=("Consolas", 10),
        bg="white", fg="#111827", bd=1, relief="solid"
    )
    history_text.pack(fill="both", expand=True, padx=18, pady=10)

    def refresh_customers():
        names = [f"{i+1}. {lead.get('name','')} | {lead.get('phone','')}" for i, lead in enumerate(leads)]
        customer_box["values"] = names
        if names:
            customer_box.current(0)
            show_history()
        else:
            selected["index"] = None
            history_text.delete("1.0", tk.END)
            history_text.insert(tk.END, "No customers found. Add a lead first.")

    def current_index():
        value = customer_var.get()
        if not value:
            return None
        try:
            idx = int(value.split(".", 1)[0]) - 1
            if 0 <= idx < len(leads):
                return idx
        except:
            pass
        return None

    def show_history(event=None):
        idx = current_index()
        selected["index"] = idx
        history_text.delete("1.0", tk.END)
        if idx is None:
            history_text.insert(tk.END, "Select a customer.")
            return

        lead = leads[idx]
        history = lead.get("history", [])
        history_text.insert(
            tk.END,
            f"CUSTOMER: {lead.get('name','')}\n"
            f"PHONE: {lead.get('phone','')}\n"
            f"SERVICE: {lead.get('service','')}\n"
            f"STATUS: {normalize_status(lead.get('status','New'))}\n"
            f"LAST CONTACTED: {lead.get('last_contacted','Not recorded')}\n"
            f"NEXT FOLLOW-UP: {lead.get('followup_date','Not set')}\n"
            f"TOTAL HISTORY ENTRIES: {len(history)}\n"
            "=" * 85 + "\n\n"
        )

        if not history:
            history_text.insert(tk.END, "No follow-up history recorded yet.\n")
            return

        for n, item in enumerate(reversed(history), 1):
            history_text.insert(
                tk.END,
                f"ENTRY {n}\n"
                f"Date/Time     : {item.get('timestamp','')}\n"
                f"Contact Type  : {item.get('contact_type','')}\n"
                f"Outcome       : {item.get('outcome','')}\n"
                f"Discussion    : {item.get('notes','')}\n"
                f"Next Follow-up: {item.get('next_followup','Not set')}\n"
                "-" * 85 + "\n"
            )

    customer_box.bind("<<ComboboxSelected>>", show_history)

    def add_history():
        idx = current_index()
        if idx is None:
            messagebox.showwarning("Select Customer", "Please select a customer first.", parent=win)
            return

        form = tk.Toplevel(win)
        form.title("Add Customer Contact")
        form.geometry("560x500")
        form.transient(win)
        form.grab_set()

        tk.Label(form, text="ADD CONTACT / FOLLOW-UP", font=("Segoe UI", 15, "bold")).pack(pady=12)
        frame = tk.Frame(form)
        frame.pack(fill="both", expand=True, padx=25)

        tk.Label(frame, text="Contact Type").pack(anchor="w", pady=(5, 2))
        type_var = tk.StringVar(value="Call")
        ttk.Combobox(frame, textvariable=type_var, state="readonly",
                     values=["Call", "WhatsApp", "Meeting", "Email", "Other"]).pack(fill="x")

        tk.Label(frame, text="Outcome").pack(anchor="w", pady=(10, 2))
        outcome_var = tk.StringVar(value="Interested")
        ttk.Combobox(frame, textvariable=outcome_var, state="readonly",
                     values=["Interested", "Not Interested", "Follow-up", "Converted", "Other"]).pack(fill="x")

        tk.Label(frame, text="Discussion / Notes").pack(anchor="w", pady=(10, 2))
        notes_box = tk.Text(frame, height=7, wrap="word")
        notes_box.pack(fill="both", expand=True)

        tk.Label(frame, text="Next Follow-up Date (DD-MM-YYYY, optional)").pack(anchor="w", pady=(10, 2))
        date_var = tk.StringVar()
        tk.Entry(frame, textvariable=date_var).pack(fill="x")

        def save_history():
            next_date = date_var.get().strip()
            if next_date and not parse_followup_date(next_date):
                messagebox.showerror("Invalid Date", "Use DD-MM-YYYY format.", parent=form)
                return

            notes = notes_box.get("1.0", tk.END).strip()
            if not notes:
                messagebox.showwarning("Notes Required", "Please enter what was discussed.", parent=form)
                return

            lead = leads[idx]
            lead.setdefault("history", [])
            outcome = outcome_var.get()
            timestamp = datetime.now().strftime("%d-%m-%Y %I:%M %p")

            lead["history"].append({
                "timestamp": timestamp,
                "contact_type": type_var.get(),
                "outcome": outcome,
                "notes": notes,
                "next_followup": next_date
            })
            lead["last_contacted"] = timestamp

            if outcome == "Converted":
                lead["status"] = "Converted"
            elif outcome == "Follow-up" or next_date:
                lead["status"] = "Follow-up"
            elif outcome == "Interested":
                lead["status"] = "Contacted"

            if next_date:
                lead["followup_date"] = next_date

            save_data()
            form.destroy()
            show_history()
            messagebox.showinfo("Saved", "Customer contact history saved.", parent=win)

        tk.Button(form, text="SAVE CONTACT HISTORY", command=save_history,
                  font=("Segoe UI", 10, "bold"), bg="#2563eb", fg="white",
                  relief="flat", padx=15, pady=9).pack(pady=15)

    def delete_last():
        idx = current_index()
        if idx is None or not leads[idx].get("history"):
            messagebox.showinfo("Nothing to Delete", "This customer has no history entries.", parent=win)
            return
        if messagebox.askyesno("Confirm", "Delete the latest history entry?", parent=win):
            leads[idx]["history"].pop()
            if leads[idx]["history"]:
                leads[idx]["last_contacted"] = leads[idx]["history"][-1].get("timestamp", "")
            else:
                leads[idx]["last_contacted"] = ""
            save_data()
            show_history()

    buttons = tk.Frame(win, bg="#f8fafc")
    buttons.pack(fill="x", padx=18, pady=(0, 15))
    tk.Button(buttons, text="➕ Add Contact / Follow-up", command=add_history,
              font=("Segoe UI", 10, "bold"), bg="#16a34a", fg="white", relief="flat", padx=12, pady=8).pack(side="left", padx=4)
    tk.Button(buttons, text="🗑 Delete Last Entry", command=delete_last,
              font=("Segoe UI", 10, "bold"), bg="#dc2626", fg="white", relief="flat", padx=12, pady=8).pack(side="left", padx=4)
    tk.Button(buttons, text="🔄 Refresh", command=refresh_customers,
              font=("Segoe UI", 10, "bold"), bg="#475569", fg="white", relief="flat", padx=12, pady=8).pack(side="left", padx=4)
    tk.Button(buttons, text="CLOSE", command=win.destroy,
              font=("Segoe UI", 10, "bold"), bg="#172033", fg="white", relief="flat", padx=12, pady=8).pack(side="right", padx=4)

    refresh_customers()

def business_profile():

    name = simpledialog.askstring(
        "Business Profile",
        "Enter Business Name:",
        initialvalue=data.get("business_name", "")
    )

    if not name:
        return

    btype = simpledialog.askstring(
        "Business Profile",
        "Enter Business Type:",
        initialvalue=data.get("business_type", "")
    )

    if not btype:
        return

    data["business_name"] = name.strip()
    data["business_type"] = btype.strip()

    save_data()

    messagebox.showinfo(
        "Saved",
        "Business profile saved successfully."
    )

    dashboard()


# =========================
# AI MARKETING ENGINE
# =========================

def marketing_engine():

    reviews = simpledialog.askinteger(
        "AI Marketing Engine",
        "Total Google Reviews:",
        minvalue=0
    )
    if reviews is None:
        return

    photos = simpledialog.askinteger(
        "AI Marketing Engine",
        "Business Photos:",
        minvalue=0
    )
    if photos is None:
        return

    description = simpledialog.askstring(
        "AI Marketing Engine",
        "Business description complete? (yes/no):"
    )
    if description is None:
        return

    website = simpledialog.askstring(
        "AI Marketing Engine",
        "Website available? (yes/no):"
    )
    if website is None:
        return

    social = simpledialog.askstring(
        "AI Marketing Engine",
        "Social media available? (yes/no):"
    )
    if social is None:
        return

    description = description.lower().strip()
    website = website.lower().strip()
    social = social.lower().strip()

    score = 0
    strengths = []
    weaknesses = []
    actions = []

    if reviews >= 100:
        score += 30
        strengths.append("Strong Google review presence.")
    elif reviews >= 50:
        score += 25
        strengths.append("Good Google review presence.")
    elif reviews >= 20:
        score += 15
        strengths.append("Growing Google review presence.")
    else:
        weaknesses.append("Very low review presence.")
        actions.append("Increase genuine customer reviews.")

    if photos >= 50:
        score += 20
        strengths.append("Strong photo presence.")
    elif photos >= 20:
        score += 15
        strengths.append("Good photo presence.")
    elif photos >= 10:
        score += 10
        strengths.append("Basic photo presence.")
    else:
        weaknesses.append("Very low photo presence.")
        actions.append(
            "Add photos of services, office, team and work."
        )

    if description == "yes":
        score += 20
        strengths.append("Business description is complete.")
    else:
        weaknesses.append("Business description is incomplete.")
        actions.append(
            "Create an SEO-friendly business description."
        )

    if website == "yes":
        score += 15
        strengths.append("Website presence available.")
    else:
        weaknesses.append("Website presence missing.")
        actions.append(
            "Create a simple business landing page."
        )

    if social == "yes":
        score += 15
        strengths.append("Social media presence available.")
    else:
        weaknesses.append("Social media presence missing.")
        actions.append(
            "Start consistent social media posting."
        )

    if score >= 80:
        status = "Excellent"
    elif score >= 60:
        status = "Good"
    else:
        status = "Needs Improvement"

    data["audit"] = {
        "score": score,
        "reviews": reviews,
        "photos": photos,
        "description": description,
        "website": website,
        "social": social,
        "date": datetime.now().strftime("%d-%m-%Y %H:%M")
    }

    save_data()

    text = f"""
========================================
          AI MARKETING AUDIT
========================================

Business : {data.get("business_name", "Not Set")}

Marketing Score : {score} / 100
Status          : {status}

----------------------------------------
STRENGTHS
----------------------------------------
"""

    if strengths:
        for item in strengths:
            text += "+ " + item + "\n"
    else:
        text += "No major strengths detected.\n"

    text += """
----------------------------------------
WEAKNESSES
----------------------------------------
"""

    if weaknesses:
        for item in weaknesses:
            text += "- " + item + "\n"
    else:
        text += "No major weaknesses detected.\n"

    text += """
----------------------------------------
PRIORITY ACTION PLAN
----------------------------------------
"""

    if actions:
        for i, action in enumerate(actions, 1):
            text += f"{i}. {action}\n"
    else:
        text += "Marketing foundation looks strong.\n"

    text += """
----------------------------------------
Audit saved successfully.
========================================
"""

    show(text)


# =========================
# SMART RECOMMENDATIONS
# =========================

def smart_recommendations():

    audit = data.get("audit", {})

    if not audit:
        messagebox.showwarning(
            "Run Audit",
            "Please run AI Marketing Engine first."
        )
        return

    score = audit.get("score", 0)
    reviews = audit.get("reviews", 0)
    photos = audit.get("photos", 0)

    recommendations = []

    if reviews < 20:
        recommendations.append(
            "Increase genuine customer reviews."
        )

    if photos < 10:
        recommendations.append(
            "Add more high-quality business photos."
        )

    if audit.get("description") != "yes":
        recommendations.append(
            "Improve your business description."
        )

    if audit.get("website") != "yes":
        recommendations.append(
            "Create a simple business website/landing page."
        )

    if audit.get("social") != "yes":
        recommendations.append(
            "Start regular social media posting."
        )

    if len(data.get("leads", [])) == 0:
        recommendations.append(
            "Start collecting and tracking leads."
        )

    text = f"""
========================================
       SMART RECOMMENDATIONS
========================================

Current Marketing Score : {score} / 100

----------------------------------------
TOP RECOMMENDATIONS
----------------------------------------
"""

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            text += f"{i}. {rec}\n"
    else:
        text += "Your marketing foundation is strong.\n"

    text += "\n========================================"

    show(text)


# =========================
# CONTENT GENERATOR
# =========================

def content_generator():

    business = data.get("business_name", "")

    if not business:
        messagebox.showwarning(
            "Business Profile",
            "First create Business Profile."
        )
        return

    service = simpledialog.askstring(
        "Content Generator",
        "Enter service/product:"
    )
    if not service:
        return

    platform = simpledialog.askstring(
        "Content Generator",
        "Platform (Facebook/Instagram/WhatsApp):"
    )
    if not platform:
        return

    post = f"""
🚀 {business}

Looking for reliable {service}?

We provide professional {service} solutions
with simple process and customer-focused service.

✅ Easy Process
✅ Professional Support
✅ Quick Response

📞 Contact us today to know more.

#Business #Marketing #{service.replace(" ", "")}
"""

    data.setdefault("content_history", []).append({
        "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "service": service,
        "platform": platform,
        "content": post
    })

    save_data()

    show(
        "========================================\n"
        "          CONTENT GENERATOR\n"
        "========================================\n\n"
        + post +
        "\n========================================"
    )


# =========================
# SEO ANALYSIS
# =========================

def seo_analysis():

    keyword = simpledialog.askstring(
        "SEO Analysis",
        "Enter main keyword:"
    )

    if not keyword:
        return

    business = data.get("business_name", "Your Business")

    text = f"""
========================================
             SEO ANALYSIS
========================================

Business : {business}

Main Keyword:
{keyword}

----------------------------------------
SEO KEYWORD IDEAS
----------------------------------------

{keyword} near me
best {keyword}
{keyword} services
{keyword} company
affordable {keyword}
{keyword} in my city
{keyword} online

----------------------------------------
SEO ACTION PLAN
----------------------------------------

1. Use keyword in business description.
2. Add keyword to website title.
3. Create useful service pages.
4. Publish local content regularly.
5. Encourage genuine customer reviews.

NOTE:
This module provides planning ideas.
It does not fetch live Google search data.

========================================
"""

    show(text)


# =========================
# REVIEW REPLY
# =========================

def review_reply():

    review = simpledialog.askstring(
        "Review Reply Generator",
        "Enter customer review:"
    )

    if not review:
        return

    lower = review.lower()

    if any(word in lower for word in ["good", "great", "excellent", "nice"]):
        reply = (
            "Thank you so much for your valuable feedback! "
            "We are happy to know that you had a great "
            "experience. We look forward to serving you again."
        )
    elif any(word in lower for word in ["bad", "poor", "worst", "late"]):
        reply = (
            "Thank you for sharing your feedback. "
            "We are sorry that your experience did not "
            "meet expectations. We take your feedback "
            "seriously and will work to improve."
        )
    else:
        reply = (
            "Thank you for taking the time to share your "
            "feedback. We truly appreciate your support "
            "and look forward to serving you again."
        )

    show(
        "========================================\n"
        "        REVIEW REPLY GENERATOR\n"
        "========================================\n\n"
        "Customer Review:\n"
        + review +
        "\n\nSuggested Reply:\n"
        + reply +
        "\n\n========================================"
    )


# =========================
# SOCIAL MEDIA
# =========================

def social_media():

    platform = simpledialog.askstring(
        "Social Media",
        "Platform:"
    )

    if not platform:
        return

    text = f"""
========================================
             SOCIAL MEDIA
========================================

Platform : {platform}

POST IDEAS
----------------------------------------

1. Customer Success Story
2. Educational Tip
3. Service Introduction
4. Frequently Asked Question
5. Behind The Scenes
6. Customer Review
7. Limited-Time Offer
8. Business Introduction
9. Local Area Post
10. Helpful Industry Tip

SUGGESTED POSTING PLAN
----------------------------------------

Monday    - Educational Post
Wednesday - Service Post
Friday    - Customer Story
Sunday    - Offer / Engagement Post

========================================
"""

    show(text)


# =========================
# COMPETITOR ANALYSIS
# =========================

def competitor_analysis():

    competitor = simpledialog.askstring(
        "Competitor Analysis",
        "Enter competitor name:"
    )

    if not competitor:
        return

    text = f"""
========================================
          COMPETITOR ANALYSIS
========================================

Competitor : {competitor}

CHECK THESE AREAS
----------------------------------------

✓ Google Reviews
✓ Review Rating
✓ Business Photos
✓ Business Description
✓ Website
✓ Social Media
✓ Posting Frequency
✓ Customer Offers
✓ Local SEO
✓ Lead Generation

----------------------------------------
STRATEGY
----------------------------------------

1. Find competitor strengths.
2. Find competitor weaknesses.
3. Improve your Google profile.
4. Publish better content.
5. Build stronger customer trust.
6. Track reviews regularly.

NOTE:
This is a planning framework.
It does not fetch live competitor data.

========================================
"""

    show(text)


# ============================================================
# ADVANCED LEAD CRM
# ============================================================

def lead_management():

    leads = data.setdefault("leads", [])

    window = tk.Toplevel(root)
    window.title("Dhanda AI - Advanced Lead CRM")
    window.geometry("680x780")
    window.minsize(600, 450)
    maximize_for_screen(window)

    # Scrollable CRM content so every option remains accessible
    canvas = tk.Canvas(window, highlightthickness=0)
    scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
    content = tk.Frame(canvas)

    content.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")

    def resize_content(event):
        canvas.itemconfigure(canvas_window, width=event.width)

    canvas.bind("<Configure>", resize_content)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    tk.Label(
        content,
        text="ADVANCED LEAD CRM",
        font=("Arial", 21, "bold")
    ).pack(pady=12)

    tk.Label(
        content,
        text="New → Contacted → Follow-up → Converted / Lost",
        font=("Arial", 9)
    ).pack(pady=(0, 10))

    # -------------------------
    # ADD LEAD
    # -------------------------

    def add_lead():

        name = simpledialog.askstring(
            "Add Lead", "Customer Name:", parent=window
        )
        if not name:
            return

        phone = simpledialog.askstring(
            "Add Lead", "Phone:", parent=window
        )

        service = simpledialog.askstring(
            "Add Lead", "Interested Service:", parent=window
        )

        status = simpledialog.askstring(
            "Add Lead",
            "Status:\nNew / Contacted / Follow-up / Converted / Lost",
            initialvalue="New",
            parent=window
        )

        final_status = normalize_status(status)

        followup_date = ""

        if final_status == "Follow-up":
            followup_date = simpledialog.askstring(
                "Follow-up Date",
                "Enter date (DD-MM-YYYY):",
                parent=window
            )

            if followup_date and not parse_followup_date(followup_date):
                messagebox.showwarning(
                    "Invalid Date",
                    "Use DD-MM-YYYY format.",
                    parent=window
                )
                return

        source = simpledialog.askstring(
            "Lead Source",
            "Source (Facebook / Google / Referral / Call / Other):",
            initialvalue="Other",
            parent=window
        )

        loan_amount = simpledialog.askstring(
            "Expected Loan Amount",
            "Expected Amount (example: 500000):",
            initialvalue="0",
            parent=window
        )

        priority = simpledialog.askstring(
            "Lead Priority",
            "Priority (High / Medium / Low):",
            initialvalue="Medium",
            parent=window
        )

        notes = simpledialog.askstring(
            "Lead Notes",
            "Notes:",
            parent=window
        )

        lead = {
            "name": name.strip(),
            "phone": (phone or "").strip(),
            "service": (service or "").strip(),
            "status": final_status,
            "followup_date": followup_date or "",
            "source": (source or "Other").strip(),
            "loan_amount": safe_amount(loan_amount),
            "priority": normalize_priority(priority),
            "notes": (notes or "").strip(),
            "date": datetime.now().strftime("%d-%m-%Y")
        }

        leads.append(lead)
        save_data()

        messagebox.showinfo(
            "Lead Saved",
            "Lead added successfully.",
            parent=window
        )

        dashboard()

    # -------------------------
    # FORMAT LEAD
    # -------------------------

    def format_lead(number, lead):

        status = normalize_status(lead.get("status"))
        priority = normalize_priority(lead.get("priority"))

        return (
            f"{number}. {lead.get('name', '')}\n"
            f"   Phone        : {lead.get('phone', '')}\n"
            f"   Service      : {lead.get('service', '')}\n"
            f"   Status       : {status}\n"
            f"   Source       : {lead.get('source', 'Unknown')}\n"
            f"   Amount       : ₹{safe_amount(lead.get('loan_amount', 0)):,.0f}\n"
            f"   Priority     : {priority}\n"
            f"   Follow-up    : {lead.get('followup_date', '') or 'Not Set'}\n"
            f"   Notes        : {lead.get('notes', '') or 'None'}\n"
            f"   Added Date   : {lead.get('date', '')}\n"
            "----------------------------------------\n"
        )

    # -------------------------
    # VIEW ALL
    # -------------------------

    def view_leads():

        if not leads:
            messagebox.showinfo(
                "View Leads",
                "No leads available.",
                parent=window
            )
            return

        view_window = tk.Toplevel(window)
        view_window.title("Dhanda AI - All Leads")
        view_window.geometry("850x650")
        view_window.minsize(650, 450)
        maximize_for_screen(view_window)

        tk.Label(
            view_window,
            text="LEAD DATABASE",
            font=("Arial", 20, "bold")
        ).pack(pady=12)

        frame = tk.Frame(view_window)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        text_box = tk.Text(
            frame,
            font=("Consolas", 10),
            wrap="word",
            yscrollcommand=scrollbar.set
        )
        text_box.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=text_box.yview)

        text = ""
        for i, lead in enumerate(leads, 1):
            text += format_lead(i, lead)

        text_box.insert("1.0", text)
        text_box.config(state="disabled")

    # -------------------------
    # SEARCH
    # -------------------------

    def search_lead():

        if not leads:
            messagebox.showwarning(
                "No Leads",
                "No leads available.",
                parent=window
            )
            return

        query = simpledialog.askstring(
            "Search Lead",
            "Search Name / Phone / Service / Source / Notes:",
            parent=window
        )

        if not query:
            return

        query = query.lower().strip()
        results = []

        for i, lead in enumerate(leads, 1):

            searchable = " ".join([
                str(lead.get("name", "")),
                str(lead.get("phone", "")),
                str(lead.get("service", "")),
                str(lead.get("status", "")),
                str(lead.get("source", "")),
                str(lead.get("loan_amount", "")),
                str(lead.get("priority", "")),
                str(lead.get("notes", ""))
            ]).lower()

            if query in searchable:
                results.append((i, lead))

        text = """
========================================
             SEARCH RESULT
========================================

"""

        if results:
            for number, lead in results:
                text += format_lead(number, lead)
        else:
            text += "No matching lead found.\n"

        text += "========================================"
        show(text)

    # -------------------------
    # FILTER STATUS
    # -------------------------

    def filter_status():

        if not leads:
            messagebox.showwarning(
                "No Leads",
                "No leads available.",
                parent=window
            )
            return

        status = simpledialog.askstring(
            "Filter Status",
            "New / Contacted / Follow-up / Converted / Lost:",
            parent=window
        )

        if not status:
            return

        status = normalize_status(status)

        results = [
            (i, lead)
            for i, lead in enumerate(leads, 1)
            if normalize_status(lead.get("status")) == status
        ]

        text = f"""
========================================
          STATUS: {status.upper()}
========================================

"""

        if results:
            for number, lead in results:
                text += format_lead(number, lead)
        else:
            text += "No leads found.\n"

        text += "========================================"
        show(text)

    # -------------------------
    # FILTER PRIORITY
    # -------------------------

    def filter_priority():

        priority = simpledialog.askstring(
            "Filter Priority",
            "High / Medium / Low:",
            initialvalue="High",
            parent=window
        )

        if not priority:
            return

        priority = normalize_priority(priority)

        results = [
            (i, lead)
            for i, lead in enumerate(leads, 1)
            if normalize_priority(lead.get("priority")) == priority
        ]

        text = f"""
========================================
         PRIORITY: {priority.upper()}
========================================

"""

        if results:
            for number, lead in results:
                text += format_lead(number, lead)
        else:
            text += "No leads found.\n"

        text += "========================================"
        show(text)

    # -------------------------
    # EDIT LEAD
    # -------------------------

    def edit_lead():

        if not leads:
            messagebox.showwarning(
                "No Leads",
                "No leads available.",
                parent=window
            )
            return

        number = simpledialog.askinteger(
            "Edit Lead",
            f"Lead Number (1-{len(leads)}):",
            minvalue=1,
            maxvalue=len(leads),
            parent=window
        )

        if number is None:
            return

        lead = leads[number - 1]

        fields = [
            ("name", "Customer Name"),
            ("phone", "Phone"),
            ("service", "Interested Service"),
            ("source", "Lead Source"),
            ("loan_amount", "Expected Amount"),
            ("priority", "Priority"),
            ("notes", "Notes")
        ]

        for key, label in fields:

            current = lead.get(key, "")

            if key == "loan_amount":
                current = str(current)

            value = simpledialog.askstring(
                "Edit Lead",
                label + ":",
                initialvalue=str(current),
                parent=window
            )

            if value is not None:

                if key == "loan_amount":
                    lead[key] = safe_amount(value)

                elif key == "priority":
                    lead[key] = normalize_priority(value)

                else:
                    lead[key] = value.strip()

        save_data()

        messagebox.showinfo(
            "Updated",
            "Lead details updated successfully.",
            parent=window
        )

        view_leads()

    # -------------------------
    # UPDATE STATUS
    # -------------------------

    def update_status():

        if not leads:
            messagebox.showwarning(
                "No Leads",
                "No leads available.",
                parent=window
            )
            return

        number = simpledialog.askinteger(
            "Update Lead",
            f"Lead Number (1-{len(leads)}):",
            minvalue=1,
            maxvalue=len(leads),
            parent=window
        )

        if number is None:
            return

        lead = leads[number - 1]

        current = normalize_status(
            lead.get("status", "New")
        )

        status = simpledialog.askstring(
            "Update Status",
            "New Status:\nNew / Contacted / Follow-up / Converted / Lost",
            initialvalue=current,
            parent=window
        )

        if not status:
            return

        status = normalize_status(status)
        lead["status"] = status

        if status == "Follow-up":

            followup = simpledialog.askstring(
                "Follow-up Date",
                "Date (DD-MM-YYYY):",
                initialvalue=lead.get("followup_date", ""),
                parent=window
            )

            if followup and not parse_followup_date(followup):
                messagebox.showwarning(
                    "Invalid Date",
                    "Use DD-MM-YYYY format.",
                    parent=window
                )
                return

            lead["followup_date"] = followup or ""

        else:
            lead["followup_date"] = ""

        save_data()

        messagebox.showinfo(
            "Updated",
            "Lead status updated successfully.",
            parent=window
        )

        dashboard()

    # -------------------------
    # FOLLOW-UP DASHBOARD
    # -------------------------

    def followup_dashboard():

        today_items = []
        overdue_items = []
        upcoming_items = []

        today = date.today()

        for i, lead in enumerate(leads, 1):

            if normalize_status(lead.get("status")) != "Follow-up":
                continue

            d = parse_followup_date(
                lead.get("followup_date", "")
            )

            if not d:
                continue

            if d < today:
                overdue_items.append((i, lead, d))
            elif d == today:
                today_items.append((i, lead, d))
            elif d <= today + timedelta(days=7):
                upcoming_items.append((i, lead, d))

        text = """
========================================
        FOLLOW-UP DASHBOARD
========================================

OVERDUE
----------------------------------------
"""

        if overdue_items:
            for number, lead, d in overdue_items:
                text += (
                    f"{number}. {lead.get('name', '')} | "
                    f"{lead.get('phone', '')} | "
                    f"₹{safe_amount(lead.get('loan_amount', 0)):,.0f} | "
                    f"Due: {d.strftime('%d-%m-%Y')}\n"
                )
        else:
            text += "No overdue follow-ups.\n"

        text += """
----------------------------------------
DUE TODAY
----------------------------------------
"""

        if today_items:
            for number, lead, d in today_items:
                text += (
                    f"{number}. {lead.get('name', '')} | "
                    f"{lead.get('phone', '')} | "
                    f"₹{safe_amount(lead.get('loan_amount', 0)):,.0f}\n"
                )
        else:
            text += "No follow-ups due today.\n"

        text += """
----------------------------------------
UPCOMING - NEXT 7 DAYS
----------------------------------------
"""

        if upcoming_items:
            for number, lead, d in upcoming_items:
                text += (
                    f"{number}. {lead.get('name', '')} | "
                    f"{lead.get('phone', '')} | "
                    f"{d.strftime('%d-%m-%Y')}\n"
                )
        else:
            text += "No upcoming follow-ups.\n"

        text += "\n========================================"

        show(text)

    # -------------------------
    # ANALYTICS
    # -------------------------

    def lead_statistics():

        counts = lead_status_counts()
        total = len(leads)
        active = counts["New"] + counts["Contacted"] + counts["Follow-up"]

        conversion_rate = (
            counts["Converted"] / total * 100
            if total else 0
        )

        high_priority = sum(
            1 for lead in leads
            if normalize_priority(lead.get("priority")) == "High"
        )

        text = f"""
========================================
          ADVANCED LEAD ANALYTICS
========================================

TOTAL LEADS        : {total}
ACTIVE LEADS       : {active}
HIGH PRIORITY      : {high_priority}

----------------------------------------
PIPELINE
----------------------------------------

New                : {counts["New"]}
Contacted          : {counts["Contacted"]}
Follow-up          : {counts["Follow-up"]}
Converted          : {counts["Converted"]}
Lost               : {counts["Lost"]}

----------------------------------------
FINANCIAL POTENTIAL
----------------------------------------

Pipeline Value     : ₹{lead_pipeline_value():,.0f}
Converted Value    : ₹{converted_value():,.0f}

----------------------------------------
PERFORMANCE
----------------------------------------

Conversion Rate    : {conversion_rate:.1f}%

----------------------------------------
FOLLOW-UP
----------------------------------------

Overdue            : {sum(
    1 for lead in leads
    if normalize_status(lead.get("status")) == "Follow-up"
    and followup_category(lead.get("followup_date")) == "Overdue"
)}

Due Today          : {sum(
    1 for lead in leads
    if normalize_status(lead.get("status")) == "Follow-up"
    and followup_category(lead.get("followup_date")) == "Due Today"
)}

========================================
"""

        show(text)

    # -------------------------
    # SOURCE REPORT
    # -------------------------

    def lead_source_report():

        if not leads:
            show("No leads available.")
            return

        sources = {}

        for lead in leads:
            source = lead.get("source", "Unknown").strip() or "Unknown"
            sources[source] = sources.get(source, 0) + 1

        ordered = sorted(
            sources.items(),
            key=lambda x: x[1],
            reverse=True
        )

        text = """
========================================
          LEAD SOURCE REPORT
========================================

"""

        for source, count in ordered:
            percentage = count / len(leads) * 100
            text += (
                f"{source:<25} {count:>4} leads  "
                f"({percentage:.1f}%)\n"
            )

        best = ordered[0][0]

        text += f"""
----------------------------------------
BEST LEAD SOURCE : {best}
----------------------------------------

Use the source report to understand
where your enquiries are coming from.

========================================
"""

        show(text)

    # -------------------------
    # DELETE LEAD
    # -------------------------

    def delete_lead():

        if not leads:
            messagebox.showwarning(
                "No Leads",
                "No leads available.",
                parent=window
            )
            return

        number = simpledialog.askinteger(
            "Delete Lead",
            f"Lead Number (1-{len(leads)}):",
            minvalue=1,
            maxvalue=len(leads),
            parent=window
        )

        if number is None:
            return

        lead = leads[number - 1]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete lead '{lead.get('name', '')}'?",
            parent=window
        )

        if not confirm:
            return

        leads.pop(number - 1)
        save_data()

        messagebox.showinfo(
            "Deleted",
            "Lead deleted successfully.",
            parent=window
        )

        dashboard()

    # -------------------------
    # BUTTONS
    # -------------------------

    def crm_button(text, command):
        tk.Button(
            content,
            text=text,
            width=38,
            height=2,
            font=("Arial", 10, "bold"),
            command=command
        ).pack(pady=4)

    crm_button("ADD NEW LEAD", add_lead)
    crm_button("VIEW ALL LEADS", view_leads)
    crm_button("SEARCH LEAD", search_lead)
    crm_button("FILTER BY STATUS", filter_status)
    crm_button("FILTER BY PRIORITY", filter_priority)
    crm_button("EDIT LEAD", edit_lead)
    crm_button("UPDATE LEAD STATUS", update_status)
    crm_button("FOLLOW-UP DASHBOARD", followup_dashboard)
    crm_button("LEAD STATISTICS", lead_statistics)
    crm_button("LEAD SOURCE REPORT", lead_source_report)
    crm_button("DELETE LEAD", delete_lead)

    tk.Button(
        content,
        text="CLOSE",
        width=38,
        height=2,
        command=window.destroy
    ).pack(pady=12)


# =========================
# BUSINESS DESCRIPTION
# =========================

def business_description():

    business = data.get("business_name", "")

    if not business:
        messagebox.showwarning(
            "Business Profile",
            "First create Business Profile."
        )
        return

    location = simpledialog.askstring(
        "Business Description",
        "Business Location:"
    )

    speciality = simpledialog.askstring(
        "Business Description",
        "Main Speciality:"
    )

    audience = simpledialog.askstring(
        "Business Description",
        "Target Audience:"
    )

    if not location or not speciality or not audience:
        return

    description = (
        f"{business} is a trusted {speciality} business "
        f"serving customers in {location}. We focus on "
        f"providing reliable solutions and professional "
        f"customer service for {audience}. Our goal is to "
        f"make the customer experience simple, transparent "
        f"and convenient."
    )

    keywords = [
        speciality,
        f"{speciality} in {location}",
        f"best {speciality} in {location}",
        f"{speciality} services",
        f"{speciality} near me"
    ]

    show(
        "========================================\n"
        "       BUSINESS DESCRIPTION\n"
        "========================================\n\n"
        + description +
        "\n\nSEO KEYWORDS\n"
        "----------------------------------------\n"
        + "\n".join("• " + x for x in keywords)
        + "\n\n========================================"
    )


# =========================
# MARKETING CAMPAIGN
# =========================

def marketing_campaign():

    campaign = simpledialog.askstring(
        "Marketing Campaign",
        "Campaign Name:"
    )

    if not campaign:
        return

    objective = simpledialog.askstring(
        "Marketing Campaign",
        "Campaign Objective:"
    )

    audience = simpledialog.askstring(
        "Marketing Campaign",
        "Target Audience:"
    )

    budget = simpledialog.askstring(
        "Marketing Campaign",
        "Budget (optional):"
    )

    campaign_data = {
        "name": campaign,
        "objective": objective or "",
        "audience": audience or "",
        "budget": budget or "₹0",
        "date": datetime.now().strftime("%d-%m-%Y")
    }

    data.setdefault("campaigns", []).append(campaign_data)
    save_data()

    show(
        f"""
========================================
          MARKETING CAMPAIGN
========================================

Campaign : {campaign}

Objective:
{objective or ""}

Target Audience:
{audience or ""}

Budget:
{budget or "₹0"}

----------------------------------------
CAMPAIGN PLAN
----------------------------------------

1. Create audience-focused content.
2. Publish regularly.
3. Collect enquiries.
4. Track leads.
5. Follow up with prospects.
6. Measure conversions.

Campaign saved successfully.

========================================
"""
    )


# =========================
# MARKETING REPORT
# =========================

def marketing_report():

    audit = data.get("audit", {})
    leads = data.get("leads", [])
    counts = lead_status_counts()

    total = len(leads)
    converted = counts["Converted"]

    conversion_rate = (
        converted / total * 100
        if total else 0
    )

    text = f"""
========================================
          MARKETING REPORT
========================================

Business:
{data.get("business_name", "Not Set")}

Business Type:
{data.get("business_type", "Not Set")}

----------------------------------------
MARKETING SCORE
----------------------------------------

{audit.get("score", "Not available")} / 100

----------------------------------------
LEAD PERFORMANCE
----------------------------------------

Total Leads       : {total}
Active Leads      : {counts["New"] + counts["Contacted"] + counts["Follow-up"]}
Converted Leads   : {converted}
Lost Leads        : {counts["Lost"]}
Conversion Rate   : {conversion_rate:.1f}%

Pipeline Value    : ₹{lead_pipeline_value():,.0f}
Converted Value   : ₹{converted_value():,.0f}

----------------------------------------
CONTENT
----------------------------------------

Content Created : {len(data.get("content_history", []))}

----------------------------------------
CAMPAIGNS
----------------------------------------

Campaigns Created : {len(data.get("campaigns", []))}

----------------------------------------
NEXT STEPS
----------------------------------------

✓ Improve Google presence
✓ Collect genuine reviews
✓ Add quality photos
✓ Create useful content
✓ Track every lead
✓ Follow up consistently
✓ Focus on high-priority leads
✓ Review conversion performance

========================================
"""

    show(text)


# =========================
# EXPORT LEADS
# =========================

def export_leads():

    leads = data.get("leads", [])

    if not leads:
        messagebox.showwarning(
            "Export",
            "No leads available to export."
        )
        return

    filename = filedialog.asksaveasfilename(
        title="Export Leads",
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")]
    )

    if not filename:
        return

    fields = [
        "name",
        "phone",
        "service",
        "status",
        "source",
        "loan_amount",
        "priority",
        "followup_date",
        "notes",
        "date"
    ]

    try:
        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            for lead in leads:
                writer.writerow({
                    field: lead.get(field, "")
                    for field in fields
                })

        messagebox.showinfo(
            "Export Complete",
            "Lead database exported successfully."
        )

    except Exception as e:
        messagebox.showerror(
            "Export Error",
            str(e)
        )


# =========================
# BACKUP DATABASE
# =========================

def backup_database():

    if not os.path.exists(DATA_FILE):
        messagebox.showwarning(
            "Backup",
            "Database file does not exist yet."
        )
        return

    filename = filedialog.asksaveasfilename(
        title="Backup Dhanda AI Database",
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json")]
    )

    if not filename:
        return

    try:
        shutil.copy2(DATA_FILE, filename)

        messagebox.showinfo(
            "Backup Complete",
            "Dhanda AI database backup created successfully."
        )

    except Exception as e:
        messagebox.showerror(
            "Backup Error",
            str(e)
        )


# =========================
# DATA SUMMARY
# =========================

def data_summary():

    leads = data.get("leads", [])

    text = f"""
========================================
           DHANDA AI DATA SUMMARY
========================================

Business Name       : {data.get("business_name", "Not Set")}
Business Type       : {data.get("business_type", "Not Set")}

Total Leads         : {len(leads)}
Content Records     : {len(data.get("content_history", []))}
Campaign Records    : {len(data.get("campaigns", []))}

Marketing Score     : {data.get("audit", {}).get("score", "Not available")}

Database File       : {DATA_FILE}

----------------------------------------
STATUS
----------------------------------------

Database is stored locally on this computer.

========================================
"""

    show(text)


# =========================
# GUI LAYOUT
# =========================

title = tk.Label(
    root,
    text="DHANDA AI MARKETING",
    font=("Arial", 24, "bold")
)
title.pack(pady=12)

subtitle = tk.Label(
    root,
    text="Business Growth • Marketing • Lead CRM • PC + Mobile Ready",
    font=("Arial", 10)
)
subtitle.pack(pady=(0, 8))

main_frame = tk.Frame(root)
main_frame.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=8
)


# =========================
# LEFT MENU
# =========================

menu_container = tk.Frame(main_frame)
menu_container.pack(
    side="left",
    fill="y",
    padx=(0, 15)
)

menu_canvas = tk.Canvas(menu_container, width=245, highlightthickness=0)
menu_scrollbar = tk.Scrollbar(menu_container, orient="vertical", command=menu_canvas.yview)
menu_frame = tk.Frame(menu_canvas)
menu_window_id = menu_canvas.create_window((0, 0), window=menu_frame, anchor="nw")

def _update_menu_scrollregion(event=None):
    menu_canvas.configure(scrollregion=menu_canvas.bbox("all"))

def _resize_menu_width(event):
    menu_canvas.itemconfigure(menu_window_id, width=event.width)

menu_frame.bind("<Configure>", _update_menu_scrollregion)
menu_canvas.bind("<Configure>", _resize_menu_width)
menu_canvas.configure(yscrollcommand=menu_scrollbar.set)
menu_canvas.pack(side="left", fill="y", expand=False)
menu_scrollbar.pack(side="right", fill="y")


# =========================
# RIGHT OUTPUT
# =========================

output_frame = tk.Frame(main_frame)
output_frame.pack(
    side="right",
    fill="both",
    expand=True
)

output = tk.Text(
    output_frame,
    font=("Consolas", 10),
    wrap="word"
)

output.pack(
    side="left",
    fill="both",
    expand=True
)

scrollbar = tk.Scrollbar(
    output_frame,
    command=output.yview
)

scrollbar.pack(
    side="right",
    fill="y"
)

output.config(
    yscrollcommand=scrollbar.set
)


# =========================
# MENU BUTTONS
# =========================

buttons = [
    ("Dashboard", dashboard),
    ("Business Profile", business_profile),
    ("AI Marketing Engine", marketing_engine),
    ("Smart Recommendations", smart_recommendations),
    ("Content Generator", content_generator),
    ("SEO Analysis", seo_analysis),
    ("Review Reply", review_reply),
    ("Social Media", social_media),
    ("Competitor Analysis", competitor_analysis),
    ("Lead Management", lead_management),
    ("Customer Follow-up History", customer_followup_history),
    ("Business Description", business_description),
    ("Marketing Campaign", marketing_campaign),
    ("Marketing Report", marketing_report),
    ("🎯 Product Demo", product_demo),
    ("📱 PC + Mobile Web App", mobile_web_app),
    ("Export Leads CSV", export_leads),
    ("Backup Database", backup_database),
    ("Data Summary", data_summary)
]


for text, command in buttons:

    btn = tk.Button(
        menu_frame,
        text=text,
        command=command,
        width=25,
        height=2,
        font=("Arial", 9, "bold")
    )

    btn.pack(pady=3)


exit_button = tk.Button(
    menu_frame,
    text="EXIT",
    command=root.destroy,
    width=25,
    height=2,
    font=("Arial", 10, "bold")
)

exit_button.pack(pady=12)


# =========================
# START
# =========================

dashboard()
root.mainloop()
