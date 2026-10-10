GRADEPATH - CCSC:MW 2026 HACKATHON
Team: DeadCode | Knox College
Members: Kamlesh Kumar, Mohsin Asad, Eeman Naveed

OVERVIEW
Gradepath is a course-grade calculator and student planning application. It accepts
editable categories, weights, scores, pending/missing work, curves, drop rules,
attendance and final-exam replacement. The Flask engine calculates current grades,
letter grades, final-score targets and best-possible outcomes.

ADDITIONAL FEATURES
- Private accounts and multiple saved courses (SQLite).
- Revision history with before/after grades and preserved policy explanations.
- Attendance warnings and present/late/absent previews.
- Term dates, class weekdays, holiday exclusions and effort-based improvement plans.
- Optional bonus scores through 199.99% for assignments, exams and finals.
- Calendar exports for classes, deadlines and study sessions (Google links / .ics).
- Animated BMO-inspired companion and separate guest sample workspace.

REQUIREMENTS
Node.js 22.12+ (Node 24 LTS recommended), npm, Python 3.10+, modern browser.
Internet is needed for dependency installation and opening Google Calendar links.
The grade engine and account database run locally without an AI API key.

INSTALL AND RUN - WINDOWS POWERSHELL
1. Open a terminal in this repository.
2. npm ci
3. python -m venv .venv
4. .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
5. npm run dev
6. Open http://127.0.0.1:5173
Stop both services with Ctrl+C. Ports 5173 and 5000 must be free.

MAC / LINUX
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm run dev
Open http://127.0.0.1:5173.

SINGLE-SERVER BUILT APP
npm run build
Windows: .\.venv\Scripts\python.exe -X utf8 backend/server.py
Mac/Linux: .venv/bin/python backend/server.py
Open http://127.0.0.1:5000. This is a development server.

FIRST USE
Choose Create account for an empty private workspace, then Add course. Use
Edit scores & policies to enter the contest sample and Save recorded changes.
The database is created automatically at backend/instance/accounts.sqlite3.
No existing accounts, personal grades or database are included in the repository.
Guest exploration deliberately uses editable demo scores, not the contest sample.
The exact contest sample is also defined in backend/app.py and tested by test_engine.py.

TESTS
npm test
npm run build
Windows: .\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend -p 'test_*.py'
Mac/Linux: .venv/bin/python -m unittest discover -s backend -p 'test_*.py'
Browser checks require Chrome; see README.md for disposable database setup notes.

CODE MAP
src/Landing.tsx: account entry and guest/account routing
src/AccountWorkspace.tsx: saved courses, history, attendance and calendar navigation
src/PolicyEditor.tsx: editable draft rules and scores
src/ImprovementPlan.tsx, CourseCalendar.tsx, calendar.ts: planning and event exports
src/App.tsx, model.ts: separate guest scenarios and demo model
src/auth.ts, api.ts: browser API adapters
backend/grade_engine.py: pure grading calculations
backend/validation.py: server-side input checks
backend/accounts.py: accounts, ownership, SQLite transactions and revision checks
backend/history.py: explanations and immutable change snapshots
backend/planner.py: independent improvement scenarios and class dates
backend/server.py: combined frontend/API entrypoint
backend/app.py: supplied engine API and original sample
backend/integration.py: guest dashboard adapter

LIMITATIONS / ASSUMPTIONS
The improvement planner uses estimated effort and 80% on pending work; it is not
an AI predictor. Gains are independent and cannot be added together. Attendance
is manually recorded. Calendar exports are snapshots, not two-way sync.
Final targets assume other pending work remains ungraded; best-possible results
include remaining work. Email verification/password recovery are not implemented.
Guest scenario saves/exports and graphs differ from the signed-in workspace.

See README.md for additional technical details, References.txt for sources and
AI assistance, and Screenshots/ for feature images using demonstration data.
