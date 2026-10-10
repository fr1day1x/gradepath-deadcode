"""
Pure grade calculation logic. No Flask, no I/O.

The engine takes a Policy (plain dict) and returns a result (plain dict),
which keeps everything JSON-serializable for the API layer.

Data model
----------
Policy = {
    "categories": [Category, ...],
    "attendance": {
        "weight": float,           # e.g. 5
        "marks": [str, ...],       # each "present" | "late" | "absent"
        "drop_fraction": float     # e.g. 0.05
    },
    "letter_cutoffs": {"A": 90, "B": 80, "C": 70, "D": 60},
    "final_category": str,         # name of the final-exam category (optional)
    "final_replaces": str          # name of category whose lowest the final can replace (optional)
}

Category = {
    "name": str,
    "weight": float,
    "items": [Item, ...],
    "drop_lowest": int,            # how many lowest completed items to drop (0 = none)
    "drop_min_scores": int,        # only drop once at least this many scores exist
    "curve_above": float | None,   # e.g. 90 (any completed score strictly above this...)
    "curve_to": float | None       # ...is treated as this value
}

Item = {
    "name": str,
    "score": float | None,         # None when not entered
    "status": str                  # "scored" | "pending" | "missing"  (missing counts as 0)
}

Blank is NOT zero. A pending item is remaining work.
"""

from copy import deepcopy

ATTENDANCE_VALUES = {"present": 100.0, "late": 75.0, "absent": 0.0}


# ---------------------------------------------------------------------------
# Category + attendance averages
# ---------------------------------------------------------------------------

def compute_category_average(category):
    """Return (avg or None, explanation dict) for one category.

    Rules fire in order: curve -> drop. Pending items are set aside.
    """
    items = category.get("items", [])
    curve_above = category.get("curve_above")
    curve_to = category.get("curve_to")
    drop_lowest = int(category.get("drop_lowest", 0) or 0)
    drop_min = int(category.get("drop_min_scores", 0) or 0)

    completed = []     # list of {name, original, effective, status}
    pending = []       # list of item names

    for item in items:
        status = item.get("status", "pending")
        if status == "scored" and item.get("score") is not None:
            completed.append({
                "name": item["name"],
                "original": float(item["score"]),
                "effective": float(item["score"]),
                "status": "scored",
            })
        elif status == "missing":
            completed.append({
                "name": item["name"],
                "original": 0.0,
                "effective": 0.0,
                "status": "missing",
            })
        else:
            pending.append(item["name"])

    # Curve
    curved = []
    if curve_above is not None and curve_to is not None:
        for c in completed:
            if c["status"] == "scored" and c["original"] > curve_above:
                c["effective"] = float(curve_to)
                curved.append({
                    "name": c["name"],
                    "from": c["original"],
                    "to": float(curve_to),
                })

    # Drop lowest
    dropped = []
    kept = completed
    if drop_lowest > 0 and len(completed) >= max(drop_min, 1):
        n = min(drop_lowest, len(completed))
        indexed = sorted(enumerate(completed), key=lambda x: x[1]["effective"])
        drop_idx = {i for i, _ in indexed[:n]}
        dropped = [{"name": completed[i]["name"], "score": completed[i]["effective"]}
                   for i in sorted(drop_idx)]
        kept = [c for i, c in enumerate(completed) if i not in drop_idx]

    explanation = {
        "has_scores": bool(kept),
        "pending": pending,
        "curved": curved,
        "dropped": dropped,
        "included": [{"name": c["name"], "score": c["effective"], "original": c["original"]}
                     for c in kept],
    }

    if not kept:
        explanation["average"] = None
        return None, explanation

    avg = sum(c["effective"] for c in kept) / len(kept)
    explanation["average"] = avg
    return avg, explanation


def compute_attendance_average(attendance):
    """Return (avg or None, explanation) for attendance marks."""
    marks = (attendance or {}).get("marks", [])
    frac = float((attendance or {}).get("drop_fraction", 0.05) or 0.0)

    if not marks:
        return None, {"has_scores": False, "average": None, "total_marks": 0,
                      "n_dropped": 0, "dropped": [], "included_count": 0}

    values = [{"index": i, "status": m, "score": ATTENDANCE_VALUES.get(m, 0.0)}
              for i, m in enumerate(marks)]
    n_drop = round(frac * len(values))

    dropped = []
    if n_drop > 0:
        order = sorted(range(len(values)), key=lambda i: values[i]["score"])
        drop_idx = set(order[:n_drop])
        dropped = [values[i] for i in sorted(drop_idx)]
        values = [v for i, v in enumerate(values) if i not in drop_idx]

    avg = sum(v["score"] for v in values) / len(values) if values else 0.0
    return avg, {
        "has_scores": True,
        "average": avg,
        "total_marks": len(marks),
        "n_dropped": n_drop,
        "dropped": dropped,
        "included_count": len(values),
    }


# ---------------------------------------------------------------------------
# Weighted roll-up (with weight renormalization)
# ---------------------------------------------------------------------------

def _weighted_grade(cat_averages, att_avg, policy):
    """Return (grade or None, {name: active_weight}) with renormalization."""
    active = {}
    total_w = 0.0

    for cat in policy["categories"]:
        if cat_averages.get(cat["name"]) is not None:
            active[cat["name"]] = float(cat["weight"])
            total_w += float(cat["weight"])

    att = policy.get("attendance") or {}
    att_w = float(att.get("weight", 0) or 0)
    if att_avg is not None and att_w > 0:
        active["__attendance__"] = att_w
        total_w += att_w

    if total_w == 0:
        return None, {}

    total = 0.0
    for cat in policy["categories"]:
        if cat["name"] in active:
            total += cat_averages[cat["name"]] * float(cat["weight"])
    if "__attendance__" in active:
        total += att_avg * att_w

    return total / total_w, active


def letter_for(grade, cutoffs):
    if grade is None:
        return None
    for letter, thresh in sorted(cutoffs.items(), key=lambda x: -x[1]):
        if grade >= thresh:
            return letter
    return "F"


# ---------------------------------------------------------------------------
# Final-replacement helpers
# ---------------------------------------------------------------------------

def _find_cat(policy, name):
    if not name:
        return None
    for c in policy["categories"]:
        if c["name"] == name:
            return c
    return None


def _lowest_completed_score(category):
    """Lowest raw score among completed items ('missing' counts as 0)."""
    scores = []
    for item in category.get("items", []):
        if item.get("status") == "scored" and item.get("score") is not None:
            scores.append(float(item["score"]))
        elif item.get("status") == "missing":
            scores.append(0.0)
    return min(scores) if scores else None


def _avg_with_lowest_replaced(category, replacement):
    """New average when the lowest completed score is replaced with `replacement`."""
    updated = deepcopy(category)
    completed = [item for item in updated.get('items', []) if item.get('status') == 'missing' or (item.get('status') == 'scored' and item.get('score') is not None)]
    if not completed:
        return None
    lowest = min(completed, key=lambda item: 0 if item['status']=='missing' else float(item['score']))
    lowest.update(score=replacement, status='scored')
    return compute_category_average(updated)[0]


def _grade_at_final(policy, cat_averages, att_avg, final_score, use_replacement):
    """Grade if the final is taken with `final_score`.

    `use_replacement=True` applies the replace-lowest-exam rule when it helps
    (i.e. when final_score strictly exceeds the lowest exam).
    """
    final_cat = _find_cat(policy, policy.get("final_category"))
    if final_cat is None:
        return None

    averages = dict(cat_averages)
    averages[final_cat["name"]] = float(final_score)

    if use_replacement:
        replace_cat = _find_cat(policy, policy.get("final_replaces"))
        if replace_cat is not None:
            lowest = _lowest_completed_score(replace_cat)
            if lowest is not None and final_score > lowest:
                averages[replace_cat["name"]] = _avg_with_lowest_replaced(replace_cat, final_score)

    grade, _ = _weighted_grade(averages, att_avg, policy)
    return grade


def final_maximum(policy):
    cat = _find_cat(policy, policy.get("final_category"))
    return 199.99 if cat and cat.get("bonus", False) else 100.0


def _solve_final_for_target(policy, cat_averages, att_avg, target, use_replacement):
    """Minimum final score in [0,100] that reaches `target`, else None."""
    g_hi = _grade_at_final(policy, cat_averages, att_avg, final_maximum(policy), use_replacement)
    if g_hi is None or g_hi < target:
        return None
    g_lo = _grade_at_final(policy, cat_averages, att_avg, 0.0, use_replacement)
    if g_lo is not None and g_lo >= target:
        return 0.0

    # Grade is monotonic non-decreasing in final_score for both pieces.
    lo, hi = 0.0, final_maximum(policy)
    for _ in range(80):
        mid = (lo + hi) / 2
        g = _grade_at_final(policy, cat_averages, att_avg, mid, use_replacement)
        if g is not None and g >= target:
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------------------
# What-if and best-possible
# ---------------------------------------------------------------------------

def compute_what_if(policy, cat_averages, att_avg):
    """For each letter cutoff, the min final score needed (with and without
    the replacement rule), plus 'already locked in' / 'not reachable' flags.
    Assumes other remaining non-final work stays unscored (current averages).
    """
    if not _find_cat(policy, policy.get("final_category")):
        return {"has_final": False, "targets": []}

    cutoffs = policy.get("letter_cutoffs", {})
    out = []
    for letter, target in sorted(cutoffs.items(), key=lambda x: -x[1]):
        without = _solve_final_for_target(policy, cat_averages, att_avg, target, False)
        with_rep = _solve_final_for_target(policy, cat_averages, att_avg, target, True)

        candidates = [c for c in [without, with_rep] if c is not None]
        needed = min(candidates) if candidates else None

        g_zero = _grade_at_final(policy, cat_averages, att_avg, 0.0, False)
        locked = g_zero is not None and g_zero >= target

        g_max = max(
            [v for v in [
                _grade_at_final(policy, cat_averages, att_avg, final_maximum(policy), False),
                _grade_at_final(policy, cat_averages, att_avg, final_maximum(policy), True),
            ] if v is not None],
            default=None,
        )
        not_reachable = g_max is not None and g_max < target

        out.append({
            "letter": letter,
            "target": target,
            "needed": needed,
            "needed_without_replacement": without,
            "needed_with_replacement": with_rep,
            "already_locked": locked,
            "not_reachable": not_reachable,
        })
    return {"has_final": True, "targets": out}


def compute_best_possible(policy):
    """Best achievable grade: all pending items set to 100, replacement applied if it helps."""
    p = deepcopy(policy)
    for cat in p["categories"]:
        for item in cat["items"]:
            if item.get("status") == "pending":
                item["status"] = "scored"
                item["score"] = 199.99 if cat.get("bonus", False) else 100.0

    cat_avgs = {}
    for cat in p["categories"]:
        avg, _ = compute_category_average(cat)
        cat_avgs[cat["name"]] = avg
    att_avg, _ = compute_attendance_average(p.get("attendance", {}))

    without, _ = _weighted_grade(cat_avgs, att_avg, p)

    final_cat = _find_cat(p, p.get("final_category"))
    replace_cat = _find_cat(p, p.get("final_replaces"))
    with_rep = None
    if final_cat and replace_cat and cat_avgs.get(final_cat["name"]) is not None:
        lowest = _lowest_completed_score(replace_cat)
        if lowest is not None and cat_avgs[final_cat["name"]] > lowest:
            alt = dict(cat_avgs)
            alt[replace_cat["name"]] = _avg_with_lowest_replaced(
                replace_cat, cat_avgs[final_cat["name"]])
            with_rep, _ = _weighted_grade(alt, att_avg, p)

    best = without
    used = False
    if with_rep is not None and (best is None or with_rep > best):
        best = with_rep
        used = True

    return {
        "grade": best,
        "letter": letter_for(best, p.get("letter_cutoffs", {})),
        "used_replacement": used,
    }


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def calculate(policy):
    """Compute current grade, per-rule explanations, what-if, and best possible."""
    cat_avgs = {}
    cat_expl = {}
    for cat in policy["categories"]:
        avg, expl = compute_category_average(cat)
        cat_avgs[cat["name"]] = avg
        cat_expl[cat["name"]] = expl

    att_avg, att_expl = compute_attendance_average(policy.get("attendance", {}))

    current, active = _weighted_grade(cat_avgs, att_avg, policy)

    # If the final has been taken, try the replacement rule for the CURRENT grade too.
    final_cat = _find_cat(policy, policy.get("final_category"))
    replace_cat = _find_cat(policy, policy.get("final_replaces"))
    used_rep = False
    rep_detail = None
    if (final_cat and replace_cat
            and cat_avgs.get(final_cat["name"]) is not None
            and current is not None):
        lowest = _lowest_completed_score(replace_cat)
        if lowest is not None and cat_avgs[final_cat["name"]] > lowest:
            alt = dict(cat_avgs)
            alt[replace_cat["name"]] = _avg_with_lowest_replaced(
                replace_cat, cat_avgs[final_cat["name"]])
            alt_grade, _ = _weighted_grade(alt, att_avg, policy)
            if alt_grade is not None and alt_grade > current:
                rep_detail = {
                    "without": current,
                    "with": alt_grade,
                    "replaced_in": replace_cat["name"],
                    "replaced_score": lowest,
                    "with_score": cat_avgs[final_cat["name"]],
                }
                current = alt_grade
                used_rep = True

    letter = letter_for(current, policy.get("letter_cutoffs", {}))

    categories_out = {}
    for cat in policy["categories"]:
        categories_out[cat["name"]] = {
            **cat_expl[cat["name"]],
            "weight": float(cat["weight"]),
            "active_weight": active.get(cat["name"]),
        }

    attendance_out = {
        **att_expl,
        "weight": float((policy.get("attendance") or {}).get("weight", 0) or 0),
        "active_weight": active.get("__attendance__"),
    }

    return {
        "current": {
            "grade": current,
            "letter": letter,
            "used_replacement": used_rep,
            "replacement_detail": rep_detail,
            "active_weight_total": sum(active.values()) if active else 0,
        },
        "categories": categories_out,
        "attendance": attendance_out,
        "what_if": compute_what_if(policy, cat_avgs, att_avg),
        "best_possible": compute_best_possible(policy),
        "letter_cutoffs": policy.get("letter_cutoffs", {}),
    }
