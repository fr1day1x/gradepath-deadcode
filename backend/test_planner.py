import unittest
from datetime import date
from copy import deepcopy
from planner import next_steps
from validation import validate_policy

class PlannerTests(unittest.TestCase):
    def policy(self):
        return dict(categories=[dict(name='Assignments',kind='assignment',weight=80,items=[dict(name='One',status='scored',score=60),dict(name='Two',status='pending',score=None)])],attendance=dict(weight=20,drop_fraction=0,marks=['absent','present']),schedule=dict(end_date='2026-10-16',weekdays=[0,2,4],excluded_dates=['2026-10-12']),letter_cutoffs={'A':90},final_category=None,final_replaces=None)
    def test_schedule_ranking_impact_and_no_mutation(self):
        p=self.policy();before=deepcopy(p);plan=next_steps(p,date(2026,10,9))
        self.assertEqual(plan['remaining_dates'],['2026-10-14','2026-10-16'])
        self.assertEqual(plan['actions'][0]['rank'],0)
        self.assertAlmostEqual(plan['actions'][0]['gain'],5)
        self.assertAlmostEqual(plan['actions'][1]['gain'],8)
        self.assertEqual(p,before)
    def test_ended_empty_and_nonbeneficial(self):
        p=self.policy();self.assertEqual(next_steps(p,date(2026,10,17))['actions'],[])
        p['attendance']['marks']=['present'];p['categories'][0]['items'][0]['score']=100
        self.assertEqual(next_steps(p,date(2026,10,9))['actions'],[])
        p['attendance']['marks']=[];p['categories'][0]['items']=[]
        self.assertEqual(next_steps(p,date(2026,10,9))['actions'],[])
    def test_validation(self):
        p=self.policy();validate_policy(p)
        for schedule in [{'end_date':'bad'}, {'weekdays':[True]}, {'excluded_dates':['2026-02-30']}, {'weekdays':[1,1]}]:
            p['schedule']=schedule
            with self.assertRaises(ValueError):validate_policy(p)
    def test_no_schedule_and_daily_rollover(self):
        p=self.policy();self.assertEqual(next_steps(p,date(2026,10,14))['remaining_dates'],['2026-10-16'])
        p.pop('schedule');self.assertEqual(next_steps(p,date(2026,10,9))['actions'][0]['rank'],1)
