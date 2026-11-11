"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { UnaApiClient } from "@una/api-client";

export function LoginForm(){
  const router=useRouter();
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  async function submit(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault();setBusy(true);setError("");
    const form=new FormData(event.currentTarget);
    try{
      const api=new UnaApiClient(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");
      const session=await api.login(String(form.get("email")),String(form.get("password")));
      sessionStorage.setItem("una_access_token",session.access_token);
      localStorage.setItem("una_refresh_token",session.refresh_token);
      router.push("/");router.refresh();
    }catch(reason){setError(reason instanceof Error?reason.message:"No se pudo iniciar sesión");}
    finally{setBusy(false);}
  }
  return <form onSubmit={submit} className="card" style={{width:"min(430px,100%)",padding:32}}><div className="brand" style={{color:"var(--ink)"}}><div className="seal">UNA</div><div><strong>Puno 360</strong><small style={{color:"var(--muted)"}}>Acceso al ecosistema universitario</small></div></div><label style={{display:"block",fontSize:13,fontWeight:700,marginTop:16}}>Correo electrónico<input name="email" className="search" type="email" autoComplete="email" required style={{display:"block",marginTop:7}}/></label><label style={{display:"block",fontSize:13,fontWeight:700,marginTop:16}}>Contraseña<input name="password" className="search" type="password" autoComplete="current-password" required minLength={12} style={{display:"block",marginTop:7}}/></label>{error&&<p role="alert" style={{color:"#a53030",fontSize:13}}>{error}</p>}<button className="button primary" disabled={busy} type="submit" style={{width:"100%",justifyContent:"center",marginTop:22}}>{busy?"Ingresando…":"Ingresar"}</button><p style={{fontSize:12,color:"var(--muted)",lineHeight:1.5}}>El acceso local es solo para desarrollo. La integración SSO institucional aún requiere autorización.</p><Link href="/registro" style={{fontSize:13,color:"#123d6a",display:"block",marginBottom:8}}>Crear cuenta de desarrollo</Link><a href="/" style={{fontSize:13,color:"#123d6a"}}>Volver al inicio</a></form>;
}
