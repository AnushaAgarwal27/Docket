import { useEffect, useState } from 'react';
import type { Activity, Patterns, Profile, Receipt, Snapshot, Timeline } from './model';
// Vite proxies /api to the private local service. No secrets are baked into bundles.
// For a remotely served frontend, use an HTTPS reverse proxy and enter its API token per session.
export const api = {
  profiles:{list:'profiles:list'}, dashboard:{snapshot:'dashboard:snapshot'},
  activity:{recent:'activity:recent'}, timeline:{forProfile:'timeline:forProfile'},
  patterns:{byEmployer:'patterns:byEmployer'}, files:{forFlag:'files:forFlag'},
  cases:{approve:'cases:approve',followUp:'cases:followUp',setPayrollScript:'cases:setPayrollScript'},
} as const;
type Result = {'profiles:list':Profile[];'dashboard:snapshot':Snapshot|null;'activity:recent':Activity[];'timeline:forProfile':Timeline|null;'patterns:byEmployer':Patterns;'files:forFlag':Receipt|null};
function headers() {
  const token=sessionStorage.getItem('docket.apiToken');
  return {'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})};
}
export async function rpc<T>(kind:string,name:string,args:object):Promise<T> {
  const response=await fetch('/api/'+kind,{method:'POST',headers:headers(),body:JSON.stringify({name,args})});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || 'Backend request failed');
  return data.value;
}
let revision=0;
export function useQuery<K extends keyof Result>(name:K,args:object|'skip'={}):Result[K]|undefined {
  const [value,setValue]=useState<Result[K]>();
  const [error,setError]=useState<Error>();
  const key=JSON.stringify(args);
  useEffect(()=>{
    let alive=true;let timer:ReturnType<typeof setTimeout>;
    setValue(undefined);setError(undefined);
    if(args==='skip') return;
    async function poll(){
      try { const v=await rpc<Result[K]>('query',name,JSON.parse(key));if(alive){setValue(v);setError(undefined);} }
      catch(e){if(alive)setError(e instanceof Error?e:new Error('Backend unavailable'));}
      if(alive)timer=setTimeout(poll,1500);
    }
    void poll();return()=>{alive=false;clearTimeout(timer);};
  },[name,key,revision]);
  // Fail explicitly rather than silently presenting stale data as live.
  if(error)throw error;
  return value;
}
export function useMutation(name:string){
  return async(args:object)=>{await rpc('mutation',name,args);revision++;};
}
export function BackendAccess({children}:{children:React.ReactNode}){
  const [token,setToken]=useState(()=>sessionStorage.getItem('docket.apiToken')||'');
  const [ready,setReady]=useState(Boolean(token));
  if(ready)return <>{children}</>;
  return <main style={{padding:32}}><h1>Connect to Docket</h1><p>Enter the backend access token from your local .env. It stays in this browser session.</p><form onSubmit={e=>{e.preventDefault();sessionStorage.setItem('docket.apiToken',token);setReady(true);}}><label>Backend access token <input type="password" value={token} onChange={e=>setToken(e.target.value)} required autoComplete="off" /></label> <button type="submit">Connect</button></form></main>;
}
export function FileLink({url,children}:{url:string;children:React.ReactNode}){
  const [error,setError]=useState('');
  return <><button className="rc-file" onClick={async()=>{
    try{const r=await fetch(url,{headers:headers()});if(!r.ok)throw new Error('Document unavailable');
      const u=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=u;a.target='_blank';a.rel='noopener';a.click();setTimeout(()=>URL.revokeObjectURL(u),60000);
    }catch{setError('Could not open document');}
  }}>{children}</button>{error&&<span role="alert">{error}</span>}</>;
}
