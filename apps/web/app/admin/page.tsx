import { Shell } from "@/components/shell";
import { AdminOverview } from "@/components/admin-overview";

export default function AdminPage() {
  return <Shell active="Administración"><div className="section-title" style={{marginTop:0}}><div><span className="eyebrow" style={{color:"#925b12"}}>Acceso restringido</span><h1 style={{fontSize:30,color:"var(--ink)"}}>Centro de administración</h1></div><span>Los permisos se validan también en la API</span></div>
    <AdminOverview/>
  </Shell>;
}
