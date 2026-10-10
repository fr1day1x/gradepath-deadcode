# Syllabus What-If

CCSC:MW 2026 hackathon submission. A grade calculator that lets a student enter
a course policy and their scores, shows the current grade with the rules that
fired, and shows what is still possible on the final.

## Run

```bash
pip install flask
python app.py
# → http://127.0.0.1:5000
```

## Files

- `grade_engine.py` — Pure Python. All grading rules live here. No Flask, no I/O.
  Can be imported and tested on its own.
- `app.py` — Flask server. Validates input shape and delegates to the engine.
- `templates/index.html`, `static/style.css`, `static/script.js` — UI.
- `test_engine.py` — Runs the sample scenario and four variations against the engine.
  `python test_engine.py` must print `ALL TESTS PASSED`.

## Verified

- Sample scenario → **87.93%, B** (expected 87.9%, B)
- Quiz curve (92 → 100), drop lowest quiz (70), drop lowest 2 HW (50, 80),
  drop 1 attendance absence, weight renormalization over the 75% that has scores
- What-if: **A needs 88.11** (replacement rule beats 96.20), B needs 56.20,
  C needs 16.20, D is already locked in
- Best still possible: **95.85 (A)** with the exam replacement
- Variation: quiz 90 (not curved) → **86.93**
- Variation: only two HW scores (drop rule does not fire) → HW avg 95
- Variation: final = 95 (replacement helps) → **93.10, A**
- Variation: final = 70 (replacement does not help, 70 < 78) → **83.45**
- Variation: minimal syllabus with no attendance → correct renormalization

## Rules the engine handles

- Quiz curve: any completed score above a threshold is treated as a ceiling value
  before any drop rule fires.
- Drop lowest N in a category, only once at least M scores exist. Pending items
  are never the ones dropped. "Missing" items are 0 and are eligible for the drop.
- Equal weighting across items within a category (exams, quizzes, HW).
- Final-replace-lowest-in-category: applied only when it strictly improves the
  course grade. Current grade shows both numbers when it fires.
- Attendance: present=100, late=75, absent=0. Drop lowest `fraction × marks`,
  rounded to the nearest whole mark.
- Weight renormalization: categories with no completed/missing scores are left out
  of the current grade; their weight does not count. The final is treated this way
  until it is entered.
- Letter cutoffs are editable per course.

## Extras

- **Save and reload a policy.** Policies land in `./saved/<name>.json` and
  appear in the "Open saved…" dropdown. Round-trip is pure JSON — a saved
  policy is the same shape the engine accepts.
- **Load sample** button pre-fills Dr. Talaga's syllabus for a one-click demo.
- **Rule-fired breakdown** under the hero shows which items were curved,
  which were dropped, and which attendance marks were dropped — so a student
  can see why the number is what it is.
- **Absence buffer warning**: once the dropped-attendance capacity is spent on
  real absences, the next absence will count. The breakdown says so.
- **Both grades shown** when the final-replacement rule fires: without the rule
  and with the rule, with the delta.
- **No-manual UI**: the editor is on the right, results on the left, updates
  are live as you type. No save-to-recalculate.

## How to add a new rule

All grading logic is in `grade_engine.py`. To add a rule, either extend
`compute_category_average` (per-category rule) or add a step in `calculate`
(cross-category rule). The UI then exposes it through the policy JSON — no
template or Flask changes are needed if the field already fits the shape.
