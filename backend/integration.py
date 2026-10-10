"""Gradepath adapter. Delegates all grade calculations to the supplied engine."""
import math
from copy import deepcopy

from flask import Blueprint, jsonify, request
from grade_engine import calculate, _grade_at_final

bridge = Blueprint('gradepath', __name__)


def number(value, label, low=0, high=100):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be a finite number from {low} to {high}.')
    return float(value)


def to_policy(scenario):
    if not isinstance(scenario, dict) or not isinstance(scenario.get('course'), dict):
        raise ValueError('A course and scenario are required.')
    for key in ['replaceLowest', 'dropLowest']:
        if not isinstance(scenario.get(key), bool):
            raise ValueError(f'{key} must be a boolean.')
    number(scenario.get('finalScore'), 'Final score', high=199.99)
    number(scenario.get('target'), 'Target')
    course = scenario['course']
    cats = course.get('categories')
    if not isinstance(cats, list) or not 1 <= len(cats) <= 30:
        raise ValueError('Provide 1–30 categories.')
    ids, names, categories = set(), set(), []
    for cat in cats:
        if not isinstance(cat, dict):
            raise ValueError('Each category must be an object.')
        cid, name = cat.get('id'), cat.get('name')
        if not isinstance(cid, str) or not cid or cid in ids or not isinstance(name, str) or not name.strip() or name in names or len(name)>120:
            raise ValueError('Category identifiers and names must be unique, nonempty strings.')
        ids.add(cid); names.add(name)
        weight = number(cat.get('weight'), 'Category weight')
        scores = cat.get('scores')
        if not isinstance(scores, list) or len(scores)>1000:
            raise ValueError('Category scores must be a list of at most 1000 scores.')
        bonus=cat.get('bonus',False)
        if not isinstance(bonus,bool) or (bonus and cid not in ('homework','exam','final')): raise ValueError('Invalid bonus setting.')
        maximum=199.99 if bonus else 100
        if cid=='final': number(scenario['finalScore'],'Final score',high=maximum)
        scores = [number(score, 'Score',high=maximum) for score in scores]
        categories.append({
            'name': name, 'weight': weight, 'bonus':bonus,
            'items': [{'name': f'{name} {i+1}', 'score': score, 'status': 'scored'} for i, score in enumerate(scores)] if cid != 'final' else [{'name': 'Final exam', 'score': None, 'status': 'pending'}],
            'drop_lowest': 1 if cid == 'quiz' and scenario['dropLowest'] else 0,
            'drop_min_scores': 2,
        })
    if 'final' not in ids or abs(sum(c['weight'] for c in categories)-100)>.01:
        raise ValueError('A final category and weights totaling 100% are required.')
    return {'course_name':course.get('name','Course'), 'categories':categories,
            'letter_cutoffs':{'A':90,'B':80,'C':70,'D':60,'Target':scenario['target']},
            'final_category':next(c['name'] for c in cats if c['id']=='final'),
            'final_replaces':next((c['name'] for c in cats if c['id']=='exam'),None) if scenario['replaceLowest'] else None}


def predict(scenario):
    policy = to_policy(scenario)
    current = calculate(policy)
    projected_policy = deepcopy(policy)
    for cat in projected_policy['categories']:
        if cat['name'] == policy['final_category']:
            cat['items'] = [{'name':'Final exam','score':scenario['finalScore'],'status':'scored'}]
    projected = calculate(projected_policy)
    if current['current']['grade'] is None or projected['current']['grade'] is None:
        raise ValueError('Enter at least one completed score in a category with a positive weight.')
    detail = projected['current']['replacement_detail']
    contributions = []
    for cat in policy['categories']:
        avg = projected['categories'][cat['name']]['average']
        if detail and cat['name']==detail['replaced_in']:
            from grade_engine import _avg_with_lowest_replaced
            avg = _avg_with_lowest_replaced(cat, scenario['finalScore'])
        active = projected['current']['active_weight_total']
        contributions.append({'name':cat['name'],'average':avg or 0,'contribution':(avg or 0)*cat['weight']/active})
    needed = next(t['needed'] for t in current['what_if']['targets'] if t['letter']=='Target')
    # Round upwards to the UI's tenth of a point so the displayed target is sufficient.
    maximum=199.99 if next(c for c in policy['categories'] if c['name']==policy['final_category']).get('bonus') else 100
    needed = min(maximum, math.ceil(needed*10-1e-9)/10) if needed is not None else None
    averages = {name:cat['average'] for name,cat in current['categories'].items()}
    curve = [{'score':score,'grade':_grade_at_final(policy,averages,None,score,scenario['replaceLowest'])} for score in [round(i*maximum/20,4) for i in range(21)]]
    return {'current':current['current']['grade'],'projected':projected['current']['grade'],
            'required':needed,'contributions':contributions,'curve':curve,
            'rules':{'replacement':detail,'categories':projected['categories']},'source':'python-grade-engine'}


@bridge.post('/api/predict')
def api_predict():
    try:
        return jsonify(predict(request.get_json(silent=True)))
    except ValueError as error:
        return jsonify(error=str(error)),400


@bridge.get('/api/health')
def health():
    return jsonify(status='ok',engine='python-grade-engine',authentication=True)
