import Link from "next/link";
import { BookOpen, Bus, CalendarDays, ChevronRight, Clock3, MapPinned, MessageCircle, Navigation, Search, Utensils } from "lucide-react";
import { Shell } from "@/components/shell";

const services = [
  ["Rutas universitarias", "Consulta recorridos y estados de vehículos", Bus, "/transporte"],
  ["Mapa del campus", "Encuentra facultades y servicios por fuente", MapPinned, "/mapa-campus"],
  ["Biblioteca", "Busca y reserva copias demostrativas", BookOpen, "/biblioteca"],
  ["Comedor universitario", "Menús y reservas demostrativas", Utensils, "/comedor"],
  ["Comunidad", "Grupos, publicaciones y actividades", MessageCircle, "comunidad"],
  ["Eventos", "Agenda académica, cultural y deportiva", CalendarDays, "/eventos"],
  ["Servicios cercanos", "Impresiones, salud, agua y más", Navigation, "mapa"],
  ["Investigación", "Acceso al repositorio académico", Search, "biblioteca"],
] as const;

export default function Dashboard() {
  return <Shell>
    <section className="hero"><span className="eyebrow">Panel estudiantil</span><h1>Buenas tardes,<br/>estudiante 👋</h1><p>Todo lo que necesitas para tu vida universitaria en Puno, reunido en un espacio claro y accesible.</p><div className="actions"><a className="button primary" href="#mapa"><MapPinned size={17}/>Explorar el campus</a><a className="button ghost" href="#transporte"><Bus size={17}/>Ver transporte</a></div></section>
    <div className="section-title"><h2>Servicios para ti</h2><span>Accesos principales</span></div>
    <section className="grid">{services.map(([title,description,Icon,id])=><a href={id.startsWith("/")?id:`#${id}`} className="card" style={{textDecoration:"none",color:"inherit"}} key={title}><div className="iconbox"><Icon size={21}/></div><h3>{title}</h3><p>{description}</p></a>)}</section>
    <div className="section-title"><h2>Hoy en la universidad</h2><span>Información de demostración</span></div>
    <section className="columns">
      <div className="card" id="transporte"><h3 style={{marginTop:0}}>Transporte universitario</h3><p>El estado siempre distingue datos en vivo, desactualizados, sin conexión y demostrativos.</p><div className="list" style={{marginTop:14}}><div className="item"><div className="iconbox"><Bus size={19}/></div><div><strong>Ruta Campus Principal</strong><small>Próxima referencia · 12 min</small></div><span className="status demo">Demostración</span></div><div className="item"><div className="iconbox"><Clock3 size={19}/></div><div><strong>Sin telemetría autorizada</strong><small>KUNTUR requiere credenciales del operador</small></div><span className="status">Transparente</span></div></div></div>
      <div className="card" id="eventos"><h3 style={{marginTop:0}}>Próximos eventos</h3><div className="notice"><strong>Feria de investigación</strong><p>Evento de demostración · Auditorio</p></div><div className="notice"><strong>Encuentro cultural</strong><p>Evento de demostración · Patio central</p></div><Link href="#comunidad" style={{fontSize:13,color:"#123d6a",fontWeight:700,textDecoration:"none"}}>Ver agenda <ChevronRight size={14} style={{verticalAlign:"middle"}}/></Link></div>
    </section>
    <div className="section-title"><h2>Novedades</h2><span>Anuncios publicados</span></div>
    <section className="columns"><div className="card" id="comunidad"><span className="eyebrow" style={{color:"#925b12"}}>Comunidad</span><h3>Un espacio universitario con moderación</h3><p>Participa en grupos por facultad, comparte publicaciones, inscríbete en eventos y reporta contenido de forma segura.</p></div><div className="card" id="biblioteca"><span className="eyebrow" style={{color:"#925b12"}}>Biblioteca y comedor</span><h3>Información sin falsas promesas</h3><p>Los catálogos externos, menús y horarios se identifican por fuente y fecha. La disponibilidad solo se muestra si ha sido verificada.</p></div></section>
    <div id="mapa"/><div id="comedor"/>
  </Shell>;
}
