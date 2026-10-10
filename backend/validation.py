"""Validation shared by calculations and account-owned policy presets."""
import math

def number(value, label, low=0, high=100):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'{label} must be a finite number from {low} to {high}.')
    return value

def validate_policy(policy):
    # UI limits are only convenience; every saved or calculated policy is checked here.
    if not isinstance(policy,dict): raise ValueError('A policy object is required.')
    cats=policy.get('categories')
    if not isinstance(cats,list) or not 1<=len(cats)<=30: raise ValueError('Use 1â€“30 categories.')
    names=set();total=0
    for cat in cats:
        if not isinstance(cat,dict): raise ValueError('Invalid category.')
        name=cat.get('name')
        if not isinstance(name,str) or not name.strip() or len(name)>120 or name in names: raise ValueError('Category names must be nonempty and unique.')
        names.add(name);total+=number(cat.get('weight'),'Weight')
        bonus=cat.get('bonus',False)
        if not isinstance(bonus,bool): raise ValueError('Bonus must be enabled or disabled.')
        kind=cat.get('kind','assignment')
        if kind not in ('assignment','quiz','exam','final'): raise ValueError('Invalid category type.')
        if bonus and kind=='quiz': raise ValueError('Quiz scores cannot exceed 100%.')
        maximum=199.99 if bonus else 100
        for key in ('drop_lowest','drop_min_scores'):
            value=number(cat.get(key,0),key,0,1000)
            if int(value)!=value: raise ValueError('Drop counts must be whole numbers.')
        for key in ('curve_above','curve_to'):
            if cat.get(key) is not None: number(cat[key],key,0,maximum)
        items=cat.get('items')
        if not isinstance(items,list) or len(items)>1000: raise ValueError('Use at most 1000 items per category.')
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get('name'),str) or not item['name'].strip(): raise ValueError('Each item needs a name.')
            if 'due_date' in item and not isinstance(item['due_date'],str): raise ValueError('Enter a valid deadline date.')
            if item.get('due_date'):
                from datetime import date
                try: date.fromisoformat(item['due_date'])
                except (ValueError,TypeError): raise ValueError('Enter a valid deadline date.')
            if item.get('status') not in ('scored','pending','missing'): raise ValueError('Invalid score status.')
            if item.get('score') is not None: number(item['score'],'Score',0,maximum)
            elif item['status']=='scored': raise ValueError('A recorded score is required; use Pending for ungraded work.')
    att=policy.get('attendance') or {}
    if not isinstance(att,dict): raise ValueError('Invalid attendance.')
    total+=number(att.get('weight',0),'Attendance weight')
    number(att.get('drop_fraction',0),'Attendance drop fraction',0,1)
    marks=att.get('marks',[])
    if not isinstance(marks,list) or len(marks)>1000 or any(m not in ('present','late','absent') for m in marks): raise ValueError('Invalid attendance marks.')
    # Attendance participates in the same 100% total as assignment/exam categories.
    if abs(total-100)>.01: raise ValueError('Category and attendance weights must total 100%.')
    cutoffs=policy.get('letter_cutoffs',{})
    if not isinstance(cutoffs,dict) or len(cutoffs)>20: raise ValueError('Invalid letter cutoffs.')
    for value in cutoffs.values(): number(value,'Letter cutoff')
    for key in ('final_category','final_replaces'):
        if policy.get(key) is not None and policy[key] not in names: raise ValueError('Select an existing final/replacement category.')
    if policy.get('final_category') and policy.get('final_category')==policy.get('final_replaces'): raise ValueError('The final cannot replace itself.')

    schedule=policy.get('schedule')
    if schedule is not None:
        from datetime import date
        if not isinstance(schedule,dict): raise ValueError('Invalid class schedule.')
        end=schedule.get('end_date','')
        if end:
            try: date.fromisoformat(end)
            except (ValueError,TypeError): raise ValueError('Enter a valid term end date.')
        days=schedule.get('weekdays',[])
        if not isinstance(days,list) or len(days)>7 or any(type(d) is not int or d<0 or d>6 for d in days) or len(set(days))!=len(days): raise ValueError('Select valid class weekdays.')
        excluded=schedule.get('excluded_dates',[])
        if not isinstance(excluded,list) or len(excluded)>366: raise ValueError('Use at most 366 excluded class dates.')
        for day in excluded:
            try: date.fromisoformat(day)
            except (ValueError,TypeError): raise ValueError('Enter valid excluded dates (YYYY-MM-DD).')
