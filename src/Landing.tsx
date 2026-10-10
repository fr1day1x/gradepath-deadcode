import { useEffect, useRef, useState, lazy, Suspense, type FormEvent } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ArrowRight, ArrowUpRight, Check, Eye, EyeOff, LockKeyhole, Mail, Sparkles, Target, TrendingUp, Zap } from 'lucide-react';
const App = lazy(() => import('./App'));
// Signed-in students use persistent records; the guest dashboard keeps sample scenarios separate.
const AccountWorkspace = lazy(() => import('./AccountWorkspace'));
import Orbit from './Orbit';
import SpaceHero from './SpaceHero';
import { getSession, signUp, signIn, signOut, type User } from './auth';
import './landing.css';

export default function Landing() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState('');
  const [name,setName]=useState('');
  const [register,setRegister]=useState(false);
  const [checking,setChecking]=useState(true);
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const reduced = useReducedMotion();
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(()=>{let active=true;getSession().then(account=>{if(active)setUser(account)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setChecking(false)});return()=>{active=false}},[]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(''); setBusy(true);
    controller.current = new AbortController();
    const timeout = setTimeout(() => controller.current?.abort(), 15000);
    try { const account = await (register?signUp(name.trim(),email.trim(),password,controller.current.signal):signIn(email.trim(), password, controller.current.signal)); setPassword(''); setUser(account); }
    catch (e) { setError(e instanceof Error && e.name !== 'AbortError' ? e.message : 'Sign-in timed out. Please try again.'); }
    finally { clearTimeout(timeout); setBusy(false); }
  }
  async function logout() {
    setBusy(true); setError('');
    try { if(user?.id)await signOut(); setUser(null); setEmail(''); setPassword(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not sign out.'); }
    finally { setBusy(false); }
  }
  function focusLogin() { document.getElementById('login-email')?.focus(); }
  if(checking)return <div className="workspace-loading" role="status">CHECKING YOUR SESSION…</div>;
  return <AnimatePresence mode="sync">
    {user ? <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <div className="session-bar"><span><Check size={13}/>{!user.id ? 'Guest session · Sample data' : `Signed in as ${user.name}`}</span>{error && <span role="alert">{error}</span>}<button disabled={busy} onClick={logout}>{busy ? 'Signing out…' : !user.id ? 'Back to landing' : 'Sign out'} <ArrowUpRight size={13}/></button></div>
      <Suspense fallback={<div className="workspace-loading">PREPARING MISSION CONTROL…</div>}>{user.id?<AccountWorkspace key={user.id} displayName={user.name} onLogout={logout} loggingOut={busy}/>:<App displayName={user.name} onLogout={logout} loggingOut={busy} isGuest/>}</Suspense>
    </motion.div> : <motion.div className="landing" key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: reduced ? 0 : -15 }}>
      <div className="landing-glow glow-one"/><div className="landing-glow glow-two"/><div className="edition-label" aria-hidden="true"></div>
      <nav className="landing-nav" aria-label="Landing navigation"><a className="brand" href="#"><span className="brand-symbol"><TrendingUp size={23}/></span>gradepath<span className="brand-dot">.</span></a><div><a href="#possibilities">01 — The possibilities</a><button onClick={focusLogin}>Your workspace <ArrowUpRight size={15}/></button></div></nav>
      <SpaceHero/>
      <main className="landing-main">
        <motion.section className="landing-story" initial={{ opacity: 0, y: reduced ? 0 : 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7 }}>
          <div className="landing-eyebrow"><span/><span>FOR THE GRADE YOU HAVEN’T MET YET</span></div>
          <h1>Less guessing.<br/><span>More becoming.</span></h1>
          <p className="landing-description">You’re more than your last exam. Play with the possibilities. Find your way to what comes next.</p>
          <div className="landing-benefits"><span><Check size={14}/> See the bigger picture</span><span><Check size={14}/> Make your next move</span></div>
          <Orbit interactive/>
        </motion.section>
        <motion.section className="login-card" aria-labelledby="login-title" initial={{ opacity: 0, y: reduced ? 0 : 25 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7, delay: .15 }}>
          <span className="login-symbol"><TrendingUp size={26}/></span><div className="login-kicker">02 / YOUR NEXT CHAPTER</div><h2 id="login-title">Make your<br/>next move<span>↗</span></h2><p>Your semester. Your ambition. Your starting point.</p>
          <div className="account-tabs" role="group" aria-label="Account action"><button type="button" aria-pressed={!register} onClick={()=>{setRegister(false);setError('');setPassword('')}} disabled={busy}>Sign in</button><button type="button" aria-pressed={register} onClick={()=>{setRegister(true);setError('');setPassword('')}} disabled={busy}>Create account</button></div>
          <form onSubmit={submit}>
            {register&&<><label htmlFor="register-name">Your name</label><div className="login-input"><input id="register-name" name="name" autoComplete="name" placeholder="What should BMO call you?" required maxLength={80} value={name} onChange={e=>setName(e.target.value)} disabled={busy}/></div></>}
            <label htmlFor="login-email">Email address</label><div className="login-input"><Mail size={17}/><input id="login-email" name="email" type="email" autoComplete="username" placeholder="you@university.edu" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={busy}/></div>
            <label htmlFor="login-password">Password</label><div className="login-input"><LockKeyhole size={17}/><input id="login-password" name="password" type={visible ? 'text' : 'password'} autoComplete={register?"new-password":"current-password"} minLength={register?8:undefined} maxLength={128} placeholder="Enter your password" required value={password} onChange={e => setPassword(e.target.value)} disabled={busy}/><button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div>
            {error && <div className="login-error" role="alert">{error}</div>}
            <motion.button whileTap={{ scale: .98 }} className="login-submit" type="submit" disabled={busy}>{busy ? 'Opening your workspace…' : register ? 'Create my account' : 'Sign in to Gradepath'}{busy ? <span className="login-spinner"/> : <ArrowRight size={18}/>}</motion.button>
            <div className="login-privacy"><LockKeyhole size={12}/>{register?'Use at least 8 characters · Passwords are securely hashed':'Your account stays signed in on this device'}</div>
          </form>
          <div className="login-divider"><span/>OR TAKE A LOOK AROUND<span/></div><button className="explore-button" onClick={() => { setPassword(''); setError(''); setUser({ name: 'Demo student', email: 'student@example.com' }); }} disabled={busy}><Zap size={15}/> Explore with sample data <ArrowUpRight size={15}/></button><p className="login-footnote">Your courses and recorded grade history stay in your account.<br/>Guest mode is still available for trying things out.</p>
          <div className="login-card-bottom"><span/> A little more confidence starts here.</div>
        </motion.section>
      </main>
      <section className="landing-features" id="possibilities" aria-label="Gradepath features">{[{icon:TrendingUp,title:'Know where you stand.',copy:'Your grades, finally in perspective.'},{icon:Sparkles,title:'Make room for what-if.',copy:'Explore a possibility before it’s a reality.'},{icon:Target,title:'Find your way forward.',copy:'Turn a target grade into a clear next step.'}].map(({icon:Icon,title,copy},i)=><motion.div key={title} initial={{opacity:0,y:reduced?0:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*.1}}><span><Icon size={19}/></span><div><h3>{title}</h3><p>{copy}</p></div></motion.div>)}</section>
      <footer className="landing-footer"><span>© 2026 Gradepath</span><span>Made for your next chapter <Sparkles size={12}/></span><span>A clearer path forward.</span></footer>
    </motion.div>}
  </AnimatePresence>;
}
