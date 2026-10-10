export type User = { id?: number; name: string; email: string };
const base=(import.meta.env.VITE_AUTH_BASE_URL || '/api').replace(/\/$/,'');
let csrfToken='';
// Share session bootstrap requests so simultaneous components receive the same CSRF token.
let pending:Promise<User|null>|null=null;

export async function getSession():Promise<User|null> {
 if(pending)return pending;
 pending=(async()=>{
  const response=await fetch(`${base}/auth/session`,{credentials:'include',cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw new Error('Account service is unavailable. Please try again, or explore as a guest.');
  const data=await response.json();
  if(typeof data.csrfToken!=='string')throw new Error('Invalid account service response.');
  csrfToken=data.csrfToken;
  if(data.user!==null&&(typeof data.user?.name!=='string'||typeof data.user?.email!=='string'||!Number.isInteger(data.user?.id)))throw new Error('Invalid account profile.');
  return data.user;
 })();
 try{return await pending}finally{pending=null}
}

async function accountRequest(path:string,body:object,signal?:AbortSignal):Promise<User|null>{
 if(!csrfToken)await getSession();
 const send=()=>fetch(`${base}/auth/${path}`,{method:'POST',credentials:'include',signal,headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},body:JSON.stringify(body)});
 let response=await send();
 if(response.status===403){await getSession();response=await send()}
 const data=await response.json().catch(()=>null);
 if(!response.ok)throw new Error(data?.error||'Account service is unavailable. Please try again.');
 if(typeof data?.csrfToken!=='string')throw new Error('Invalid account service response.');
 csrfToken=data.csrfToken;
 return data.user;
}
export async function signIn(email:string,password:string,signal:AbortSignal):Promise<User>{
 const user=await accountRequest('login',{email,password},signal);
 if(!user?.id)throw new Error('The service did not return an account.');
 return user;
}
export async function signUp(name:string,email:string,password:string,signal:AbortSignal):Promise<User>{
 const user=await accountRequest('register',{name,email,password},signal);
 if(!user?.id)throw new Error('The service did not return an account.');
 return user;
}
export async function signOut():Promise<void>{await accountRequest('logout',{})}

// Cookies identify the account; the CSRF token protects mutations. Never embed credentials in URLs.
export async function policyRequest(path:string='',method='GET',body?:unknown){
 if(!csrfToken)await getSession();
 const send=()=>fetch(`${base}/auth/policies${path}`,{method,credentials:'include',signal:AbortSignal.timeout(15000),headers:{'Content-Type':'application/json','X-CSRF-Token':csrfToken},...(body===undefined?{}:{body:JSON.stringify(body)})});
 let response=await send();if(response.status===403){await getSession();response=await send()}
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not access your policies.');return data;
}
