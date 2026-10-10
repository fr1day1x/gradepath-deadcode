# Gradepath

Animated React, Tailwind, Motion, and Three.js frontend connected to the supplied Flask grade engine. Python calculations are enabled by default.

## Run locally (PowerShell)

First-time setup (already completed in this workspace):

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Start both services:

```powershell
npm run dev
```

Open http://127.0.0.1:5173. This starts Vite on 5173 and Flask on 5000; Ctrl+C stops both. Both bind only to the local computer. `npm run dev:frontend` starts Vite alone.

To run the built frontend and API on one local server:

```powershell
npm run build
.\.venv\Scripts\python.exe -X utf8 backend/server.py
```

Then open http://127.0.0.1:5000. This is a local development server, not a production deployment.

## Integration

The zip's nested project and loose Python copies were identical. The complete nested project is in `backend/`, including its original UI and README. The supplied backend is retained and extended with validation, bonus-aware calculations, accounts, history, and planning.

- `backend/integration.py` adds `POST /api/predict`, validates the frontend Scenario, converts it into a policy, delegates grading to the supplied engine, and adapts its results.
- `backend/server.py` serves the React build and redirects `/policy-editor` into the Gradepath popup.
- Vite proxies `/api`, `/policy-editor`, and `/static` to Flask.
- `src/api.ts` requests predictions. `src/model.ts` defines the frontend contract and retains an explicit offline demo calculator.
- Slider, scores, weights, target requirements, category contributions, and chart use Python results. Chart uses 21 samples across the allowed final-score range, with connecting lines between them; the active point uses the exact prediction.
- Current grade applies selected course rules, excludes the pending final, and renormalizes active weights. The previous browser demo showed current grade before the drop rule, so current-grade values can change when connecting the backend.
- Required final scores round upwards to one decimal so the displayed requirement reaches the target.

Routes:

| Route | Purpose |
| --- | --- |
| GET /api/health | Connection status, including account service availability |
| POST /api/predict | Frontend Scenario to current, projected, required, contributions, curve |
| POST /api/calculate | Original `{ policy }` to full engine output |
| GET /api/sample | Teammate's sample syllabus |
| GET/POST /api/auth/policies | List/create/update account-owned presets |
| GET/DELETE /api/auth/policies/<id> | Load/delete an owned preset |
| /api/save and /api/saved | Retired (410); shared JSON files are no longer served |

## Accounts, advanced policies, and persistence

The landing page supports real account creation, sign-in, sign-out, and guest exploration. `backend/accounts.py` stores accounts in SQLite at `backend/instance/accounts.sqlite3` (created automatically and excluded from Git). Passwords use Werkzeug scrypt hashes. Sessions use revocable HttpOnly, SameSite cookies with a seven-day lifetime; authentication changes require a CSRF token, and login/registration attempts are rate limited. Accounts and sessions survive server restarts. No external service or API key is needed. Back up the database using SQLite backup tools; do not commit or share it.

Email verification and password recovery are not implemented. Registering an email does not verify ownership. This is a local hackathon setup, not a production account service.

Signed-in users start with an empty account workspace. Add a course, enter scores and rules in **Edit scores & policies**, then choose **Save recorded changes**. Courses persist in SQLite across logins. Existing account-owned presets appear as courses; they are not deleted or replaced by samples. Guest exploration retains sample courses in a separate session-only dashboard.

Each saved change creates an immutable grade-history revision with before/after scores, policy, engine results, timestamp, and explanation. Unchanged saves create no revision. Older presets begin history on their next change, preserving the prior calculation. Concurrent edits are checked by revision to prevent overwriting newer saves. The grade timeline explains corrections, curves, dropped scores, attendance, and replacement rules.

Attendance outlook previews the next present, late, or absent mark using the actual grading engine and recalculated drop allowance. Recording a mark saves it and creates history. What-if final sliders only calculate previews and never write records or history. The policy popup retains unsaved edits while open/closed within the current workspace; save before switching courses. Old `backend/saved/` JSON files are not automatically imported or shared.

Account API: `GET /api/auth/session` bootstraps a session and returns `{user, csrfToken}`. `POST /api/auth/register` accepts `{name,email,password}`; `POST /api/auth/login` accepts `{email,password}`; `POST /api/auth/logout` revokes the session. All POST requests require the session cookie and `X-CSRF-Token`. `GET /api/auth/me` requires a signed-in session. The frontend adapter is `src/auth.ts`.

Account profiles are private to their sessions. Grade prediction remains available to guests, and policy presets require authentication, ownership checks, and CSRF protection for changes. Signed-in course records and history are saved to the accounts database.

## Configuration

No `.env.local` is required. `.env.example` documents:

- `VITE_API_BASE_URL=/api`: grade service base URL.
- `VITE_DEMO_MODE=false`: set true only for explicit browser-only demo calculations.
- `VITE_AUTH_BASE_URL=/api`: same-origin account API.
- Backend `GRADEPATH_DATABASE`: optional absolute path to the SQLite database.
- Backend `GRADEPATH_SECURE_COOKIES=true`: require HTTPS cookies when deploying behind HTTPS. Local HTTP development should leave it unset. HTTPS login/register requests automatically receive Secure cookies based on their browser Origin.

VITE-prefixed variables are public in the browser bundle. Never store private keys there. Backend failures display an error and Retry connection button rather than silently reverting to demo calculations.

## Verification

```powershell
npm run build
npm test
.\.venv\Scripts\python.exe -X utf8 backend/test_engine.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend -p 'test_*.py'
```

With the dev services running and Chrome installed:

```powershell
node integration-check.mjs
node browser-check.mjs
node landing-check.mjs
node accounts-check.mjs
node space-check.mjs
```

Integration checks cover live Flask predictions, targets, charts, failure/retry, the original editor, save/load round-trips, and the built app served by Flask. Other browser checks cover mobile, score edits, guest entry and account registration/login/logout, and WebGL controls. Preview screenshots are ignored by Git. `accounts-check.mjs` creates a test account; run it against a disposable test database. Set `CHECK_URL` to override its default localhost:5173 target.

## Visual implementation

`src/BmoModel.ts` constructs an animated BMO-style calculator based on the supplied reference; `src/Astro.tsx` handles cursor tracking, blinking, idle movement, waving, happy expressions, and grade reactions with Three.js. It supports pause, reduced motion, pixel-density limits, hidden/offscreen rendering suspension, cleanup on unmount, and a WebGL fallback. `src/SpaceHero.tsx` defines the cinematic landing hero; `src/light.css` supplies the light-gray palette. No external character model or hosted embed is required.

## Score limits and bonus points

All numeric score inputs reject/clamp negatives; the API rejects invalid and nonfinite numbers. Normal scores stay within 0–100%. Explicit bonus switches on assignments, exams, and finals allow totals up to 199.99%; quizzes remain capped at 100%. Turning bonus off caps existing scores at 100%. Bonus scores are the total percentage including extra credit, not a second addition. Charts, final requirements, and best-possible grades account for bonus limits. Weights still total 100%, including attendance.

`policy-check.mjs` tests the rebuilt popup, bonus boundaries, save/load after refresh and mobile fit. It defaults to port 5001; point CHECK_URL at a disposable database because it creates a test account.

`history-check.mjs` verifies the empty account flow, saved scores, attendance, immutable history, hypothetical isolation, reload persistence, and mobile fit against a disposable database on port 5001.

## Improvement planning

Signed-in courses include **Best next steps**. Set the term end date, class weekdays, and excluded holiday dates in the policy editor. Remaining classes are counted from tomorrow through the end date (maximum two-year planning horizon), refreshed by the browser's local date daily and on window focus. This never creates attendance marks automatically.

Suggestions simulate full attendance or 80% on listed pending work with the actual grading engine, including drops, curves and final replacement. Only positive gains are shown. Estimated effort order is attendance, assignments, quizzes, exams, finals; within each tier, larger gains appear first. This is a transparent heuristic, not a personalized difficulty claim. Scenarios are independent; their gains cannot be summed. Recorded scores, retakes, and bonus opportunities are not assumed editable. After the term ends, no future-work actions are suggested. The authenticated `GET /api/auth/policies/<id>/plan?today=YYYY-MM-DD` endpoint checks course ownership and never writes history.

## Calendar export

Under Best next steps, open **Make time for your next step**. Export remaining classes (saved weekdays and exclusions), pending assignment/exam deadlines, or a chosen study session. Add due dates in the policy editor's per-category deadline section. Each event has an Add to Google Calendar link; bulk classes/deadlines and individual study sessions download as .ics files for manual import. Google Calendar imports files through Settings → Import & export. Review event details before saving.

Class times and study sessions use the device timezone and export as UTC; classes without a time and date-only deadlines are all-day reminders. Calendar exports never modify scores, attendance, or history. This is a snapshot export, not OAuth integration or synchronization: edits do not update imported events and repeated imports can create duplicates. No Google credentials are stored. `calendar-check.mjs` exercises this flow against a disposable database on port 5001.

Calendar format reference: https://www.rfc-editor.org/rfc/rfc5545 ; Google import help: https://support.google.com/calendar/answer/37118
