"""Immutable explanations and attendance previews, using the grading engine."""
from copy import deepcopy
from grade_engine import calculate

def explain(result):
    lines=[]
    for name,cat in result['categories'].items():
        for item in cat['curved']:lines.append(f"{name}: {item['name']} raised/curved from {item['from']:g}% to {item['to']:g}%.")
        for item in cat['dropped']:lines.append(f"{name}: dropped {item['name']} ({item['score']:g}%).")
        if cat['average'] is not None:lines.append(f"{name} average {cat['average']:.2f}%, syllabus weight {cat['weight']:g}%.")
    for mark in result['attendance']['dropped']:lines.append(f"Attendance: dropped mark {mark['index']+1} ({mark['status']}).")
    att=result['attendance']
    if att['average'] is not None:lines.append(f"Attendance average {att['average']:.2f}%, syllabus weight {att['weight']:g}%.")
    detail=result['current']['replacement_detail']
    if detail:lines.append(f"Final replaced {detail['replaced_score']:g}% with {detail['with_score']:g}% in {detail['replaced_in']}; course grade {detail['without']:.2f}% → {detail['with']:.2f}%.")
    if result['current']['grade'] is None:lines.append('No completed work with positive weight yet. A grade is not available.')
    else:lines.append(f"Current grade uses {result['current']['active_weight_total']:g}% of syllabus weight, renormalized over completed categories. Pending items are excluded; missing items count as zero.")
    return lines

def changes(before,after):
    # Entries are compared by position because the policy format has no stable item IDs.
    # The full snapshots below preserve the original data even after renaming or removal.
    if before is None:return ['Course created. No earlier grade history exists.'],['course']
    lines=[];kinds=set()
    for i in range(max(len(before['categories']),len(after['categories']))):
        a=before['categories'][i] if i<len(before['categories']) else None
        b=after['categories'][i] if i<len(after['categories']) else None
        if a is None or b is None:
            lines.append(f"Category {'added: '+b['name'] if b else 'removed: '+a['name']}.");kinds.add('policy');continue
        settings=lambda c:{k:v for k,v in c.items() if k!='items'}
        if settings(a)!=settings(b):lines.append(f"Policy settings changed for {b['name']} (including name, weight, bonus, curve or drop rules).");kinds.add('policy')
        def describe(item):
            if item is None:return 'not recorded'
            return f"{item['name']}: {str(item['score'])+'%' if item['status']=='scored' else item['status']}{'; due '+item['due_date'] if item.get('due_date') else ''}"
        for j in range(max(len(a['items']),len(b['items']))):
            x=a['items'][j] if j<len(a['items']) else None;y=b['items'][j] if j<len(b['items']) else None
            if x!=y:lines.append(f"{b['name']} entry {j+1}: {describe(x)} → {describe(y)}.");kinds.add('scores')
    aa=before.get('attendance') or {};bb=after.get('attendance') or {}
    for i in range(max(len(aa.get('marks',[])),len(bb.get('marks',[])))):
        a=aa.get('marks',[])[i] if i<len(aa.get('marks',[])) else 'not recorded';b=bb.get('marks',[])[i] if i<len(bb.get('marks',[])) else 'removed'
        if a!=b:lines.append(f'Attendance mark {i+1}: {a} → {b}.');kinds.add('attendance')
    if {k:v for k,v in aa.items() if k!='marks'}!={k:v for k,v in bb.items() if k!='marks'}:lines.append('Attendance weight or drop allowance changed.');kinds.add('policy')
    for key in ['course_name','letter_cutoffs','final_category','final_replaces','schedule']:
        if before.get(key)!=after.get(key):lines.append(f"{key.replace('_',' ').capitalize()} changed from {before.get(key)} to {after.get(key)}.");kinds.add('policy')
    return lines,sorted(kinds)

def event(before,after):
    # Recalculate both snapshots now. Historical results must not depend on later edits.
    prior=calculate(before) if before else None;result=calculate(after);diff,kinds=changes(before,after)
    return {'before_policy':before,'after_policy':after,'before_result':prior,'after_result':result,'changes':diff,'kinds':kinds,'explanations':explain(result)}

def attendance_preview(policy):
    # Copy for each branch so previews never append marks to the student's real record.
    current=calculate(policy);att=current['attendance'];variants={}
    for status in ('present','late','absent'):
        p=deepcopy(policy);a=p.setdefault('attendance',{});a['marks']=[*a.get('marks',[]),status]
        result=calculate(p)
        variants[status]={'grade':result['current']['grade'],'attendance_average':result['attendance']['average'],'drop_count':result['attendance']['n_dropped']}
    absent=variants['absent'];average=att['average']
    reduces=average is not None and absent['attendance_average']<average-1e-9
    return {'recorded':att['total_marks'],'drop_count':att['n_dropped'],'attendance_average':average,'weight':att['weight'],'next_absence_reduces_attendance':reduces,'next':variants}
