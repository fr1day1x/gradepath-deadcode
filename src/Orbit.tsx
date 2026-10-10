import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from 'motion/react';

import { useState } from 'react';

import { ArrowUpRight } from 'lucide-react';

import { calculate, courses, letter } from './model';



export default function Orbit({ value, interactive=false }: { value?:number; interactive?:boolean }) {

 const [score,setScore]=useState(85);

 const grade=value??calculate({course:courses[0],finalScore:score,target:90,replaceLowest:true,dropLowest:true}).projected;

 const reduced=useReducedMotion();

 const px=useMotionValue(0),py=useMotionValue(0);

 const rx=useSpring(useTransform(py,[-1,1],[9,-9]),{stiffness:90,damping:22});

 const ry=useSpring(useTransform(px,[-1,1],[-12,12]),{stiffness:90,damping:22});

 return <div className={`orbit-experience ${interactive?'orbit-interactive':''}`} onPointerMove={e=>{if(reduced||e.pointerType==='touch')return;const b=e.currentTarget.getBoundingClientRect();px.set((e.clientX-b.left)/b.width*2-1);py.set((e.clientY-b.top)/b.height*2-1)}} onPointerLeave={()=>{px.set(0);py.set(0)}}>

   <div className="orbit-coordinates" aria-hidden="true"><span>GP—01 / POSSIBILITIES</span><span>YOUR FUTURE IS IN MOTION ↗</span></div>

   <motion.div className="orbit-sculpture" style={{rotateX:rx,rotateY:ry}}>

    <div className="orbit-grid"/>

    <motion.div className="orbital-band band-one" animate={{rotate:-31+(grade-85)*.35}} transition={{type:"spring",stiffness:70,damping:20}}/><motion.div className="orbital-band band-two" animate={{rotate:53+(grade-85)*.2}} transition={{type:"spring",stiffness:70,damping:20}}/><motion.div className="orbital-band band-three" animate={{rotate:-31+(grade-85)*.35}} transition={{type:"spring",stiffness:70,damping:20}}/>

    <motion.div className="orbit-core" animate={{scale:grade>=90?1.08:1}} transition={{type:'spring',stiffness:130,damping:18}}><span className="orbit-core-caption">POSSIBLE YOU</span><motion.strong key={letter(grade)} initial={{opacity:0,filter:'blur(12px)',y:15}} animate={{opacity:1,filter:'blur(0px)',y:0}}>{letter(grade)}<i>↗</i></motion.strong><span className="orbit-core-number">{grade.toFixed(1)}<small>%</small></span></motion.div>

    <span className="orbit-satellite satellite-one"/><span className="orbit-satellite satellite-two"/>

    <motion.div className="orbit-float float-one" animate={reduced?{}:{y:[0,-9,0]}} transition={{duration:5,repeat:Infinity}}><span className="orbit-live"/> {grade>=90?'TARGET REACHED':'STILL WRITING YOUR STORY'}</motion.div>

    <motion.div className="orbit-float float-two" animate={reduced?{}:{y:[0,9,0]}} transition={{duration:6,repeat:Infinity}}><ArrowUpRight size={18}/><div>{grade.toFixed(1)}% · Potential, unlocked.<small>One possibility at a time.</small></div></motion.div>

   </motion.div>

   {interactive&&<div className="orbit-demo-control"><div><label htmlFor="orbit-score">TRY A DIFFERENT FUTURE</label><span>Final exam <strong>{score}%</strong></span></div><input id="orbit-score" aria-label="Preview final exam score" type="range" min="0" max="100" value={score} onChange={e=>setScore(+e.target.value)} style={{'--progress':`${score}%`} as React.CSSProperties}/><p>Drag to explore · Real calculations, sample course</p></div>}

 </div>;

}
