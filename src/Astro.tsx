import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { createBmo } from './BmoModel';
import { Heart, Orbit, Pause, Play, RotateCcw } from 'lucide-react';

/** Animated BMO calculator modeled from the user-provided reference. */
export default function Astro({grade=87.7, compact=false}:{grade?:number;compact?:boolean}) {
 const host=useRef<HTMLDivElement>(null);
 const [cheer,setCheer]=useState(false),[wave,setWave]=useState(0),[paused,setPaused]=useState(false),[failed,setFailed]=useState(false);
 const [reduced,setReduced]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches);
 useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const update=()=>setReduced(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 const state=useRef({cheer,grade,wave,paused,reduced});
 state.current={cheer,grade,wave,paused,reduced};
 useEffect(()=>{
  const element=host.current!;let renderer:THREE.WebGLRenderer;
  try {renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});} catch {setFailed(true);return;}
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));renderer.setClearColor(0,0);
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  element.appendChild(renderer.domElement);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(33,1,.1,100);camera.position.set(0,.8,8.5);camera.lookAt(0,.4,0);
  const root=new THREE.Group();scene.add(root);
  const mats:THREE.Material[]=[];
  const {head,eyes,eyeMeshes,smile,openMouth,tongue,arms,legs,textures}=createBmo(root,mats);
  scene.add(new THREE.HemisphereLight('#f3fff8','#567f72',2.3));
  const light=(color:string,intensity:number,x:number,y:number,z:number)=>{const l=new THREE.DirectionalLight(color,intensity);l.position.set(x,y,z);scene.add(l)};
  light('#ffffff',2.5,-3,4,5);light('#b5ded4',1.6,4,1,-2);light('#abd9e7',1.4,-4,0,-1);
  const starGeo=new THREE.BufferGeometry(),positions=[];
  for(let i=0;i<140;i++){positions.push(Math.sin(i*127.1)*10,Math.cos(i*39.7)*6,-3-(i%11));}
  starGeo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
  const starMat=new THREE.PointsMaterial({color:'#7384aa',size:.022,transparent:true,opacity:.38});mats.push(starMat);
  const stars=new THREE.Points(starGeo,starMat);scene.add(stars);
  let tx=0,ty=0,visible=true,elapsed=0,last=0,lastWave=0,waveStart=-100,dirty=true;
  const pointer=(e:PointerEvent)=>{const r=element.getBoundingClientRect();tx=THREE.MathUtils.clamp((e.clientX-r.left)/r.width*2-1,-1,1);ty=THREE.MathUtils.clamp((e.clientY-r.top)/r.height*2-1,-1,1);dirty=true;};
  const reset=()=>{tx=0;ty=0;dirty=true};
  window.addEventListener('pointermove',pointer,{passive:true});document.documentElement.addEventListener('pointerleave',reset);
  const resize=()=>{const w=element.clientWidth,h=element.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.position.z=w/h<.85?10:8.5;camera.updateProjectionMatrix();dirty=true;};
  const observer=new ResizeObserver(resize);observer.observe(element);resize();
  const intersection=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;dirty=true});intersection.observe(element);
  renderer.setAnimationLoop((time)=>{
   const dt=Math.min((time-last)/1000,.05);last=time;
   if(!visible||document.hidden)return;
   const s=state.current;const still=s.paused||s.reduced;
   if(!still)elapsed+=dt;
   if(lastWave!==s.wave){lastWave=s.wave;waveStart=elapsed;dirty=true;}
   if(still&&!dirty)return;
   const blend=still?1:1-Math.exp(-dt*6);
   head.rotation.y=THREE.MathUtils.lerp(head.rotation.y,still?-.16:-.16+tx*.3,blend);
   head.rotation.x=THREE.MathUtils.lerp(head.rotation.x,still?0:ty*.12,blend);
   root.rotation.y=THREE.MathUtils.lerp(root.rotation.y,still?0:tx*.08,blend);
   root.position.y=still?0:Math.sin(elapsed*1.4)*.055;
   eyes.position.x=still?0:tx*.055;eyes.position.y=.81+(still?0:-ty*.035);
   const blink=still?1:(elapsed%4.8>4.62?.1:1);eyeMeshes.forEach(e=>{e.scale.y=.08*blink;});
   const happy=s.cheer||s.grade>=90;
   smile.visible=!happy;openMouth.visible=happy;tongue.visible=happy;
   const waving=!still&&elapsed-waveStart<2.4;
   arms[1].rotation.z=waving?2.1+Math.sin((elapsed-waveStart)*13)*.22:-.12;
   arms[0].rotation.z=still?.05:.05+Math.sin(elapsed*1.7)*.06;
   legs.forEach((leg,i)=>{leg.rotation.z=still?0:Math.sin(elapsed*1.4+i*Math.PI)*.045});
   stars.rotation.z=still?0:elapsed*.006;
   renderer.render(scene,camera);dirty=false;
   // Reduced-motion mode still reflects explicit controls on the next frame.
  });
  const changed=setInterval(()=>{dirty=true},150);
  return()=>{clearInterval(changed);renderer.setAnimationLoop(null);observer.disconnect();intersection.disconnect();window.removeEventListener('pointermove',pointer);document.documentElement.removeEventListener('pointerleave',reset);scene.traverse(o=>{if(o instanceof THREE.Mesh||o instanceof THREE.Points)o.geometry.dispose()});mats.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());renderer.dispose();renderer.domElement.remove()};
 },[]);
 return <div className={`astro-stage ${compact?'astro-compact':''}`}>
  <div className="astro-horizon"/><div ref={host} className="astro-canvas" role="img" aria-label="BMO, an animated teal calculator whose face follows your pointer"/>
  {failed&&<div className="astro-fallback"><span>✦</span><strong>BMO</strong><p>3D preview unavailable on this device.<br/>Your grade tools are ready below.</p></div>}
  <div className="astro-caption"><span className="signal-dot"/> BMO / YOUR STUDY BUDDY <span>{grade>=90?'TARGET IN RANGE':'EXPLORING POSSIBILITIES'}</span></div>
  {!failed&&<div className="astro-controls"><button aria-label={cheer?'Relax expression':'Happy expression'} aria-pressed={cheer} onClick={()=>setCheer(v=>!v)}><Heart size={14}/><span>{cheer?'Relax expression':'Happy expression'}</span></button><button onClick={()=>setWave(v=>v+1)} disabled={paused||!!reduced} aria-label="Wave hello"><Orbit size={14}/><span>Say hello</span></button><button onClick={()=>setPaused(p=>!p)} aria-label={paused?'Resume animation':'Pause animation'} aria-pressed={paused}>{paused?<Play size={14}/>:<Pause size={14}/>}</button><button onClick={()=>{setCheer(false);setPaused(false);setWave(0)}} aria-label="Reset companion"><RotateCcw size={13}/></button></div>}
 </div>;
}
