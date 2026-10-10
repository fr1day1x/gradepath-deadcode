import unittest
from copy import deepcopy
from test_accounts import AccountTests
from test_integration import scenario
from integration import predict
from validation import validate_policy
from app import SAMPLE_POLICY
from grade_engine import calculate

class PolicyTests(AccountTests):
    def test_private_presets(self):
        self.register()
        policy=deepcopy(SAMPLE_POLICY)
        saved=self.post('policies',{'name':'My course','policy':policy})
        self.assertEqual(saved.status_code,200)
        pid=saved.get_json()['id']
        self.assertEqual(self.client.get(f'/api/auth/policies/{pid}').get_json()['policy'],policy)
        self.assertEqual(self.post('policies',{'name':'My course','policy':policy}).status_code,409)
        self.assertEqual(self.client.post('/api/auth/policies',json={}).status_code,403)
        self.post('logout',{})
        self.assertEqual(self.client.get('/api/auth/policies').status_code,401)
        self.register('bob@example.com')
        self.assertEqual(self.client.get('/api/auth/policies').get_json()['policies'],[])
        self.assertEqual(self.client.get(f'/api/auth/policies/{pid}').status_code,404)
        self.assertEqual(self.post('policies',{'id':pid,'name':'stolen','policy':policy}).status_code,404)
        self.assertEqual(self.client.delete(f'/api/auth/policies/{pid}',json={},headers={'X-CSRF-Token':self.csrf}).status_code,404)
        self.post('logout',{});self.post('login',{'email':'alice@example.com','password':'correct horse battery'})
        policy['categories'][0]['items'][0]['score']=88
        self.assertEqual(self.post('policies',{'id':pid,'name':'Renamed','policy':policy}).status_code,200)
        restarted=self.make_app().test_client();restarted.set_cookie('gradepath_session',self.client.get_cookie('gradepath_session').value)
        self.assertEqual(restarted.get(f'/api/auth/policies/{pid}').get_json()['name'],'Renamed')
        self.assertEqual(self.client.delete(f'/api/auth/policies/{pid}',json={},headers={'X-CSRF-Token':self.csrf}).status_code,200)

class ScoreTests(unittest.TestCase):
    def test_bonus_boundaries(self):
        for value in [-.01,200,float('inf'),float('nan')]:
            s=scenario();s['course']['categories'][-1]['bonus']=True;s['finalScore']=value
            with self.assertRaises(ValueError):predict(s)
        s=scenario();s['course']['categories'][-1]['bonus']=True;s['finalScore']=199.99
        result=predict(s);self.assertGreater(result['projected'],100);self.assertEqual(result['curve'][-1]['score'],199.99)
        for index in [0,2]:
            s=scenario();s['course']['categories'][index]['bonus']=True;s['course']['categories'][index]['scores']=[150]
            self.assertGreater(predict(s)['current'],90)
        s=scenario();s['course']['categories'][1]['bonus']=True
        with self.assertRaises(ValueError):predict(s)
    def test_policy_bounds(self):
        for change in [lambda p:p['categories'][0]['items'][0].update(score=-1),lambda p:p['categories'][0].update(weight=-1),lambda p:p['categories'][0].update(curve_to=-1),lambda p:p['attendance'].update(drop_fraction=-.1),lambda p:p['letter_cutoffs'].update(A=-1)]:
            p=deepcopy(SAMPLE_POLICY);change(p)
            with self.assertRaises(ValueError):validate_policy(p)
        p=deepcopy(SAMPLE_POLICY);p['categories'][0]['bonus']=True;p['categories'][0]['items'][0]['score']=199.99;validate_policy(p)
        p['categories'][0]['items'][0]['score']=200
        with self.assertRaises(ValueError):validate_policy(p)
    def test_bonus_final_target(self):
        p={'categories':[{'name':'Work','weight':50,'items':[{'name':'Work','score':0,'status':'scored'}]},{'name':'Final','weight':50,'bonus':True,'items':[{'name':'Final','score':None,'status':'pending'}]}],'final_category':'Final','letter_cutoffs':{'A':90}}
        validate_policy(p);result=calculate(p)
        self.assertAlmostEqual(result['what_if']['targets'][0]['needed'],180)
        self.assertAlmostEqual(result['best_possible']['grade'],99.995)

if __name__=='__main__':unittest.main()
