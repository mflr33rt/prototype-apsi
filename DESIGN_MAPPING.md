# Design-Prototype mapping (for the re-presentation)

The previous note was "prototype features ≠ system design." This table shows every
designed requirement now backed by a real, database-driven screen.

| Design ref | Feature / Screen | System Requirement | DB table(s) |
|------------|------------------|--------------------|-------------|
| Login | Sign-in (hashed pw, role redirect) | auth | users |
| Employee Data | Employee Data (CRUD) | SR-01 | employees |
| Evaluation Period | Evaluation Period (create/activate/close) | — | periods |
| Evaluator Determination | Evaluator Approval → *Generate List* | SR-02 | assignments |
| Evaluator List Approval | Evaluator Approval → *Approve/Reject* | SR-03, SR-04, SR-05 | assignments |
| Assessment Form / Input | Fill Assessment (AKHLAK form) | SR-06, SR-07 | assignments, responses |
| Assessment Calculation | Results → *Consolidate now* | SR-08 | responses → results |
| Assessment Results | Assessment Results table | SR-09 | results |
| Gap Analysis | Gap Analysis (radar vs target) | analysis | results |
| IDP Recommendations | IDP Recommendations | analysis | results |
| Evaluation Reports | Reports → generate + PDF | SR-09, SR-11, SR-12 | reports |
| Notifications | Notifications centre | SR-10 | notifications |
| Evaluation History | Evaluation History (per period) | history | periods, results |
| Audit Trail | Audit Trail (every action logged) | transparency | audit |
| Employee Feedback | My Feedback (own scores + comments) | feedback | results, responses |

**Roles (Table 12 / use case):** HR-Admin, Employee/Evaluator, and **Management**
are all implemented as distinct, gated views — the Management view that was missing
before now exists.

**ERD coverage:** Employee, EvaluatorAssignment (`assignments`), AssessmentForm
(`responses`), AssessmentResult (`results`), Report, Notification, AuditTrail all
exist as real tables with the documented relationships.

## Added to resolve the use-case feedback (round 2)

| Use-case item | Where it is now | Role |
|---------------|-----------------|------|
| Employee → view own IDP | **My IDP** menu | employee |
| Management → performance trends | **Performance Trends** (line chart across periods) | management/admin/hr |
| Management → department comparison | **Department Comparison** (chart + table) | management/admin/hr |
| Management → IDP summary | **IDP Summary** (the IDP screen, relabelled for Management) | management |
| Evaluator → assigned / fill / submit | **Fill Assessment** — evaluator = an employee (Nadia/Sasi/Fahmi) signs in to assess others | employee |
| Admin/HR → audit trail | **Audit Trail** now visible to HR as well as Admin | admin/hr |
| Admin/HR → send reminder | **Notifications → Send Reminders** (nudges evaluators with pending forms) | admin/hr |

Seed note: a closed period (2025 Sem 2) and a second department (Operations) were added
so Performance Trends and Department Comparison show real data out of the box.

## Full use-case coverage audit (against the use-case diagram)

Every ellipse in the diagram, mapped to the screen/action that implements it.

### Actor: employee (self-assessor)
| Use case | Implemented as |
|----------|----------------|
| login | Login |
| view dashboard | **My Dashboard** (personal) |
| view personal assessment result | **My Results** (scores + radar) |
| view feedback | **My Feedback** (anonymous comments) |
| view IDP | **My IDP** |
| receive notification | Notifications |

### Actor: HR / ADMIN
| Use case | Implemented as |
|----------|----------------|
| login | Login |
| manage employee data | Employee Data (CRUD) |
| manage evaluation data | Evaluation Period (create/activate/close) |
| generate evaluator assignment (incl. determine self/supervisor/peer/subordinate) | Evaluator Approval → Generate List |
| review & approve evaluator list | Evaluator Approval → Approve/Reject |
| monitor assessment progress (incl. dashboard & real-time) | Dashboard (total/done/pending/participation) |
| manage notification (incl. send reminder & status update) | Notifications → Send Reminders |
| generate reports (incl. calculate score) | Reports → Generate Report |
| calculate score (automatic recap) | Results → Consolidate now |
| generate IDP recommendation (incl. based on result & gap) | IDP Recommendations |
| view audit trail | Audit Trail |
| export data | **Export Data (CSV)** |

### Actor: evaluator (supervisor, peer, subordinate)
| Use case | Implemented as |
|----------|----------------|
| login | Login (as any employee — evaluator = an employee) |
| view assigned assessment | Fill Assessment (list of people assigned to you) |
| fill assessment form | Assessment Form (AKHLAK indicators) |
| submit assessment (incl. validate data) | Submit (required-field validation) |

### Actor: management (viewer)
| Use case | Implemented as |
|----------|----------------|
| login | Login |
| view dashboard | Dashboard |
| view performance report | Evaluation Reports |
| view performance trend | Performance Trends |
| view department comparison | Department Comparison |
| view gap analysis result | Gap Analysis |
| view IDP summary | IDP Summary |
| export / download report | Reports → Download PDF |

All four actors' use cases are now covered. "export data" (HR, raw CSV) and
"export / download report" (Management, formatted PDF) are deliberately separate,
matching the two distinct ellipses in the diagram.
