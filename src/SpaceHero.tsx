import { motion, useReducedMotion } from 'motion/react';
import { ArrowDown, ArrowUpRight, MoveUpRight } from 'lucide-react';
import { lazy, Suspense } from 'react';
const Astro=lazy(()=>import('./Astro'));
export default function SpaceHero(){
 const reduced=useReducedMotion();
 const enter=()=>{document.getElementById('login-email')?.focus({preventScroll:true});document.getElementById('login-title')?.scrollIntoView({behavior:reduced?'instant':'smooth',block:'center'});};
 return <section className="space-hero" aria-labelledby="space-title">
   <div className="space-grain"/>
   <div className="space-topline"><span>MISSION 001 — YOUR NEXT CHAPTER</span><span><i/> ALL SYSTEMS POSSIBLE</span></div>
   <motion.div className="space-title" initial={{opacity:0,y:reduced?0:35,filter:reduced?'none':'blur(12px)'}} animate={{opacity:1,y:0,filter:'blur(0px)'}} transition={{duration:1.1,ease:[.16,1,.3,1]}}><span>YOUR POTENTIAL. UNLIMITED.</span><h1 id="space-title">BEYOND<span>THE GRADE.</span></h1><p>Your last score isn’t your final frontier.</p></motion.div>
   <Suspense fallback={<div className="scene-loading">WAKING UP BMO <span/></div>}><Astro/></Suspense>
   <div className="space-side left"><span>01 / MEET BMO</span><p>Move your cursor.<br/>You’ve got company.</p><MoveUpRight size={22}/></div>
   <div className="space-side right"><span>SET YOUR COORDINATES</span><p>A little curiosity.<br/>A whole new trajectory.</p><button onClick={enter}>Start your mission <ArrowUpRight size={18}/></button></div>
   <div className="space-bottom"><span>INTERACTIVE 3D EXPERIENCE <i>✦</i> MADE FOR YOUR NEXT MOVE</span><button onClick={enter}>SCROLL TO TAKE OFF <ArrowDown size={15}/></button><span>FALL ’26 / EARTH</span></div>
 </section>;
}
