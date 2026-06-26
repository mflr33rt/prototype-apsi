# Design Prototype mapping (for the re-presentation)

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