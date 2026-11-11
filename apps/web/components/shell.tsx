"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Bell, BookOpen, Bus, CalendarDays, Home, Library, Map, MessageCircle, Search, Settings, ShieldCheck, UserRound, Utensils } from "lucide-react";

const links = [
  ["Inicio", Home, "/"], ["Transporte", Bus, "/transporte"], ["Mapa campus", Map, "/mapa-campus"],
  ["Biblioteca", Library, "/biblioteca"], ["Comedor", Utensils, "/comedor"], ["Comunidad", MessageCircle, "/comunidad"],
  ["Eventos", CalendarDays, "/eventos"],
] as const;

export function Shell({ children, active = "Inicio" }: { children: React.ReactNode; active?: string }) {
  const router=useRouter();
  const [notifications,setNotifications]=useState<{id:number;title:string;body:string;target_url:string|null;read_at:string|null}[]>([]);
  const [open,setOpen]=useState(false);
  const [loggedIn,setLoggedIn]=useState(false);
  const [account,setAccount]=useState<{display_name:string;role:string}|null>(null);
  useEffect(()=>{const token=sessionStorage.getItem("una_access_token");setLoggedIn(Boolean(token));if(!token)return;const headers={Authorization:`Bearer ${token}`};void Promise.all([fetch(`${process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000"}/notifications`,{headers}),fetch(`${process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000"}/auth/me`,{headers})]).then(async([notices,me])=>{if(notices.ok)setNotifications((await notices.json()).data);if(me.ok)setAccount(await me.json());else if(me.status===401){sessionStorage.removeItem("una_access_token");localStorage.removeItem("una_refresh_token");setLoggedIn(false)}}).catch(()=>undefined)},[]);
  const search=(event:React.FormEvent<HTMLFormElement>)=>{event.preventDefault();const value=String(new FormData(event.currentTarget).get("q")??"").toLowerCase();if(/libro|biblioteca|autor/.test(value))router.push("/biblioteca");else if(/bus|ruta|transporte/.test(value))router.push("/transporte");else if(/comida|menú|comedor/.test(value))router.push("/comedor");else if(/evento|actividad/.test(value))router.push("/eventos");else router.push("/mapa-campus")};
  const markAll=async()=>{const token=sessionStorage.getItem("una_access_token");if(!token)return;const response=await fetch(`${process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000"}/notifications/read-all`,{method:"POST",headers:{Authorization:`Bearer ${token}`}});if(response.ok)setNotifications(value=>value.map(item=>({...item,read_at:new Date().toISOString()})))};
  const unread=notifications.filter(item=>!item.read_at).length;
  const privileged=account&&["moderator","librarian","transport_operator","admin","superadmin"].includes(account.role);
  const signOut=async()=>{const token=sessionStorage.getItem("una_access_token");if(token)await fetch(`${process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000"}/auth/logout`,{method:"POST",headers:{Authorization:`Bearer ${token}`}}).catch(()=>undefined);sessionStorage.removeItem("una_access_token");localStorage.removeItem("una_refresh_token");router.push("/login");router.refresh()};
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="seal">UNA</div><div><strong>Puno 360</strong><small>Tu universidad en tus manos</small></div></div>
      <nav>{links.map(([label, Icon, href]) => <Link className={`navlink ${active === label ? "active" : ""}`} href={href} key={label}><Icon size={18}/>{label}</Link>)}{privileged&&<Link className={`navlink ${active==="Administración"?"active":""}`} href="/admin"><ShieldCheck size={18}/>Administración</Link>}</nav>
    </aside>
    <main className="main">
      <header className="topbar"><form className="search" onSubmit={search}><Search size={17} style={{display:"inline",marginRight:9,verticalAlign:"middle"}}/><input name="q" aria-label="Buscar" placeholder="Buscar servicios, libros o lugares..." style={{border:0,outline:0,width:"85%"}}/></form><div className="profile"><div className="notification-wrap"><button className="notification-button" onClick={()=>setOpen(value=>!value)} aria-label={`Notificaciones: ${unread} sin leer`}><Bell size={19}/>{unread>0&&<span>{unread}</span>}</button>{open&&<div className="notification-panel"><div><strong>Notificaciones</strong>{unread>0&&<button onClick={()=>void markAll()}>Marcar todas</button>}</div>{!loggedIn?<p>Inicia sesión para ver tus notificaciones.</p>:notifications.length===0?<p>No tienes notificaciones.</p>:notifications.slice(0,8).map(item=><Link className={!item.read_at?"unread":""} href={item.target_url??"/"} key={item.id}><strong>{item.title}</strong><span>{item.body}</span></Link>)}</div>}</div><Link href={loggedIn?"/perfil":"/login"} className="profile-link"><div className="avatar">{account?.display_name?.split(" ").map(part=>part[0]).join("").slice(0,2).toUpperCase()||"EP"}</div><span><strong style={{display:"block",fontSize:13}}>{account?.display_name??(loggedIn?"Cargando…":"Ingresar")}</strong><small style={{color:"var(--muted)"}}>{account?.role??"Invitado"}</small></span></Link>{loggedIn&&<button className="signout-button" onClick={()=>void signOut()}>Salir</button>}</div></header>
      {children}
      <footer className="footer"><span>UNA Puno 360 · MVP independiente, no es un servicio oficial de la UNA.</span><span>Datos demostrativos identificados · OSM © colaboradores</span></footer>
    </main>
    <nav className="mobile-nav">{links.slice(0,5).map(([label,Icon,href])=><Link href={href} key={label}><Icon size={19}/>{label}</Link>)}</nav>
  </div>;
}
