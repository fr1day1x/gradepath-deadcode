import unittest
from copy import deepcopy
from server import app
from integration import predict

def scenario():
    return {'course':{'id':'cs','name':'Data Structures','code':'CS 241','categories':[
        {'id':'homework','name':'Assignments','weight':25,'scores':[94,88,96,92,85]},
        {'id':'quiz','name':'Quizzes','weight':15,'scores':[85,90,78,95]},
        {'id':'exam','name':'Midterms','weight':30,'scores':[76,88]},
        {'id':'final','name':'Final exam','weight':30,'scores':[]}]},
        'finalScore':85,'target':90,'replaceLowest':True,'dropLowest':True}

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()

    def test_frontend_scenario(self):
        r=self.client.post('/api/predict',json=scenario())
        self.assertEqual(r.status_code,200)
        data=r.get_json()
        self.assertAlmostEqual(data['projected'],87.7)
        self.assertAlmostEqual(data['current'],86.92857142857)
        self.assertEqual(data['required'],90.2)
        self.assertAlmostEqual(sum(c['contribution'] for c in data['contributions']),data['projected'])
        self.assertAlmostEqual(data['curve'][17]['grade'],data['projected'])
        self.assertEqual(data['source'],'python-grade-engine')

    def test_switches_and_target(self):
        s=scenario();s['replaceLowest']=False;s['dropLowest']=False
        self.assertAlmostEqual(predict(s)['projected'],85.9)
        s['replaceLowest']=True;s['finalScore']=50
        a=predict(s);s['replaceLowest']=False
        self.assertEqual(a['projected'],predict(s)['projected'])
        s=scenario();required=predict(s)['required'];s['finalScore']=required
        self.assertGreaterEqual(predict(s)['projected'],90)
        s['finalScore']-=.1
        self.assertLess(predict(s)['projected'],90)

    def test_invalid_inputs(self):
        for invalid in [None, [], {}, {'course':None}]:
            self.assertEqual(self.client.post('/api/predict',json=invalid).status_code,400)
        for value in [-1,101,'85',True,float('nan')]:
            s=scenario();s['finalScore']=value
            self.assertEqual(self.client.post('/api/predict',json=s).status_code,400)
        s=scenario();s['course']['categories'][0]['weight']=30
        self.assertEqual(self.client.post('/api/predict',json=s).status_code,400)

    def test_original_api_and_editor(self):
        p=self.client.get('/api/sample').get_json()
        data=self.client.post('/api/calculate',json={'policy':p}).get_json()
        self.assertAlmostEqual(data['current']['grade'],87.9333333333)
        self.assertEqual(self.client.get('/policy-editor').status_code,302)
        self.assertEqual(self.client.get('/api/health').get_json()['authentication'],True)

if __name__=='__main__':unittest.main()
