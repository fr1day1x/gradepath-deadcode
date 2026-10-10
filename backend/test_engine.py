"""Tests the grade engine against the sample scenario and small variations."""
from grade_engine import calculate, compute_category_average, compute_attendance_average


def sample_policy():
    return {
        "categories": [
            {
                "name": "Quizzes", "weight": 15, "drop_lowest": 1, "drop_min_scores": 2,
                "curve_above": 90, "curve_to": 100,
                "items": [
                    {"name": "Q1", "score": 80, "status": "scored"},
                    {"name": "Q2", "score": 92, "status": "scored"},
                    {"name": "Q3", "score": 70, "status": "scored"},
                    {"name": "Q4", "score": None, "status": "pending"},
                ],
            },
            {
                "name": "Homework", "weight": 15, "drop_lowest": 2, "drop_min_scores": 3,
                "curve_above": None, "curve_to": None,
                "items": [
                    {"name": "H1", "score": 100, "status": "scored"},
                    {"name": "H2", "score": 90, "status": "scored"},
                    {"name": "H3", "score": 80, "status": "scored"},
                    {"name": "H4", "score": 50, "status": "scored"},
                ],
            },
            {
                "name": "Exams", "weight": 40, "drop_lowest": 0, "drop_min_scores": 0,
                "curve_above": None, "curve_to": None,
                "items": [
                    {"name": "Exam 1", "score": 78, "status": "scored"},
                    {"name": "Exam 2", "score": 88, "status": "scored"},
                ],
            },
            {
                "name": "Final", "weight": 25, "drop_lowest": 0, "drop_min_scores": 0,
                "curve_above": None, "curve_to": None,
                "items": [{"name": "Final", "score": None, "status": "pending"}],
            },
        ],
        "attendance": {
            "weight": 5, "drop_fraction": 0.05,
            "marks": ["present"] * 19 + ["absent"],
        },
        "letter_cutoffs": {"A": 90, "B": 80, "C": 70, "D": 60},
        "final_category": "Final",
        "final_replaces": "Exams",
    }


def approx(a, b, tol=0.05):
    return abs(a - b) <= tol


# --- Sample scenario ---------------------------------------------------------
p = sample_policy()
r = calculate(p)
print("=" * 60)
print("SAMPLE SCENARIO")
print("=" * 60)
print(f"Current grade: {r['current']['grade']:.2f}  (expected 87.93)")
print(f"Letter:        {r['current']['letter']}       (expected B)")
assert approx(r["current"]["grade"], 87.93), r["current"]["grade"]
assert r["current"]["letter"] == "B"

# Category spot checks
cats = r["categories"]
print(f"\nQuiz avg:     {cats['Quizzes']['average']:.2f}  (expected 90.00)")
print(f"  curved:     {cats['Quizzes']['curved']}")
print(f"  dropped:    {cats['Quizzes']['dropped']}")
assert approx(cats["Quizzes"]["average"], 90.0)
assert cats["Quizzes"]["curved"] == [{"name": "Q2", "from": 92.0, "to": 100.0}]
assert cats["Quizzes"]["dropped"] == [{"name": "Q3", "score": 70.0}]

print(f"\nHW avg:       {cats['Homework']['average']:.2f}  (expected 95.00)")
print(f"  dropped:    {cats['Homework']['dropped']}")
assert approx(cats["Homework"]["average"], 95.0)

print(f"\nExam avg:     {cats['Exams']['average']:.2f}  (expected 83.00)")
assert approx(cats["Exams"]["average"], 83.0)

print(f"\nAttendance:   {r['attendance']['average']:.2f}  (expected 100.00)")
print(f"  dropped:    {len(r['attendance']['dropped'])} mark(s)")
assert approx(r["attendance"]["average"], 100.0)
assert r["attendance"]["n_dropped"] == 1

# What-if
print("\n--- What-if (final needed for each letter) ---")
for t in r["what_if"]["targets"]:
    def fmt(x): return f"{x:.2f}" if x is not None else "n/a"
    need = fmt(t["needed"]) if not t["already_locked"] else "locked"
    print(f"  {t['letter']} ({t['target']}): need={need} "
          f"| without_rep={fmt(t['needed_without_replacement'])} "
          f"with_rep={fmt(t['needed_with_replacement'])}")

# Expected: A needs 88.11 (with replacement, since 88.11 > 78 and gives better path)
#          B needs 56.2
#          C needs 16.2
#          D already locked
targets = {t["letter"]: t for t in r["what_if"]["targets"]}
assert approx(targets["A"]["needed"], 88.11, tol=0.1), targets["A"]
assert approx(targets["B"]["needed"], 56.2, tol=0.1), targets["B"]
assert approx(targets["C"]["needed"], 16.2, tol=0.1), targets["C"]
assert targets["D"]["already_locked"], targets["D"]

# Best possible
print(f"\nBest possible: {r['best_possible']['grade']:.2f} ({r['best_possible']['letter']})"
      f" used_replacement={r['best_possible']['used_replacement']}")
# Q4=100, Final=100 -> replacement replaces 78 with 100, exam avg = 94
# Quizzes: [80, 100, 70, 100] -> curve nothing new -> drop 70 -> avg [80,100,100]=93.33
# Grade = (93.33*15 + 95*15 + 94*40 + 100*25 + 100*5)/100 = 9585/100 = 95.85
assert approx(r["best_possible"]["grade"], 95.85, tol=0.05), r["best_possible"]
assert r["best_possible"]["letter"] == "A"

print("\n[OK] Sample scenario passes.\n")


# --- Variation 1: quiz 90 instead of 92 (no longer curved to 100) ----------
print("=" * 60)
print("VARIATION 1: quiz 90 instead of 92")
print("=" * 60)
p1 = sample_policy()
p1["categories"][0]["items"][1]["score"] = 90  # Q2 = 90 exactly (not > 90)
r1 = calculate(p1)
# Quizzes: [80, 90, 70] no curve (90 is not > 90). Drop 70. avg [80,90] = 85.
# Grade = (85*15 + 95*15 + 83*40 + 100*5)/75 = (1275+1425+3320+500)/75 = 6520/75 = 86.933
print(f"Quiz avg:  {r1['categories']['Quizzes']['average']:.2f} (expected 85.00)")
print(f"Grade:     {r1['current']['grade']:.2f} (expected 86.93)")
assert approx(r1["categories"]["Quizzes"]["average"], 85.0)
assert approx(r1["current"]["grade"], 86.93, tol=0.05)
print("[OK]\n")


# --- Variation 2: only two homework scores (drop rule should NOT fire) ------
print("=" * 60)
print("VARIATION 2: only two homework scores entered")
print("=" * 60)
p2 = sample_policy()
# Only H1=100, H2=90, rest pending
p2["categories"][1]["items"] = [
    {"name": "H1", "score": 100, "status": "scored"},
    {"name": "H2", "score": 90, "status": "scored"},
    {"name": "H3", "score": None, "status": "pending"},
    {"name": "H4", "score": None, "status": "pending"},
]
r2 = calculate(p2)
# HW drop rule needs >= 3 scores, so no drop. avg = (100+90)/2 = 95.
print(f"HW avg:     {r2['categories']['Homework']['average']:.2f} (expected 95.00)")
print(f"HW dropped: {r2['categories']['Homework']['dropped']} (expected [])")
assert approx(r2["categories"]["Homework"]["average"], 95.0)
assert r2["categories"]["Homework"]["dropped"] == []
print("[OK]\n")


# --- Variation 3: final taken, replacement helps ---------------------------
print("=" * 60)
print("VARIATION 3: final = 95 (replaces lowest exam, helps)")
print("=" * 60)
p3 = sample_policy()
p3["categories"][3]["items"][0] = {"name": "Final", "score": 95, "status": "scored"}
r3 = calculate(p3)
# Without replacement: (90*15 + 95*15 + 83*40 + 95*25 + 100*5)/100
#   = (1350+1425+3320+2375+500)/100 = 8970/100 = 89.70
# With replacement: exam becomes (95+88)/2 = 91.5
#   = (90*15 + 95*15 + 91.5*40 + 95*25 + 100*5)/100
#   = (1350+1425+3660+2375+500)/100 = 9310/100 = 93.10
print(f"Grade: {r3['current']['grade']:.2f} (expected 93.10)")
print(f"used_replacement: {r3['current']['used_replacement']}")
print(f"replacement_detail: {r3['current']['replacement_detail']}")
assert approx(r3["current"]["grade"], 93.10, tol=0.05)
assert r3["current"]["used_replacement"] is True
assert r3["current"]["letter"] == "A"
print("[OK]\n")


# --- Variation 4: final taken, replacement does NOT help -------------------
print("=" * 60)
print("VARIATION 4: final = 70 (does not help, below lowest exam of 78)")
print("=" * 60)
p4 = sample_policy()
p4["categories"][3]["items"][0] = {"name": "Final", "score": 70, "status": "scored"}
r4 = calculate(p4)
# Without replacement: (90*15 + 95*15 + 83*40 + 70*25 + 100*5)/100
#   = (1350+1425+3320+1750+500)/100 = 8345/100 = 83.45
# With replacement: 70 < 78, so no replacement.
print(f"Grade: {r4['current']['grade']:.2f} (expected 83.45)")
print(f"used_replacement: {r4['current']['used_replacement']} (expected False)")
assert approx(r4["current"]["grade"], 83.45, tol=0.05)
assert r4["current"]["used_replacement"] is False
print("[OK]\n")


# --- Variation 5: simpler syllabus (no drops, no curve, no attendance) -----
print("=" * 60)
print("VARIATION 5: minimal syllabus (two categories only)")
print("=" * 60)
p5 = {
    "categories": [
        {"name": "Homework", "weight": 40, "drop_lowest": 0, "drop_min_scores": 0,
         "curve_above": None, "curve_to": None,
         "items": [
             {"name": "HW1", "score": 85, "status": "scored"},
             {"name": "HW2", "score": 95, "status": "scored"},
         ]},
        {"name": "Final", "weight": 60, "drop_lowest": 0, "drop_min_scores": 0,
         "curve_above": None, "curve_to": None,
         "items": [{"name": "Final", "score": None, "status": "pending"}]},
    ],
    "attendance": {"weight": 0, "drop_fraction": 0.0, "marks": []},
    "letter_cutoffs": {"A": 90, "B": 80, "C": 70, "D": 60},
    "final_category": "Final",
    "final_replaces": None,
}
r5 = calculate(p5)
# HW avg = 90. Only HW active, weight 40, renormalized -> grade = 90.
print(f"Grade:  {r5['current']['grade']:.2f} (expected 90.00)")
print(f"Letter: {r5['current']['letter']} (expected A)")
assert approx(r5["current"]["grade"], 90.0)
assert r5["current"]["letter"] == "A"
# What-if for A: grade with F=X is (90*40 + X*60)/100 = 36 + 0.6X. For >=90: X>=90.
targets5 = {t["letter"]: t for t in r5["what_if"]["targets"]}
print(f"Needed on final for A: {targets5['A']['needed']:.2f} (expected 90.00)")
assert approx(targets5["A"]["needed"], 90.0)
print("[OK]\n")


print("=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
