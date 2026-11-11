"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Building2, Bus, Database, FileWarning, Library, LogIn, ShieldCheck, UsersRound, Utensils } from "lucide-react";

const API=process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000";
type Account={id:string;display_name:string;email:string;role:string};
type Overview={total_accounts:number;active_users:number;pending_reports:number;published_groups:number;registered_events:number;campus_facilities:number;transport_routes:number};
type Report={id:number;target_type:string;target_id:number;reason:string;status:string;created_at:string};
type Reservation={id:string;reservation_number:string;status:string;title:string;display_name:string;email:string};
type Meal={id:string;confirmation_code:string;status:string;description:string;display_name:string;email:string};

const privileged=new Set(["moderator","librarian","transport_operator","admin","superadmin"]);

export function AdminOverview(){
  const [account,setAccount]=useState<Account|null>(null);
  const [checked,setChecked]=useState(false);
  const [data,setData]=useState<Overview|null>(null);
  const [reports,setReports]=useState<Report[]>([]);
  const [reservations,setReservations]=useState<Reservation[]>([]);
  const [meals,setMeals]=useState<Meal[]>([]);
  const [message,setMessage]=useState("");
  const token=()=>sessionStorage.getItem("una_access_token");
  const request=useCallback(async(path:string,init?:RequestInit)=>fetch(`${API}${path}`,{...init,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token()}`,...init?.headers},cache:"no-store"}),[]);
  const load=useCallback(async()=>{
    const value=token();
    if(!value){setChecked(true);return;}
    const me=await request("/auth/me");
    if(!me.ok){setChecked(true);return;}
    const current=await me.json() as Account;setAccount(current);setChecked(true);
    if(!privileged.has(current.role))return;
    const tasks:Promise<void>[]=[];
    if(["admin","superadmin"].includes(current.role))tasks.push(request("/admin/overview").then(async r=>{if(r.ok)setData(await r.json())}));
    if(["moderator","admin","superadmin"].includes(current.role))tasks.push(request("/admin/reports").then(async r=>{if(r.ok)setReports((await r.json()).data)}));
    if(["librarian","admin","superadmin"].includes(current.role))tasks.push(request("/admin/library/reservations").then(async r=>{if(r.ok)setReservations((await r.json()).data)}));
    if(["admin","superadmin"].includes(current.role))tasks.push(request("/admin/dining/reservations").then(async r=>{if(r.ok)setMeals((await r.json()).data)}));
    await Promise.all(tasks);
  },[request]);
  useEffect(()=>{void load()},[load]);
  const resolve=async(id:number,action:"hide"|"dismiss")=>{if(!confirm(action==="hide"?"¿Ocultar el contenido reportado?":"¿Descartar este reporte?"))return;const response=await request(`/admin/reports/${id}/resolve`,{method:"POST",body:JSON.stringify({action,note:"Revisión realizada desde el panel administrativo"})});setMessage(response.ok?"Reporte procesado y auditado.":"No se pudo procesar el reporte.");if(response.ok)await load()};
  const advanceReservation=async(item:Reservation)=>{const next={requested:"confirmed",confirmed:"ready",ready:"collected"}[item.status];if(!next)return;const response=await request(`/admin/library/reservations/${item.id}`,{method:"PATCH",body:JSON.stringify({status:next})});setMessage(response.ok?`Reserva actualizada a ${next}.`:"La transición no está permitida.");if(response.ok)await load()};
  const advanceMeal=async(item:Meal)=>{if(item.status!=="confirmed")return;const response=await request(`/admin/dining/reservations/${item.id}`,{method:"PATCH",body:JSON.stringify({status:"checked_in"})});setMessage(response.ok?"Ingreso demostrativo registrado.":"No se pudo actualizar la reserva.");if(response.ok)await load()};

  if(!checked)return <div className="skeleton-list"/>;
  if(!account)return <div className="login-gate"><LogIn/><h2>Acceso administrativo</h2><p>Inicia sesión con una cuenta autorizada. La API vuelve a validar el rol en cada operación.</p><Link className="button primary" href="/login">Ingresar</Link></div>;
  if(!privileged.has(account.role))return <div className="login-gate denied"><AlertTriangle/><h2>Acceso denegado</h2><p>La cuenta {account.email} tiene rol de estudiante y no puede acceder a operaciones administrativas.</p><Link className="button secondary" href="/">Volver al espacio estudiantil</Link></div>;
  const metrics=[["Cuentas",data?.total_accounts??"—",UsersRound],["Usuarios activos",data?.active_users??"—",UsersRound],["Reportes pendientes",reports.length,FileWarning],["Instalaciones",data?.campus_facilities??"—",Building2],["Rutas",data?.transport_routes??"—",Bus],["API protegida","En línea",Database]] as const;
  return <>
    <div className="admin-role-banner"><ShieldCheck/><div><strong>Espacio de {account.role}</strong><span>{account.display_name} · permisos verificados por FastAPI</span></div><Link href="/">Vista estudiantil</Link></div>
    {message&&<div className="feedback" role="status">{message}</div>}
    {data&&<section className="admin-grid">{metrics.map(([label,value,Icon])=><div className="card metric" key={label}><div className="iconbox"><Icon size={20}/></div><small>{label}</small><strong>{value}</strong><span className="tag">Datos actuales</span></div>)}</section>}
    {["transport_operator","admin","superadmin"].includes(account.role)&&<section className="admin-section card"><div><Bus/><h2>Simulación de transporte</h2></div><p>Los controles deterministas de pausa, reinicio y velocidad están disponibles en el mapa de demostración.</p><Link className="button secondary" href="/transporte">Abrir controles</Link></section>}
    {["moderator","admin","superadmin"].includes(account.role)&&<section className="admin-section"><div className="section-title"><h2>Moderación</h2><span>{reports.length} pendientes</span></div>{reports.length===0?<div className="empty-state card"><ShieldCheck/><strong>No hay reportes pendientes.</strong></div>:<div className="card table-wrap"><table className="table"><thead><tr><th>Tipo</th><th>Motivo</th><th>Acciones</th></tr></thead><tbody>{reports.map(item=><tr key={item.id}><td>{item.target_type} #{item.target_id}</td><td>{item.reason}</td><td><button onClick={()=>void resolve(item.id,"hide")}>Ocultar</button><button onClick={()=>void resolve(item.id,"dismiss")}>Descartar</button></td></tr>)}</tbody></table></div>}</section>}
    {["librarian","admin","superadmin"].includes(account.role)&&<section className="admin-section"><div className="section-title"><h2><Library/> Reservas de biblioteca</h2><span>{reservations.length} registros</span></div><div className="card table-wrap"><table className="table"><thead><tr><th>Estudiante</th><th>Libro</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{reservations.map(item=><tr key={item.id}><td>{item.display_name}<small>{item.email}</small></td><td>{item.title}</td><td>{item.status}</td><td><button disabled={!(["requested","confirmed","ready"].includes(item.status))} onClick={()=>void advanceReservation(item)}>Avanzar estado</button></td></tr>)}</tbody></table>{reservations.length===0&&<div className="empty-state"><Library/><strong>No hay reservas.</strong></div>}</div></section>}
    {["admin","superadmin"].includes(account.role)&&<section className="admin-section"><div className="section-title"><h2><Utensils/> Reservas de comedor</h2><span>{meals.length} registros</span></div><div className="card table-wrap"><table className="table"><thead><tr><th>Estudiante</th><th>Menú</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{meals.map(item=><tr key={item.id}><td>{item.display_name}<small>{item.email}</small></td><td>{item.description}</td><td>{item.status}</td><td><button disabled={item.status!=="confirmed"} onClick={()=>void advanceMeal(item)}>Registrar ingreso</button></td></tr>)}</tbody></table>{meals.length===0&&<div className="empty-state"><Utensils/><strong>No hay reservas.</strong></div>}</div></section>}
  </>;
}
