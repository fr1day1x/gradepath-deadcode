"""Transparent effort heuristics; all impacts come from the actual grade engine."""
from copy import deepcopy
from datetime import date, timedelta
from grade_engine import calculate

def next_steps(policy, today=None):
    today=today or date.today()
    current=calculate(policy)['current']['grade']
    schedule=policy.get('schedule') or {}
    end=date.fromisoformat(schedule['end_date']) if schedule.get('end_date') else None
    dates=[]
    # Today is excluded: its class may already have happened. The browser supplies its local date.
    if end and end>today:
        excluded=set(schedule.get('excluded_dates',[]))
        for n in range(1,min((end-today).days,732)+1):
            d=today+timedelta(days=n)
            if d.weekday() in schedule.get('weekdays',[]) and d.isoformat() not in excluded:dates.append(d.isoformat())
    actions=[]
    # Compare independent scenarios, not cumulative gains. Omit actions that do not help.
    def add(title, effort, rank, changed, detail):
        after=calculate(changed)['current']['grade']
        if current is not None and after is not None and after>current+0.005:
            actions.append(dict(title=title,effort=effort,rank=rank,grade=after,gain=after-current,detail=detail))
    att=policy.get('attendance') or {}
    if dates and att.get('weight',0)>0 and len(att.get('marks',[]))+len(dates)<=1000:
        p=deepcopy(policy);p['attendance']['marks']=[*att.get('marks',[]),*(['present']*len(dates))]
        add(f"Attend the remaining {len(dates)} classes",'Lower estimated effort',0,p,'Assumes every remaining scheduled class is present. Drop allowances are recalculated; past absences stay unchanged.')
    if not end or end>=today:
        for i,cat in enumerate(policy['categories']):
            pending=[x for x in cat['items'] if x['status']=='pending']
            if not pending or cat['weight']<=0:continue
            p=deepcopy(policy)
            for item in p['categories'][i]['items']:
                if item['status']=='pending':item.update(status='scored',score=80)
            kind=cat.get('kind','assignment')
            # Difficulty is an explicit heuristic, not a prediction of this student's ability.
            rank={'assignment':1,'quiz':2,'exam':3,'final':4}[kind]
            add(f"Aim for 80% on remaining {cat['name']}", 'Moderate estimated effort' if rank<3 else 'Higher estimated effort',rank,p,f"Assumes 80% on {len(pending)} listed pending item(s). Other pending work stays ungraded. Confirm deadlines; difficulty varies by student.")
    actions.sort(key=lambda x:(x['rank'],-x['gain']))
    return dict(as_of=today.isoformat(),current=current,remaining_dates=dates,term_ended=bool(end and end<today),schedule_ready=bool(end and schedule.get('weekdays')),actions=actions[:6])
