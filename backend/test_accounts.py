from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from flask import Flask
from werkzeug.security import check_password_hash
from accounts import COOKIE, init_accounts


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/'accounts.sqlite3')
        self.app=self.make_app()
        self.client=self.app.test_client()
        self.csrf=self.client.get('/api/auth/session').get_json()['csrfToken']

    def tearDown(self):
        self.temp.cleanup()

    def make_app(self):
        app=Flask(__name__)
        app.config.update(TESTING=True,ACCOUNT_DATABASE=self.path)
        init_accounts(app)
        return app

    def post(self,path,data,**kwargs):
        headers={'X-CSRF-Token':self.csrf,**kwargs.pop('headers',{})}
        response=self.client.post('/api/auth/'+path,json=data,headers=headers,**kwargs)
        token=response.get_json().get('csrfToken')
        if token:self.csrf=token
        return response

    def register(self,email='Alice@Example.com'):
        return self.post('register',{'name':'Alice','email':email,'password':'correct horse battery'})

    def test_registration_stores_hash_and_safe_profile(self):
        response=self.register()
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.get_json()['user']['email'],'alice@example.com')
        self.assertNotIn('password_hash',str(response.get_json()))
        with closing(sqlite3.connect(self.path)) as db:
            value=db.execute('SELECT password_hash FROM users').fetchone()[0]
        self.assertNotEqual(value,'correct horse battery')
        self.assertTrue(value.startswith('scrypt:'))
        self.assertTrue(check_password_hash(value,'correct horse battery'))
        self.assertIn('HttpOnly',response.headers['Set-Cookie'])
        self.assertIn('SameSite=Lax',response.headers['Set-Cookie'])
        self.assertEqual(self.client.get('/api/auth/me').status_code,200)

    def test_duplicate_case_insensitive(self):
        self.register()
        self.assertEqual(self.register(' ALICE@example.COM ').status_code,409)

    def test_logout_revokes_session_and_login_rotates(self):
        anonymous=self.client.get_cookie(COOKIE).value
        self.register()
        old=self.client.get_cookie(COOKIE).value
        self.assertNotEqual(old,anonymous)
        self.assertEqual(self.post('logout',{}).status_code,200)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        attacker=self.app.test_client();attacker.set_cookie(COOKIE,old)
        self.assertEqual(attacker.get('/api/auth/me').status_code,401)
        self.assertEqual(self.post('login',{'email':'alice@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('login',{'email':'alice@example.com','password':'correct horse battery'}).status_code,200)

    def test_csrf_and_anonymous_access(self):
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.client.post('/api/auth/register',json={'name':'A'}).status_code,403)
        self.assertEqual(self.client.post('/api/auth/login',json={},headers={'X-CSRF-Token':'wrong','Origin':'https://evil.example'}).status_code,403)

    def test_database_and_session_survive_restart(self):
        user=self.register().get_json()['user']
        cookie=self.client.get_cookie(COOKIE).value
        restarted=self.make_app().test_client();restarted.set_cookie(COOKIE,cookie)
        self.assertEqual(restarted.get('/api/auth/session').get_json()['user'],user)

    def test_secure_cookie_on_https_tunnel(self):
        response=self.post('register',{'name':'Alice','email':'a@example.com','password':'longpassword'},headers={'Origin':'https://example.loca.lt'})
        self.assertIn('Secure;',response.headers['Set-Cookie'])

    def test_validation_and_throttling(self):
        for password in ['short','x'*129]:
            self.assertEqual(self.post('register',{'name':'Alice','email':'a@example.com','password':password}).status_code,400)
        for _ in range(12):
            self.assertEqual(self.post('login',{'email':'nobody@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('login',{'email':'nobody@example.com','password':'wrong'}).status_code,429)

    def test_expired_session(self):
        self.register()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('UPDATE sessions SET expires_at=0');db.commit()
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertIsNone(self.client.get('/api/auth/session').get_json()['user'])


if __name__=='__main__':unittest.main()
