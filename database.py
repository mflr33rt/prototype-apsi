"""
Database layer for the 360 Core Values Assessment System.
Schema mirrors the Class/ERD diagram in the system design report:
Employee, EvaluatorAssignment, AssessmentForm(Response), AssessmentResult,
Report, Notification, AuditTrail  ->  plus Users, EvaluationPeriod.

SQLite is used as the central database so the app is genuinely multi-user
and persistent (a single shared .db file the Flask server reads/writes),
which is what a frontend-only file with localStorage could not be.
"""
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "feedback360.db")

# AKHLAK Core Values (6 indicators, including Kolaboratif).
# Order follows the AKHLAK acronym: Amanah, Kompeten, Harmonis, Loyal, Adaptif,
# Kolaboratif. Adding/removing a value here propagates through the seed, queries,
# CSV export and PDF automatically; only the SQL schema columns below are explicit.
VALUES = ["amanah", "kompeten", "harmonis", "loyal", "adaptif", "kolaboratif"]
VALUE_LABELS = {
    "amanah": "Amanah",
    "kompeten": "Kompeten",
    "harmonis": "Harmonis",
    "loyal": "Loyal",
    "adaptif": "Adaptif",
    "kolaboratif": "Kolaboratif",
}
CORPORATE_TARGET = 4.00  # standard each indicator is compared against


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,                -- admin | hr | management | employee
    employee_id INTEGER REFERENCES employees(id)
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nip TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    position TEXT NOT NULL,
    department TEXT NOT NULL,
    supervisor_id INTEGER REFERENCES employees(id)
);

CREATE TABLE periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft'   -- draft | active | closed
);

CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES periods(id),
    assessee_id INTEGER NOT NULL REFERENCES employees(id),
    evaluator_id INTEGER NOT NULL REFERENCES employees(id),
    relation_type TEXT NOT NULL,           -- self | supervisor | peer | subordinate
    approval_status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    submitted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
    amanah REAL, kompeten REAL, harmonis REAL, loyal REAL, adaptif REAL, kolaboratif REAL,
    comment TEXT,
    submitted_at TEXT
);

CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES periods(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    amanah REAL, kompeten REAL, harmonis REAL, loyal REAL, adaptif REAL, kolaboratif REAL,
    overall REAL,
    computed_at TEXT
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES periods(id),
    title TEXT NOT NULL,
    summary TEXT,
    generated_at TEXT
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_role TEXT,
    target_user_id INTEGER,
    message TEXT NOT NULL,
    created_at TEXT,
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT
);
"""


def log_audit(conn, username, action, detail=""):
    conn.execute(
        "INSERT INTO audit (username, action, detail, created_at) VALUES (?,?,?,?)",
        (username, action, detail, now()),
    )


def add_notification(conn, message, role=None, user_id=None):
    conn.execute(
        "INSERT INTO notifications (target_role, target_user_id, message, created_at) "
        "VALUES (?,?,?,?)",
        (role, user_id, message, now()),
    )


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = get_db()
    conn.executescript(SCHEMA)

    # --- Employees (the three real group members from the report) ---
    employees = [
        # nip, name, position, department, supervisor_nip
        ("102012340259", "Muhammad Fahmi", "Project Manager", "Project FRI-142", None),
        ("102012340269", "Nadia Kunanti", "Project Team", "Project FRI-142", "102012340259"),
        ("102012340370", "Sasi Azhari Kirana Putri", "Project Team", "Project FRI-142", "102012340259"),
        ("102012340401", "Budi Santoso", "Operations Manager", "Operations", None),
        ("102012340402", "Citra Dewi", "Operations Staff", "Operations", "102012340401"),
    ]
    nip_to_id = {}
    for nip, name, pos, dept, _ in employees:
        cur = conn.execute(
            "INSERT INTO employees (nip, full_name, position, department) VALUES (?,?,?,?)",
            (nip, name, pos, dept),
        )
        nip_to_id[nip] = cur.lastrowid
    for nip, _, _, _, sup_nip in employees:
        if sup_nip:
            conn.execute(
                "UPDATE employees SET supervisor_id=? WHERE id=?",
                (nip_to_id[sup_nip], nip_to_id[nip]),
            )

    # --- Users / accounts (passwords are hashed, never stored in the page) ---
    users = [
        ("admin", "ADMIN123SECURE", "Super Admin", "admin", None),
        ("hr.supervisor", "SUPERVISOR456HR", "Nadia HR Dept", "hr", None),
        ("management", "MANAGE789VIEW", "Board of Management", "management", None),
        ("fahmi.muhammad", "FAHMI33PM", "Muhammad Fahmi", "employee", "102012340259"),
        ("nadia.kunanti", "NADIA33TEAM", "Nadia Kunanti", "employee", "102012340269"),
        ("sasi.azhari", "SASI123HR", "Sasi Azhari Kirana Putri", "employee", "102012340370"),
    ]
    for uname, pw, dname, role, emp_nip in users:
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, role, employee_id) "
            "VALUES (?,?,?,?,?)",
            (uname, generate_password_hash(pw), dname, role,
             nip_to_id.get(emp_nip) if emp_nip else None),
        )

    # --- Active evaluation period ---
    pcur = conn.execute(
        "INSERT INTO periods (name, start_date, end_date, status) VALUES (?,?,?,?)",
        ("Evaluation Period 2026 - Semester 1", "2026-03-30", "2026-06-30", "active"),
    )
    period_id = pcur.lastrowid

    # --- Generate the 360 evaluator assignments for this period ---
    generate_assignments(conn, period_id, actor="system")
    # Pre-approve them so the demo starts mid-flow (as if supervisor approved)
    conn.execute("UPDATE assignments SET approval_status='approved' WHERE period_id=?", (period_id,))

    # --- Seed completed responses for Fahmi & Nadia (matches the report data),
    #     leave Sasi unfilled so the live "fill -> recalculate" demo works ---
    seed_scores = {
        "102012340259": [4.60, 4.20, 4.10, 4.70, 4.30, 4.40],  # Fahmi
        "102012340269": [4.10, 4.60, 4.30, 4.00, 4.50, 4.20],  # Nadia
        "102012340401": [4.50, 4.40, 4.20, 4.30, 4.10, 4.30],  # Budi (Operations)
        "102012340402": [3.90, 4.10, 4.00, 3.80, 4.20, 3.95],  # Citra (Operations)
    }
    for nip, scores in seed_scores.items():
        emp_id = nip_to_id[nip]
        rows = conn.execute(
            "SELECT id FROM assignments WHERE period_id=? AND assessee_id=?",
            (period_id, emp_id),
        ).fetchall()
        for r in rows:
            cols = ", ".join(VALUES)
            ph = ", ".join("?" * len(VALUES))
            conn.execute(
                f"INSERT INTO responses (assignment_id, {cols}, comment, submitted_at) "
                f"VALUES (?, {ph}, ?, ?)",
                (r["id"], *scores, "Seeded evaluation.", now()),
            )
            conn.execute("UPDATE assignments SET submitted=1 WHERE id=?", (r["id"],))

    consolidate(conn, period_id, actor="system")  # compute initial results

    # Previous (closed) period with historical results -> enables Performance Trends.
    prev = conn.execute(
        "INSERT INTO periods (name, start_date, end_date, status) VALUES (?,?,?,?)",
        ("Evaluation Period 2025 - Semester 2", "2025-09-01", "2025-12-31", "closed")
    ).lastrowid
    history_scores = {
        "102012340259": [4.30, 4.00, 3.90, 4.40, 4.10, 4.10],  # Fahmi (lower -> improved since)
        "102012340269": [3.80, 4.30, 4.00, 3.70, 4.20, 3.90],  # Nadia
        "102012340401": [4.20, 4.10, 4.00, 4.10, 3.90, 4.05],  # Budi
        "102012340402": [3.60, 3.90, 3.80, 3.60, 4.00, 3.70],  # Citra
    }
    for nip, sc in history_scores.items():
        eid = nip_to_id[nip]
        overall = round(sum(sc) / len(sc), 2)
        cols = ", ".join(VALUES)
        ph = ", ".join("?" * len(VALUES))
        conn.execute(
            f"INSERT INTO results (period_id, employee_id, {cols}, overall, computed_at) "
            f"VALUES (?, ?, {ph}, ?, ?)",
            (prev, eid, *sc, overall, now()))

    log_audit(conn, "system", "INIT", "Database initialised and seeded.")
    conn.commit()
    conn.close()
    print("Database initialised at", DB_PATH)


def generate_assignments(conn, period_id, actor="system"):
    """SR-02: auto-build the 360 evaluator list from the org structure."""
    # Clear dependents first (responses reference assignments) so regeneration is clean.
    conn.execute(
        "DELETE FROM responses WHERE assignment_id IN "
        "(SELECT id FROM assignments WHERE period_id=?)", (period_id,))
    conn.execute("DELETE FROM assignments WHERE period_id=?", (period_id,))
    emps = conn.execute("SELECT * FROM employees").fetchall()
    by_id = {e["id"]: e for e in emps}
    count = 0
    for assessee in emps:
        targets = []  # (evaluator_id, relation_type)
        targets.append((assessee["id"], "self"))                      # self
        if assessee["supervisor_id"]:
            targets.append((assessee["supervisor_id"], "supervisor"))  # supervisor
        # peers: same department, not self, not the supervisor relation
        for e in emps:
            if e["id"] == assessee["id"]:
                continue
            if e["department"] == assessee["department"] and e["id"] != assessee["supervisor_id"]:
                # subordinate if assessee supervises e, else peer
                rel = "subordinate" if e["supervisor_id"] == assessee["id"] else "peer"
                targets.append((e["id"], rel))
        for ev_id, rel in targets:
            conn.execute(
                "INSERT INTO assignments (period_id, assessee_id, evaluator_id, relation_type) "
                "VALUES (?,?,?,?)",
                (period_id, assessee["id"], ev_id, rel),
            )
            count += 1
    log_audit(conn, actor, "GENERATE_EVALUATORS",
              f"Generated {count} assignments for period {period_id}.")
    add_notification(conn, "Evaluator list generated and awaiting approval.", role="hr")
    return count


def consolidate(conn, period_id, actor="system"):
    """SR-08/09: consolidate submitted forms into one result per employee."""
    emps = conn.execute("SELECT * FROM employees").fetchall()
    conn.execute("DELETE FROM results WHERE period_id=?", (period_id,))
    for e in emps:
        rows = conn.execute(
            "SELECT r.* FROM responses r JOIN assignments a ON r.assignment_id=a.id "
            "WHERE a.period_id=? AND a.assessee_id=?",
            (period_id, e["id"]),
        ).fetchall()
        if not rows:
            continue
        avg = {v: round(sum(row[v] for row in rows) / len(rows), 2) for v in VALUES}
        overall = round(sum(avg.values()) / len(VALUES), 2)
        cols = ", ".join(VALUES)
        ph = ", ".join("?" * len(VALUES))
        conn.execute(
            f"INSERT INTO results (period_id, employee_id, {cols}, overall, computed_at) "
            f"VALUES (?, ?, {ph}, ?, ?)",
            (period_id, e["id"], *[avg[v] for v in VALUES], overall, now()),
        )
    log_audit(conn, actor, "CONSOLIDATE", f"Scores consolidated for period {period_id}.")


if __name__ == "__main__":
    init_db()
