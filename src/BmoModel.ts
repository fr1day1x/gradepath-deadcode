import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

/** A modeled interpretation of the supplied BMO calculator reference. */
export function createBmo(parent: THREE.Group, materials: THREE.Material[]) {
 const textures:THREE.Texture[]=[];
 const mat=(color:string)=>{const m=new THREE.MeshStandardMaterial({color,roughness:.68,metalness:.02});materials.push(m);return m};
 const teal=mat('#399f97'),edge=mat('#214e4c'),screen=mat('#c2edbe'),ink=mat('#102c29'),keys=mat('#28484b'),yellow=mat('#efc762'),orange=mat('#ef7637');
 const head=new THREE.Group();parent.add(head);
 const box=(w:number,h:number,d:number,r:number,m:THREE.Material,g:THREE.Object3D,x:number,y:number,z:number)=>{const mesh=new THREE.Mesh(new RoundedBoxGeometry(w,h,d,4,r),m);mesh.position.set(x,y,z);g.add(mesh);return mesh};
 const ball=(g:THREE.Object3D,x:number,y:number,z:number,sx:number,sy:number,sz:number,m=teal)=>{const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,24,16),m);mesh.position.set(x,y,z);mesh.scale.set(sx,sy,sz);g.add(mesh);return mesh};
 box(1.96,2.93,.76,.2,edge,head,0,0,0);
 box(1.9,2.87,.74,.19,teal,head,0,.01,.03);
 box(1.6,1.08,.08,.13,edge,head,0,.77,.416);
 box(1.49,.97,.06,.11,screen,head,0,.77,.464);
 const eyes=new THREE.Group();eyes.position.set(0,.81,.503);head.add(eyes);
 const eyeMeshes=[-1,1].map(side=>ball(eyes,side*.38,.03,0,.041,.08,.018,ink));
 const smile=new THREE.Mesh(new THREE.TorusGeometry(.15,.022,8,32,Math.PI),ink);smile.position.set(0,.71,.511);smile.rotation.z=Math.PI;head.add(smile);
 const openMouth=ball(head,0,.62,.511,.16,.115,.017,ink);openMouth.visible=false;
 const tongue=ball(head,0,.565,.53,.09,.035,.008,mat('#78cc93'));tongue.visible=false;
 const label=(text:string,w:number,h:number,g:THREE.Object3D,x:number,y:number,z:number,color='#f4eaca',size=85)=>{
  const c=document.createElement('canvas');c.width=256;c.height=128;const ctx=c.getContext('2d')!;ctx.clearRect(0,0,256,128);ctx.fillStyle=color;ctx.font=`500 ${size}px Arial`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text,128,67);
  const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;textures.push(texture);
  const m=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false});materials.push(m);
  const p=new THREE.Mesh(new THREE.PlaneGeometry(w,h),m);p.position.set(x,y,z);g.add(p);return p;
 };
 const rows=[['AC','+/−','%','÷'],['7','8','9','×'],['4','5','6','−'],['1','2','3','=']];
 rows.forEach((row,j)=>row.forEach((text,i)=>{
  const x=-.615+i*.41,y=.01-j*.32;
  const tall=text==='=';
  box(.355,tall?.595:.27,.09,.052,edge,head,x,tall?y-.16:y,.45);
  box(.322,tall?.56:.239,.09,.043,text==='AC'?yellow:tall?orange:keys,head,x,tall?y-.16:y,.477);
  label(text,.29,.19,head,x,tall?y-.16:y,.531,text==='AC'?'#273d37':'#efe6cb',text==='+/−'?62:85);
 }));
 box(.765,.27,.09,.05,edge,head,-.41,-1.27,.45);box(.728,.239,.09,.043,keys,head,-.41,-1.27,.478);label('0',.34,.19,head,-.41,-1.27,.532);
 box(.355,.27,.09,.05,edge,head,.205,-1.27,.45);box(.322,.239,.09,.043,keys,head,.205,-1.27,.478);label('·',.28,.19,head,.205,-1.27,.532);
 // Speaker holes and vertical lettering on the left flank.
 for(let i=0;i<7;i++)ball(head,-.971,.72-Math.floor(i/3)*.16,-.17+(i%3)*.15,.014,.032,.032,ink);
 const sideLabel=label('BMO',.65,.28,head,-.982,-.52,0,'#132f2c',70);sideLabel.rotation.y=-Math.PI/2;sideLabel.rotation.z=Math.PI/2;
 const tube=(points:THREE.Vector3[],radius:number,g:THREE.Group)=>{const geo=new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),24,radius,10,false);const mesh=new THREE.Mesh(geo,teal);g.add(mesh);return mesh};
 const arms=[-1,1].map(side=>{
  const arm=new THREE.Group();arm.position.set(side*.95,-.37,0);head.add(arm);
  tube([new THREE.Vector3(),new THREE.Vector3(side*.37,-.19,0),new THREE.Vector3(side*.48,-.58,.05),new THREE.Vector3(side*.44,-.85,.08)],.068,arm);
  ball(arm,side*.44,-.86,.08,.11,.13,.07);
  for(let i=0;i<3;i++)ball(arm,side*(.38+i*.06),-.965+(i===1?-.02:0),.08,.037,.075,.046);
  return arm;
 });
 const legs=[-1,1].map(side=>{const leg=new THREE.Group();leg.position.set(side*.51,-1.41,0);head.add(leg);tube([new THREE.Vector3(),new THREE.Vector3(side*.05,-.25,0),new THREE.Vector3(side*.12,-.51,.06)],.078,leg);box(.32,.15,.22,.065,teal,leg,side*.21,-.53,.07);return leg;});
 parent.scale.setScalar(.83);
 return {head,eyes,eyeMeshes,smile,openMouth,tongue,arms,legs,textures};
}
