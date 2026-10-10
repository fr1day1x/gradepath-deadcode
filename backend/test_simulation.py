import unittest
from copy import deepcopy
from app import SAMPLE_POLICY
from integration import simulate_policy

class SimulationTests(unittest.TestCase):
    def test_exact_sample_and_no_mutation(self):
        policy=deepcopy(SAMPLE_POLICY);before=deepcopy(policy)
        data=simulate_policy({'policy':policy,'score':95})
        self.assertAlmostEqual(data['point']['grade'],93.1)
        self.assertAlmostEqual(data['point']['without'],89.7)
        self.assertEqual(len(data['curve']),21)
        self.assertEqual(policy,before)
        self.assertAlmostEqual(data['curve'][19]['grade'],data['point']['grade'])

    def test_disabled_replacement_and_bonus_boundaries(self):
        policy=deepcopy(SAMPLE_POLICY);policy['final_replaces']=None
        data=simulate_policy({'policy':policy,'score':95})
        self.assertEqual(data['point']['grade'],data['point']['without'])
        final=next(c for c in policy['categories'] if c['name']==policy['final_category'])
        final['bonus']=True;final['kind']='final'
        self.assertEqual(simulate_policy({'policy':policy,'score':199.99})['curve'][-1]['score'],199.99)
        for score in [-1,200,float('nan')]:
            with self.assertRaises(ValueError):simulate_policy({'policy':policy,'score':score})

    def test_missing_final_and_pending_items(self):
        policy=deepcopy(SAMPLE_POLICY)
        policy['final_category']=None
        with self.assertRaises(ValueError):simulate_policy({'policy':policy,'score':80})
        policy=deepcopy(SAMPLE_POLICY)
        data=simulate_policy({'policy':policy,'score':70})
        self.assertEqual(data['point']['grade'],data['point']['without'])
        self.assertAlmostEqual(data['result']['categories']['Quizzes']['average'],90)
