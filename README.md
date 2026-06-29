# 360° Core Values Assessment System

Group FRI-142

A working web application (not a static mockup) for the AKHLAK 360° performance
evaluation system designed in our APSI report. Built with **Flask + SQLite**, so
it has real login, role-based access, and a **central database** that persists and
is shared across users — the things a single HTML file could not provide.

## How to run

```bash
pip install -r requirements.txt
python database.py     # one-time: creates & seeds feedback360.db
python app.py          # starts server -> http://127.0.0.1:5000
```

Open the URL, then use a **Fast-Track Login** button on the sign-in page.

## Accounts

| Role        | Username         | Password         | Sees |
|-------------|------------------|------------------|------|
| Admin       | `admin`          | `ADMIN123SECURE` | everything incl. Audit Trail |
| HR          | `hr.supervisor`  | `SUPERVISOR456HR`| HR operations |
| Management  | `management`     | `MANAGE789VIEW`  | dashboard, results, reports (view only) |
| Employee/PM | `fahmi.muhammad` | `FAHMI33PM`      | fill assessments, own feedback |
| Employee    | `nadia.kunanti`  | `NADIA33TEAM`    | fill assessments, own feedback |
| Employee    | `sasi.azhari`    | `SASI123HR`      | fill assessments (still pending. use for the live demo) |

Passwords are stored **hashed** in the database, never in the page source.

## Suggested demo flow (matches SR-01 -> SR-12)

1. **HR** → Employee Data (add one) → Evaluation Period → Evaluator Approval →
   *Generate List* then *Approve & Distribute*.
2. **Employee `sasi.azhari`** → Fill Assessment → submit the AKHLAK form.
3. **HR** → Assessment Results → *Consolidate now* (scores recalculate live) →
   Gap Analysis → IDP → Evaluation Reports → *Generate Report* → Download PDF.
4. **Management** → log in to show the read-only report/dashboard view.
5. **Admin** → Audit Trail to show every action was logged.

To reset to the starting state, re-run `python database.py`.