import unittest
from copy import deepcopy
from test_accounts import AccountTests
from app import SAMPLE_POLICY
from history import attendance_preview

class HistoryTests(unittest.TestCase):
    setUp=AccountTests.setUp
    tearDown=AccountTests.tearDown
    make_app=AccountTests.make_app
    post=AccountTests.post
    register=AccountTests.register
    def test_history_snapshots_noops_and_conflicts(self):
        self.register()
        self.assertEqual(self.client.get('/api/auth/policies').get_json()['policies'],[])
        p=deepcopy(SAMPLE_POLICY)
        saved=self.post('policies',{'name':'Real course','policy':p}).get_json();pid=saved['id']
        first=self.client.get(f'/api/auth/policies/{pid}').get_json()
        self.assertEqual(len(first['history']),1)
        self.assertAlmostEqual(first['history'][0]['after_result']['current']['grade'],87.933333333333)
        self.assertTrue(any('Quiz 2' in s and '100' in s for s in first['explanations']))
        self.post('policies',{'id':pid,'name':'Real course','policy':p,'revision':1})
        self.assertEqual(len(self.client.get(f'/api/auth/policies/{pid}').get_json()['history']),1)
        p['categories'][0]['items'][1]['score']=90
        response=self.post('policies',{'id':pid,'name':'Real course','policy':p,'revision':1})
        self.assertEqual(response.get_json()['revision'],2)
        self.assertEqual(self.post('policies',{'id':pid,'name':'Real course','policy':p,'revision':1}).status_code,409)
        current=self.client.get(f'/api/auth/policies/{pid}').get_json()
        self.assertEqual(current['history'][1],first['history'][0])
        self.assertEqual(current['history'][0]['before_policy']['categories'][0]['items'][1]['score'],92)
        self.assertEqual(current['history'][0]['after_policy']['categories'][0]['items'][1]['score'],90)
        self.assertIn('scores',current['history'][0]['kinds'])
        p['attendance']['marks'].append('absent')
        self.post('policies',{'id':pid,'name':'Real course','policy':p,'revision':2})
        self.assertIn('attendance',self.client.get(f'/api/auth/policies/{pid}').get_json()['history'][0]['kinds'])
        self.post('logout',{});self.register('other@example.com')
        self.assertEqual(self.client.get(f'/api/auth/policies/{pid}').status_code,404)
    def test_attendance_preview_does_not_mutate(self):
        p=deepcopy(SAMPLE_POLICY);old=deepcopy(p);preview=attendance_preview(p)
        self.assertTrue(preview['next_absence_reduces_attendance'])
        self.assertEqual(preview['next']['absent']['attendance_average'],95)
        self.assertEqual(preview['next']['present']['attendance_average'],100)
        self.assertEqual(p,old)
        p['attendance']['marks']=['present']*28+['absent']
        preview=attendance_preview(p)
        self.assertEqual(preview['next']['absent']['drop_count'],2)
        self.assertEqual(preview['next']['absent']['attendance_average'],100)
    def test_empty_policy_has_no_fabricated_grade(self):
        self.register();p=deepcopy(SAMPLE_POLICY)
        for c in p['categories']:c['items']=[]
        p['attendance']['marks']=[]
        pid=self.post('policies',{'name':'New empty course','policy':p}).get_json()['id']
        result=self.client.get(f'/api/auth/policies/{pid}').get_json()
        self.assertIsNone(result['result']['current']['grade'])
        self.assertIsNone(result['history'][0]['after_result']['current']['grade'])

if __name__=='__main__':unittest.main()
