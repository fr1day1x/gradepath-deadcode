from contextlib import closing
"""SQLite accounts and revocable, server-side sessions for Gradepath."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

auth = Blueprint('accounts', __name__, url_prefix='/api/auth')
COOKIE = 'gradepath_session'
SESSION_SECONDS = 7 * 24 * 60 * 60


def database():
    if 'accounts_db' not in g:
        g.accounts_db = sqlite3.connect(current_app.config['ACCOUNT_DATABASE'], timeout=10)
        g.accounts_db.row_factory = sqlite3.Row
        g.accounts_db.execute('PRAGMA foreign_keys = ON')
    return g.accounts_db


def init_accounts(app):
    app.config.setdefault('ACCOUNT_DATABASE', os.environ.get('GRADEPATH_DATABASE') or str(Path(__file__).parent/'instance'/'accounts.sqlite3'))
    Path(app.config['ACCOUNT_DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(app.config['ACCOUNT_DATABASE'])) as db:
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                policy_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(user_id,name)
            );
            CREATE TABLE IF NOT EXISTS grade_history (
                id INTEGER PRIMARY KEY,
                policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
                recorded_at TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_json TEXT NOT NULL,
                UNIQUE(policy_id,revision)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                csrf_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_attempts (
                bucket TEXT NOT NULL,
                attempted_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS attempts_bucket_time ON auth_attempts(bucket, attempted_at);
        ''')

        if 'revision' not in [r[1] for r in db.execute('PRAGMA table_info(policies)')]:
            db.execute('ALTER TABLE policies ADD COLUMN revision INTEGER NOT NULL DEFAULT 1')
        db.commit()

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop('accounts_db', None)
        if db is not None:
            db.close()

    app.register_blueprint(auth)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def session_record():
    token = request.cookies.get(COOKIE, '')
    if not token or len(token)>200:
        return None
    return database().execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?',
                              (digest(token), int(time.time()))).fetchone()


def public_user(user_id):
    if user_id is None:
        return None
    row = database().execute('SELECT id, name, email FROM users WHERE id=?', (user_id,)).fetchone()
    return dict(row) if row else None


def issue_session(user_id=None):
    db=database()
    old=request.cookies.get(COOKIE)
    if old:
        db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(old),))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now=int(time.time())
    db.execute('DELETE FROM sessions WHERE expires_at<=?',(now,))
    db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(digest(token),user_id,csrf,now+SESSION_SECONDS))
    db.commit()
    response=jsonify(user=public_user(user_id),csrfToken=csrf)
    # HTTPS browser origins (including the tunnel) receive Secure cookies.
    secure=request.is_secure or request.headers.get('Origin','').startswith('https://') or os.environ.get('GRADEPATH_SECURE_COOKIES')=='true'
    response.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,httponly=True,samesite='Lax',secure=secure,path='/')
    return response


@auth.after_request
def no_cache(response):
    response.headers['Cache-Control']='no-store'
    return response


@auth.before_request
def csrf_guard():
    if request.method not in ('POST','PUT','PATCH','DELETE'):
        return None
    record=session_record()
    submitted=request.headers.get('X-CSRF-Token','')
    if not record or not submitted or not secrets.compare_digest(submitted,record['csrf_token']):
        return jsonify(error='Your session expired. Refresh and try again.'),403
    if not request.is_json:
        return jsonify(error='Send a JSON request.'),415


@auth.get('/session')
def get_session():
    record=session_record()
    if record:
        return jsonify(user=public_user(record['user_id']),csrfToken=record['csrf_token'])
    return issue_session()


def credentials(register=False):
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        raise ValueError('Enter your account details.')
    email=data.get('email')
    password=data.get('password')
    if not isinstance(email,str) or len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()):
        raise ValueError('Enter a valid email address.')
    if not isinstance(password,str) or not 1<=len(password)<=128:
        raise ValueError('Enter a password of at most 128 characters.')
    name=data.get('name','')
    if register:
        if not isinstance(name,str) or not 1<=len(name.strip())<=80:
            raise ValueError('Enter a name of 1–80 characters.')
        if len(password)<8:
            raise ValueError('Use at least 8 characters for your password.')
    return email.strip().casefold(),password,name.strip() if isinstance(name,str) else ''


def limited(email):
    """Persistent throttling; do not trust client-controlled forwarded IP headers."""
    now=int(time.time());db=database()
    buckets=[(digest('email:'+email),12),(digest('ip:'+(request.remote_addr or 'unknown')),120)]
    db.execute('BEGIN IMMEDIATE')
    db.execute('DELETE FROM auth_attempts WHERE attempted_at<?',(now-900,))
    for bucket,maximum in buckets:
        count=db.execute('SELECT COUNT(*) FROM auth_attempts WHERE bucket=?',(bucket,)).fetchone()[0]
        if count>=maximum:
            db.commit()
            return True
    db.executemany('INSERT INTO auth_attempts VALUES (?,?)',[(b,now) for b,_ in buckets]);db.commit()
    return False


@auth.post('/register')
def register():
    try:
        email,password,name=credentials(register=True)
    except ValueError as error:
        return jsonify(error=str(error)),400
    if limited(email):
        return jsonify(error='Too many attempts. Please try again in 15 minutes.'),429
    password_hash=generate_password_hash(password,method='scrypt')
    db=database()
    try:
        cursor=db.execute('INSERT INTO users(email,name,password_hash,created_at) VALUES(?,?,?,?)',
                          (email,name,password_hash,int(time.time())))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error='An account with this email already exists. Sign in instead.'),409
    return issue_session(cursor.lastrowid),201


# The dummy hash keeps password checking work similar for unknown accounts.
DUMMY_HASH=generate_password_hash(secrets.token_urlsafe(32),method='scrypt')


@auth.post('/login')
def login():
    try:
        email,password,_name=credentials()
    except ValueError as error:
        return jsonify(error=str(error)),400
    if limited(email):
        return jsonify(error='Too many attempts. Please try again in 15 minutes.'),429
    row=database().execute('SELECT id,password_hash FROM users WHERE email=?',(email,)).fetchone()
    matches=check_password_hash(row['password_hash'] if row else DUMMY_HASH,password)
    if not row or not matches:
        return jsonify(error='That email and password combination wasn’t recognized.'),401
    return issue_session(row['id'])


@auth.post('/logout')
def logout():
    return issue_session()  # Revokes the signed-in session and rotates to an anonymous one.


@auth.get('/me')
def me():
    record=session_record()
    user=public_user(record['user_id']) if record else None
    if user is None:
        return jsonify(error='Sign in to access your account.'),401
    return jsonify(user=user)


@auth.route('/policies', methods=['GET','POST'])
def policies():
    record=session_record()
    if not record or record['user_id'] is None:
        return jsonify(error='Sign in to save or load your personal policies.'),401
    user_id=record['user_id'];db=database()
    if request.method=='GET':
        return jsonify(policies=[dict(r) for r in db.execute('SELECT id,name,updated_at,revision FROM policies WHERE user_id=? ORDER BY updated_at DESC,id DESC',(user_id,))])
    data=request.get_json(silent=True)
    if not isinstance(data,dict):return jsonify(error='A policy is required.'),400
    name=data.get('name');policy=data.get('policy')
    try:
        if not isinstance(name,str) or not 1<=len(name.strip())<=120:raise ValueError('Use a preset name of 1-120 characters.')
        from validation import validate_policy
        validate_policy(policy)
    except ValueError as error:return jsonify(error=str(error)),400
    policy_id=data.get('id')
    if policy_id is not None and (type(policy_id) is not int or policy_id<1): return jsonify(error='Invalid policy identifier.'),400
    from history import event
    from datetime import datetime, timezone
    # Lock before checking the revision: two tabs must not both save over the same version.
    db.execute('BEGIN IMMEDIATE')
    owned=None
    if policy_id is not None:
        owned=db.execute('SELECT * FROM policies WHERE id=? AND user_id=?',(policy_id,user_id)).fetchone()
        if not owned:
            db.rollback();return jsonify(error='Policy not found.'),404
        if data.get('revision') is not None and data['revision']!=owned['revision']:
            db.rollback();return jsonify(error='This course changed in another window. Close the editor and reload the course before saving.'),409
    previous=json.loads(owned['policy_json']) if owned else None
    if owned and previous==policy and owned['name']==name.strip():
        db.rollback();return jsonify(id=policy_id,name=name.strip(),saved=True,revision=owned['revision'],unchanged=True)
    revision=owned['revision']+1 if owned else 1
    # Store the course and its explanation in one transaction; neither can exist alone.
    entry=event(previous,policy)
    if owned and owned['name']!=name.strip():entry['changes'].append(f"Course label changed from {owned['name']} to {name.strip()}.")
    try:
        if policy_id is None:
            cursor=db.execute('INSERT INTO policies(user_id,name,policy_json,updated_at,revision) VALUES(?,?,?,?,?)',(user_id,name.strip(),json.dumps(policy),int(time.time()),revision))
            policy_id=cursor.lastrowid
        else:
            db.execute('UPDATE policies SET name=?,policy_json=?,updated_at=?,revision=? WHERE id=? AND user_id=?',(name.strip(),json.dumps(policy),int(time.time()),revision,policy_id,user_id))
        db.execute('INSERT INTO grade_history(policy_id,recorded_at,revision,event_json) VALUES(?,?,?,?)',(policy_id,datetime.now(timezone.utc).isoformat(),revision,json.dumps(entry)))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback();return jsonify(error='You already have a course with this name. Choose another name.'),409
    return jsonify(id=policy_id,name=name.strip(),saved=True,revision=revision)


@auth.route('/policies/<int:policy_id>',methods=['GET','DELETE'])
def saved_policy(policy_id):
    record=session_record()
    if not record or record['user_id'] is None:return jsonify(error='Sign in to access your policies.'),401
    db=database();row=db.execute('SELECT * FROM policies WHERE id=? AND user_id=?',(policy_id,record['user_id'])).fetchone()
    if not row:return jsonify(error='Policy not found.'),404
    if request.method=='DELETE':
        db.execute('DELETE FROM policies WHERE id=? AND user_id=?',(policy_id,record['user_id']));db.commit()
        return jsonify(deleted=True)
    from grade_engine import calculate
    from history import explain,attendance_preview
    policy=json.loads(row['policy_json']);result=calculate(policy)
    history=[{'id':r['id'],'recorded_at':r['recorded_at'],'revision':r['revision'],**json.loads(r['event_json'])} for r in db.execute('SELECT * FROM grade_history WHERE policy_id=? ORDER BY revision DESC',(policy_id,))]
    return jsonify(id=row['id'],name=row['name'],revision=row['revision'],policy=policy,result=result,explanations=explain(result),history=history,attendance=attendance_preview(policy))


@auth.get('/policies/<int:policy_id>/plan')
def improvement_plan(policy_id):
    record=session_record()
    if not record or record['user_id'] is None:return jsonify(error='Sign in to view your plan.'),401
    # Resolve ownership on the server; a course ID is never proof of access.
    row=database().execute('SELECT policy_json FROM policies WHERE id=? AND user_id=?',(policy_id,record['user_id'])).fetchone()
    if not row:return jsonify(error='Policy not found.'),404
    from datetime import date
    from planner import next_steps
    try: today=date.fromisoformat(request.args.get('today',date.today().isoformat()))
    except ValueError:return jsonify(error='Invalid local date.'),400
    return jsonify(next_steps(json.loads(row['policy_json']),today))
