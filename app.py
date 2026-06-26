"""
360 Core Values Assessment System — PT Energi Nusantara
Flask + SQLite. Real login, role-based access, central database.

Run:
    python database.py     # one-time: build & seed the database
    python app.py          # start the server -> http://127.0.0.1:5000
"""
import io
from functools import wraps
from flask import (Flask, g, session, request, redirect, url_for,
                   render_template, flash, Response, abort)
from werkzeug.security import check_password_hash

from database import (get_db, now, log_audit, add_notification,
                      generate_assignments, consolidate,
                      VALUES, VALUE_LABELS, CORPORATE_TARGET)

app = Flask(__name__)
app.secret_key = "fri142-apsi-demo-secret"   # demo key; rotate for real use


# --------------------------------------------------------------------------- #
# Request lifecycle / auth helpers
# --------------------------------------------------------------------------- #
@app.before_request
def load_user():
    g.db = get_db()
    g.user = None
    if "uid" in session:
        g.user = g.db.execute(
            "SELECT * FROM users WHERE id=?", (session["uid"],)
        ).fetchone()


@app.teardown_request
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def require(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not g.user:
                return redirect(url_for("login"))
            if roles and g.user["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject_globals():
    unread = 0
    if g.get("user"):
        unread = g.db.execute(
            "SELECT COUNT(*) c FROM notifications WHERE is_read=0 AND "
            "(target_role=? OR target_user_id=?)",
            (g.user["role"], g.user["id"]),
        ).fetchone()["c"]
    return dict(user=g.get("user"), VALUES=VALUES, VALUE_LABELS=VALUE_LABELS,
                TARGET=CORPORATE_TARGET, unread=unread)


def active_period():
    return g.db.execute(
        "SELECT * FROM periods WHERE status='active' ORDER BY id DESC LIMIT 1"
    ).fetchone()


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    if not g.user:
        return redirect(url_for("login"))
    if g.user["role"] == "employee":
        return redirect(url_for("my_assignments"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        row = g.db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if row and check_password_hash(row["password_hash"], p):
            session["uid"] = row["id"]
            log_audit(g.db, u, "LOGIN", f"Role {row['role']} signed in.")
            g.db.commit()
            return redirect(url_for("index"))
        flash("Wrong username or password. Use a Fast-Track button to autofill.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    if g.user:
        log_audit(g.db, g.user["username"], "LOGOUT", "Signed out.")
        g.db.commit()
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------------------- #
# Dashboard (SR overview)  — admin / hr / management
# --------------------------------------------------------------------------- #
@app.route("/dashboard")
@require("admin", "hr", "management")
def dashboard():
    period = active_period()
    emps = g.db.execute("SELECT * FROM employees").fetchall()
    results = {r["employee_id"]: r for r in g.db.execute(
        "SELECT * FROM results WHERE period_id=?", (period["id"],)).fetchall()}

    total = len(emps)
    done = len(results)
    pending = total - done
    participation = round(done / total * 100, 1) if total else 0

    # collective average per value
    collective = {}
    for v in VALUES:
        vals = [results[e["id"]][v] for e in emps if e["id"] in results]
        collective[v] = round(sum(vals) / len(vals), 2) if vals else 0
    # per-employee overall comparison
    comparison = [{"name": e["full_name"].split()[0],
                   "overall": results[e["id"]]["overall"] if e["id"] in results else 0}
                  for e in emps]

    return render_template("dashboard.html", period=period,
                           total=total, done=done, pending=pending,
                           participation=participation, collective=collective,
                           comparison=comparison)


# --------------------------------------------------------------------------- #
# SR-01 Employee Data — admin / hr
# --------------------------------------------------------------------------- #
@app.route("/employees", methods=["GET", "POST"])
@require("admin", "hr")
def employees():
    if request.method == "POST":
        nip = request.form["nip"].strip()
        name = request.form["full_name"].strip()
        pos = request.form["position"].strip()
        dept = request.form.get("department", "Project FRI-142").strip()
        sup = request.form.get("supervisor_id") or None
        try:
            g.db.execute(
                "INSERT INTO employees (nip, full_name, position, department, supervisor_id)"
                " VALUES (?,?,?,?,?)", (nip, name, pos, dept, sup))
            log_audit(g.db, g.user["username"], "ADD_EMPLOYEE", f"{name} ({nip})")
            g.db.commit()
            flash(f"Employee {name} added.", "ok")
        except Exception:
            flash("NIP already exists.", "error")
        return redirect(url_for("employees"))

    rows = g.db.execute(
        "SELECT e.*, s.full_name AS sup_name FROM employees e "
        "LEFT JOIN employees s ON e.supervisor_id=s.id ORDER BY e.id").fetchall()
    allemp = g.db.execute("SELECT id, full_name FROM employees").fetchall()
    return render_template("employees.html", rows=rows, allemp=allemp)


# --------------------------------------------------------------------------- #
# Evaluation Period — admin / hr
# --------------------------------------------------------------------------- #
@app.route("/periods", methods=["GET", "POST"])
@require("admin", "hr")
def periods():
    if request.method == "POST":
        name = request.form["name"].strip()
        g.db.execute(
            "INSERT INTO periods (name, start_date, end_date, status) VALUES (?,?,?,?)",
            (name, request.form.get("start_date"), request.form.get("end_date"), "draft"))
        log_audit(g.db, g.user["username"], "ADD_PERIOD", name)
        g.db.commit()
        flash(f"Period '{name}' created.", "ok")
        return redirect(url_for("periods"))
    rows = g.db.execute("SELECT * FROM periods ORDER BY id DESC").fetchall()
    return render_template("periods.html", rows=rows)


@app.route("/periods/<int:pid>/<action>")
@require("admin", "hr")
def period_action(pid, action):
    if action == "activate":
        g.db.execute("UPDATE periods SET status='active' WHERE id=?", (pid,))
    elif action == "close":
        g.db.execute("UPDATE periods SET status='closed' WHERE id=?", (pid,))
    log_audit(g.db, g.user["username"], "PERIOD_" + action.upper(), f"Period {pid}")
    g.db.commit()
    return redirect(url_for("periods"))


# --------------------------------------------------------------------------- #
# SR-02..06 Evaluator determination + approval — admin / hr
# --------------------------------------------------------------------------- #
@app.route("/evaluators")
@require("admin", "hr")
def evaluators():
    period = active_period()
    rows = g.db.execute(
        "SELECT a.*, ae.full_name AS assessee, ev.full_name AS evaluator "
        "FROM assignments a "
        "JOIN employees ae ON a.assessee_id=ae.id "
        "JOIN employees ev ON a.evaluator_id=ev.id "
        "WHERE a.period_id=? ORDER BY ae.full_name, a.relation_type", (period["id"],)
    ).fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["assessee"], []).append(r)
    return render_template("evaluators.html", grouped=grouped, period=period)


@app.route("/evaluators/generate")
@require("admin", "hr")
def evaluators_generate():
    period = active_period()
    n = generate_assignments(g.db, period["id"], actor=g.user["username"])
    g.db.commit()
    flash(f"Generated {n} evaluator assignments automatically (SR-02).", "ok")
    return redirect(url_for("evaluators"))


@app.route("/evaluators/<decision>")
@require("admin", "hr")
def evaluators_decide(decision):
    period = active_period()
    status = "approved" if decision == "approve" else "rejected"
    g.db.execute("UPDATE assignments SET approval_status=? WHERE period_id=?",
                 (status, period["id"]))
    log_audit(g.db, g.user["username"], "EVALUATOR_LIST_" + status.upper(),
              f"Period {period['id']}")
    if status == "approved":
        add_notification(g.db, "Evaluator list approved — forms distributed.", role="employee")
    g.db.commit()
    flash(f"Evaluator list {status}.", "ok")
    return redirect(url_for("evaluators"))


# --------------------------------------------------------------------------- #
# SR-06/07 Fill questionnaire — employee
# --------------------------------------------------------------------------- #
@app.route("/my-assignments")
@require("employee")
def my_assignments():
    period = active_period()
    rows = g.db.execute(
        "SELECT a.*, ae.full_name AS assessee FROM assignments a "
        "JOIN employees ae ON a.assessee_id=ae.id "
        "WHERE a.period_id=? AND a.evaluator_id=? AND a.approval_status='approved' "
        "ORDER BY a.relation_type",
        (period["id"], g.user["employee_id"])).fetchall()
    return render_template("my_assignments.html", rows=rows, period=period)


@app.route("/assess/<int:aid>", methods=["GET", "POST"])
@require("employee")
def assess(aid):
    a = g.db.execute(
        "SELECT a.*, ae.full_name AS assessee FROM assignments a "
        "JOIN employees ae ON a.assessee_id=ae.id WHERE a.id=?", (aid,)).fetchone()
    if not a or a["evaluator_id"] != g.user["employee_id"]:
        abort(403)
    if request.method == "POST":
        scores = {v: float(request.form[v]) for v in VALUES}
        g.db.execute(
            "INSERT INTO responses (assignment_id, amanah, kompeten, harmonis, loyal, "
            "adaptif, comment, submitted_at) VALUES (?,?,?,?,?,?,?,?)",
            (aid, scores["amanah"], scores["kompeten"], scores["harmonis"],
             scores["loyal"], scores["adaptif"], request.form.get("comment", ""), now()))
        g.db.execute("UPDATE assignments SET submitted=1 WHERE id=?", (aid,))
        add_notification(g.db, "A new assessment form was submitted.", role="hr")
        log_audit(g.db, g.user["username"], "SUBMIT_FORM", f"Assignment {aid}")
        g.db.commit()
        flash("Assessment submitted (anonymous).", "ok")
        return redirect(url_for("my_assignments"))
    return render_template("assess.html", a=a)


# --------------------------------------------------------------------------- #
# SR-08/09 Consolidate & generate results — admin / hr
# --------------------------------------------------------------------------- #
@app.route("/consolidate")
@require("admin", "hr")
def consolidate_route():
    period = active_period()
    consolidate(g.db, period["id"], actor=g.user["username"])
    g.db.commit()
    flash("Forms consolidated and scores recalculated (SR-08/09).", "ok")
    return redirect(url_for("results"))


@app.route("/results")
@require("admin", "hr", "management")
def results():
    period = active_period()
    rows = g.db.execute(
        "SELECT r.*, e.full_name, e.position FROM results r "
        "JOIN employees e ON r.employee_id=e.id WHERE r.period_id=? "
        "ORDER BY r.overall DESC", (period["id"],)).fetchall()
    return render_template("results.html", rows=rows, period=period)


# --------------------------------------------------------------------------- #
# Gap analysis + IDP — admin / hr / management
# --------------------------------------------------------------------------- #
@app.route("/gap")
@require("admin", "hr", "management")
def gap():
    period = active_period()
    emps = g.db.execute(
        "SELECT e.id, e.full_name FROM results r JOIN employees e ON r.employee_id=e.id "
        "WHERE r.period_id=? ORDER BY e.full_name", (period["id"],)).fetchall()
    sel = request.args.get("emp", type=int) or (emps[0]["id"] if emps else None)
    res = None
    if sel:
        res = g.db.execute("SELECT * FROM results WHERE period_id=? AND employee_id=?",
                           (period["id"], sel)).fetchone()
    return render_template("gap.html", emps=emps, sel=sel, res=res)


@app.route("/idp")
@require("admin", "hr", "management")
def idp():
    period = active_period()
    rows = g.db.execute(
        "SELECT r.*, e.full_name FROM results r JOIN employees e ON r.employee_id=e.id "
        "WHERE r.period_id=?", (period["id"],)).fetchall()
    cards = []
    for r in rows:
        gaps = [(VALUE_LABELS[v], round(r[v] - CORPORATE_TARGET, 2))
                for v in VALUES if r[v] < CORPORATE_TARGET]
        gaps.sort(key=lambda x: x[1])
        cards.append({"name": r["full_name"], "overall": r["overall"], "gaps": gaps})
    return render_template("idp.html", cards=cards)


# --------------------------------------------------------------------------- #
# SR-09/11/12 Reports — generate, archive, view, PDF
# --------------------------------------------------------------------------- #
@app.route("/reports")
@require("admin", "hr", "management")
def reports():
    rows = g.db.execute(
        "SELECT rp.*, p.name AS period_name FROM reports rp "
        "JOIN periods p ON rp.period_id=p.id ORDER BY rp.id DESC").fetchall()
    return render_template("reports.html", rows=rows)


@app.route("/reports/generate")
@require("admin", "hr")
def reports_generate():
    period = active_period()
    res = g.db.execute("SELECT * FROM results WHERE period_id=?", (period["id"],)).fetchall()
    title = f"Berita Acara Konsolidasi Nilai Akhir — {period['name']}"
    summary = f"{len(res)} employees consolidated."
    g.db.execute("INSERT INTO reports (period_id, title, summary, generated_at) VALUES (?,?,?,?)",
                 (period["id"], title, summary, now()))
    add_notification(g.db, "Final assessment report generated.", role="hr")
    add_notification(g.db, "Final assessment report is ready for review.", role="management")
    log_audit(g.db, g.user["username"], "GENERATE_REPORT", title)
    g.db.commit()
    flash("Report generated, archived, and sent to Management (SR-09/11/12).", "ok")
    return redirect(url_for("reports"))


@app.route("/reports/<int:rid>/pdf")
@require("admin", "hr", "management")
def report_pdf(rid):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    rp = g.db.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    if not rp:
        abort(404)
    rows = g.db.execute(
        "SELECT r.*, e.full_name, e.position FROM results r JOIN employees e "
        "ON r.employee_id=e.id WHERE r.period_id=? ORDER BY r.overall DESC",
        (rp["period_id"],)).fetchall()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    center = ParagraphStyle("c", parent=styles["Title"], fontSize=14, alignment=1)
    sub = ParagraphStyle("s", parent=styles["Normal"], alignment=1, textColor=colors.grey)
    el = [
        Paragraph("PT ENERGI NUSANTARA", center),
        Paragraph("DEPARTEMEN MANAJEMEN SUMBER DAYA MANUSIA (HRD)", sub),
        Spacer(1, 6),
        Paragraph("BERITA ACARA KONSOLIDASI EVALUASI KINERJA 360° (FORM SR-09)", sub),
        Spacer(1, 16),
        Paragraph(f"Document date: {rp['generated_at']}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Recapitulation of AKHLAK Core Values scores:", styles["Normal"]),
        Spacer(1, 8),
    ]
    header = ["Name"] + [VALUE_LABELS[v] for v in VALUES] + ["Overall"]
    data = [header]
    for r in rows:
        data.append([r["full_name"]] + [f"{r[v]:.2f}" for v in VALUES] + [f"{r['overall']:.2f}"])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1329")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    el += [t, Spacer(1, 40)]
    sign = Table([["Prepared by,", "Approved by,"],
                  ["Komite HR Korporat", "Head of HRD Corporate"],
                  ["(............................)", "(............................)"]],
                 colWidths=[8*cm, 8*cm])
    sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                              ("TOPPADDING", (0, 2), (-1, 2), 30)]))
    el.append(sign)
    doc.build(el)
    buf.seek(0)
    return Response(buf.read(), mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f"inline; filename=Berita_Acara_360_{rid}.pdf"})


# --------------------------------------------------------------------------- #
# Notifications / History / Audit / Feedback
# --------------------------------------------------------------------------- #
@app.route("/notifications")
@require("admin", "hr", "management", "employee")
def notifications():
    rows = g.db.execute(
        "SELECT * FROM notifications WHERE target_role=? OR target_user_id=? "
        "ORDER BY id DESC", (g.user["role"], g.user["id"])).fetchall()
    g.db.execute("UPDATE notifications SET is_read=1 WHERE target_role=? OR target_user_id=?",
                 (g.user["role"], g.user["id"]))
    g.db.commit()
    return render_template("notifications.html", rows=rows)


@app.route("/history")
@require("admin", "hr", "management")
def history():
    rows = g.db.execute(
        "SELECT p.name, p.status, p.start_date, p.end_date, "
        "COUNT(DISTINCT r.employee_id) AS n FROM periods p "
        "LEFT JOIN results r ON r.period_id=p.id GROUP BY p.id ORDER BY p.id DESC"
    ).fetchall()
    return render_template("history.html", rows=rows)


@app.route("/audit")
@require("admin")
def audit():
    rows = g.db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 200").fetchall()
    return render_template("audit.html", rows=rows)


@app.route("/feedback")
@require("employee")
def feedback():
    period = active_period()
    res = g.db.execute("SELECT * FROM results WHERE period_id=? AND employee_id=?",
                       (period["id"], g.user["employee_id"])).fetchone()
    comments = g.db.execute(
        "SELECT r.comment FROM responses r JOIN assignments a ON r.assignment_id=a.id "
        "WHERE a.period_id=? AND a.assessee_id=? AND r.comment != ''",
        (period["id"], g.user["employee_id"])).fetchall()
    return render_template("feedback.html", res=res, comments=comments, period=period)


@app.route("/profile", methods=["POST"])
@require("admin", "hr", "management", "employee")
def profile():
    name = request.form.get("display_name", "").strip()
    if name:
        g.db.execute("UPDATE users SET display_name=? WHERE id=?", (name, g.user["id"]))
        log_audit(g.db, g.user["username"], "UPDATE_PROFILE", name)
        g.db.commit()
        flash("Profile updated.", "ok")
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    import os
    if not os.path.exists("feedback360/feedback360.db") and not os.path.exists("feedback360.db"):
        pass
    app.run(debug=True)
