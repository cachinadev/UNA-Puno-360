"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MapLibreMap, Marker } from "maplibre-gl";
import { Bus, Clock3, Gauge, LocateFixed, Maximize2, Pause, Play, RefreshCw, Route, Users } from "lucide-react";
import { ReliableMap } from "@/components/reliable-map";

type Stop = { id: string; name: string; stop_order: number; lat: number; lon: number; official_verified: boolean };
type UpcomingStop = { id: string; name: string; distance_m: number; eta_seconds: number };
type Vehicle = { id: string; public_label: string; route_id: string; position: {lon:number;lat:number}; heading:number; speed_kph:number; status:"moving"|"stopped"|"delayed"|"offline"; occupancy:"low"|"medium"|"high"; age_seconds:number; next_stop:UpcomingStop|null; upcoming_stops:UpcomingStop[] };
type DemoRoute = { id:string; name:string; description:string; official_verified:boolean; geometry:{type:"LineString";coordinates:number[][]}; stops:Stop[]; vehicles:Vehicle[] };
type Snapshot = { mode:"demonstration"; generated_at:string; data:DemoRoute[]; disclaimer:string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const statusLabel = { moving:"En movimiento", stopped:"En paradero", delayed:"Con demora simulada", offline:"Sin conexión simulada" };
const occupancyLabel = { low:"Baja", medium:"Media", high:"Alta" };

export function TransportExperience() {
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Map<string, Marker>>(new Map());
  const snapshotRef = useRef<Snapshot|null>(null);
  const [snapshot,setSnapshot] = useState<Snapshot|null>(null);
  const [routeId,setRouteId] = useState<string>("");
  const [vehicleId,setVehicleId] = useState<string>("");
  const [running,setRunning] = useState(true);
  const [speed,setSpeed] = useState(1);
  const [simulatedAt,setSimulatedAt] = useState(() => Date.now());
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [fullScreen,setFullScreen] = useState(false);
  const [mapReady,setMapReady] = useState(0);
  const [routesRendered,setRoutesRendered] = useState(0);
  const [followMode,setFollowMode] = useState(false);
  const lastTick = useRef(Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      const now = Date.now();
      if (running) setSimulatedAt(value => value + (now - lastTick.current) * speed);
      lastTick.current = now;
    }, 750);
    return () => window.clearInterval(timer);
  }, [running,speed]);

  const load = useCallback(async () => {
    try {
      const query = new URLSearchParams({at:new Date(simulatedAt).toISOString()});
      const response = await fetch(`${API_URL}/transport/demo/snapshot?${query}`,{cache:"no-store"});
      if (!response.ok) throw new Error("El simulador no respondió correctamente");
      const data = await response.json() as Snapshot;
      setSnapshot(data); setError("");
      if (!routeId && data.data[0]) setRouteId(data.data[0].id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo cargar el transporte demostrativo");
    } finally { setLoading(false); }
  },[routeId,simulatedAt]);

  useEffect(() => { void load(); },[load]);
  const selectedRoute = useMemo(() => snapshot?.data.find(route => route.id===routeId) ?? snapshot?.data[0],[snapshot,routeId]);
  const selectedVehicle = useMemo(() => selectedRoute?.vehicles.find(vehicle => vehicle.id===vehicleId) ?? selectedRoute?.vehicles[0],[selectedRoute,vehicleId]);
  useEffect(()=>{snapshotRef.current=snapshot},[snapshot]);

  const prepareMap=useCallback((map:MapLibreMap,maplibregl:typeof import("maplibre-gl"))=>{
    mapRef.current=map;
    map.addSource("routes",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
    map.addLayer({id:"route-line",type:"line",source:"routes",paint:{"line-color":["case",["boolean",["get","selected"],false],"#0f5f9a","#70879a"],"line-width":["case",["boolean",["get","selected"],false],7,4],"line-opacity":["case",["boolean",["get","selected"],false],.95,.55]}});
    map.addSource("stops",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
    map.addLayer({id:"stop-points",type:"circle",source:"stops",paint:{"circle-radius":7,"circle-color":"#f3bd4d","circle-stroke-color":"#10243b","circle-stroke-width":2}});
    map.on("click","stop-points",event=>{
      const id=String(event.features?.[0]?.properties?.id??"");const name=String(event.features?.[0]?.properties?.name??"Paradero demostrativo");
      const arrivals=(snapshotRef.current?.data.flatMap(route=>route.vehicles).map(vehicle=>({vehicle,stop:vehicle.upcoming_stops.find(stop=>stop.id===id)})).filter(item=>item.stop).sort((a,b)=>(a.stop?.eta_seconds??0)-(b.stop?.eta_seconds??0))??[]);
      const content=document.createElement("div");content.className="stop-popup";const title=document.createElement("strong");title.textContent=name;content.appendChild(title);
      const note=document.createElement("small");note.textContent="ETA de vehículos simulados";content.appendChild(note);
      arrivals.slice(0,4).forEach(item=>{const row=document.createElement("button");row.type="button";row.textContent=`${item.vehicle.public_label} · ${Math.max(1,Math.ceil((item.stop?.eta_seconds??0)/60))} min`;row.onclick=()=>{setRouteId(item.vehicle.route_id);setVehicleId(item.vehicle.id)};content.appendChild(row)});
      if(!arrivals.length){const empty=document.createElement("span");empty.textContent="Sin arribos calculados";content.appendChild(empty)}
      new maplibregl.Popup({offset:12}).setLngLat(event.lngLat).setDOMContent(content).addTo(map);
    });
    map.on("mouseenter","stop-points",()=>map.getCanvas().style.cursor="pointer");map.on("mouseleave","stop-points",()=>map.getCanvas().style.cursor="");
    setMapReady(value=>value+1);
  },[]);
  const disposeMap=useCallback(()=>{markersRef.current.forEach(marker=>marker.remove());markersRef.current.clear();mapRef.current=null},[]);

  useEffect(() => {
    const map=mapRef.current;
    if (!map || !snapshot || !selectedRoute || !map.isStyleLoaded()) return;
    (map.getSource("routes") as GeoJSONSource)?.setData({type:"FeatureCollection",features:snapshot.data.map(route=>({type:"Feature",properties:{id:route.id,name:route.name,selected:route.id===selectedRoute.id},geometry:route.geometry}))});
    (map.getSource("stops") as GeoJSONSource)?.setData({type:"FeatureCollection",features:snapshot.data.flatMap(route=>route.stops.map(stop=>({type:"Feature" as const,properties:{id:stop.id,name:stop.name,route_id:route.id},geometry:{type:"Point" as const,coordinates:[stop.lon,stop.lat]}})))});
    setRoutesRendered(snapshot.data.length);
    void import("maplibre-gl").then(maplibregl => {
      const vehicles=snapshot.data.flatMap(route=>route.vehicles);
      const active=new Set(vehicles.map(vehicle=>vehicle.id));
      markersRef.current.forEach((marker,id)=>{if(!active.has(id)){marker.remove();markersRef.current.delete(id);}});
      vehicles.forEach(vehicle => {
        let marker=markersRef.current.get(vehicle.id);
        if(!marker){
          const element=document.createElement("button"); element.className="bus-marker"; element.type="button";
          const icon=document.createElement("span"); icon.textContent="🚌"; element.appendChild(icon);
          element.setAttribute("aria-label",`Ver ${vehicle.public_label}`); element.dataset.vehicleId=vehicle.id; element.onclick=()=>{setRouteId(vehicle.route_id);setVehicleId(vehicle.id)};
          marker=new maplibregl.Marker({element,anchor:"center"}).setLngLat([vehicle.position.lon,vehicle.position.lat]).addTo(map);
          marker.getElement().style.transition="transform 700ms linear";
          markersRef.current.set(vehicle.id,marker);
        }
        marker.setLngLat([vehicle.position.lon,vehicle.position.lat]);
        const icon=marker.getElement().firstElementChild as HTMLElement|null;
        if(icon) icon.style.transform=`rotate(${vehicle.heading}deg)`;
        marker.getElement().dataset.selected=String(vehicle.id===selectedVehicle?.id);
      });
    });
  },[snapshot,selectedRoute,selectedVehicle?.id,mapReady]);

  useEffect(()=>{if(followMode&&selectedVehicle)mapRef.current?.easeTo({center:[selectedVehicle.position.lon,selectedVehicle.position.lat],duration:650})},[followMode,selectedVehicle]);

  const selectRoute=(route:DemoRoute) => {
    setRouteId(route.id); setVehicleId(route.vehicles[0]?.id ?? "");
    const coordinates=route.geometry.coordinates;
    if(coordinates.length){
      void import("maplibre-gl").then(maplibregl=>{
        const bounds=coordinates.reduce((value,point)=>value.extend(point as [number,number]),new maplibregl.LngLatBounds(coordinates[0] as [number,number],coordinates[0] as [number,number]));
        mapRef.current?.fitBounds(bounds,{padding:55,duration:700});
      });
    }
  };
  const restart=()=>{setSimulatedAt(Date.now());setRunning(true);lastTick.current=Date.now();};
  const follow=()=>{if(!selectedVehicle)return;setFollowMode(value=>!value);mapRef.current?.easeTo({center:[selectedVehicle.position.lon,selectedVehicle.position.lat],zoom:16,duration:700})};

  return <section className={`transport-page ${fullScreen?"map-fullscreen":""}`}>
    <div className="page-heading"><div><span className="demo-ribbon">MODO DEMOSTRACIÓN — VEHÍCULOS Y RUTAS SIMULADOS</span><h1>Transporte universitario</h1><p>Vehículos sintéticos sincronizados por reloj y animados sobre recorridos ilustrativos. No son GPS ni rutas oficiales.</p></div><button className="button secondary" onClick={()=>setFullScreen(value=>!value)}><Maximize2 size={17}/>{fullScreen?"Cerrar mapa":"Mapa completo"}</button></div>
    <div className="simulation-toolbar" aria-label="Controles de simulación">
      <button className="icon-button" onClick={()=>setRunning(value=>!value)} aria-label={running?"Pausar simulación":"Reanudar simulación"}>{running?<Pause size={18}/>:<Play size={18}/>}</button>
      <button className="icon-button" onClick={restart} aria-label="Reiniciar simulación"><RefreshCw size={18}/></button>
      <span className="simulation-state">{running?"Simulación activa":"Simulación pausada"}</span>
      <div className="speed-group" aria-label="Velocidad">{[1,2,5].map(value=><button className={speed===value?"selected":""} onClick={()=>setSpeed(value)} key={value}>{value}×</button>)}</div>
      <time>{new Date(simulatedAt).toLocaleTimeString("es-PE")}</time>
    </div>
    {error&&<div className="error-state" role="alert"><strong>No se pudo conectar con la API.</strong><span>{error}. Verifica FastAPI en el puerto 8000.</span><button className="button primary" onClick={()=>void load()}>Reintentar</button></div>}
    <div className="transport-layout">
      <aside className="route-panel"><h2><Route size={19}/> Circuitos demostrativos</h2>{loading&&<div className="skeleton-list"/>}{snapshot?.data.map(route=><button className={`route-option ${selectedRoute?.id===route.id?"active":""}`} onClick={()=>selectRoute(route)} key={route.id}><strong>{route.name}</strong><span>{route.vehicles.length} vehículo(s) · {route.stops.length} paraderos</span><small>No verificado · datos sintéticos</small></button>)}</aside>
      <div className="map-panel" data-routes-rendered={routesRendered}><ReliableMap className="transport-map" ariaLabel="Mapa interactivo de transporte demostrativo" center={[-70.015,-15.829]} zoom={13.5} onReady={prepareMap} onDispose={disposeMap}/><button className={`follow-button ${followMode?"active":""}`} onClick={follow} disabled={!selectedVehicle}><LocateFixed size={16}/> {followMode?"Siguiendo bus":"Seguir bus"}</button></div>
      <aside className="vehicle-panel">{selectedVehicle?<><div className="vehicle-title"><div className="vehicle-avatar">🚌</div><div><span className="demo-ribbon">DEMO</span><h2>{selectedVehicle.public_label}</h2></div></div><span className={`vehicle-status ${selectedVehicle.status}`}>{statusLabel[selectedVehicle.status]}</span><div className="vehicle-metrics"><div><Gauge/><strong>{selectedVehicle.speed_kph} km/h</strong><span>Velocidad simulada</span></div><div><Users/><strong>{occupancyLabel[selectedVehicle.occupancy]}</strong><span>Ocupación</span></div><div><Clock3/><strong>{selectedVehicle.next_stop?`${Math.max(1,Math.ceil(selectedVehicle.next_stop.eta_seconds/60))} min`:"—"}</strong><span>Próximo paradero</span></div></div>{selectedVehicle.next_stop&&<div className="next-stop"><span>Siguiente parada</span><strong>{selectedVehicle.next_stop.name}</strong><small>{selectedVehicle.next_stop.distance_m} m de distancia estimada</small></div>}<h3>Próximas paradas</h3><ol className="stop-timeline">{selectedVehicle.upcoming_stops.map(stop=><li key={stop.id}><span/><div><strong>{stop.name}</strong><small>ETA simulada · {Math.max(1,Math.ceil(stop.eta_seconds/60))} min</small></div></li>)}</ol></>:<div className="empty-state"><Bus size={34}/><strong>Selecciona un circuito</strong><span>Los vehículos aparecerán cuando la semilla demostrativa esté cargada.</span></div>}</aside>
    </div>
    <p className="map-attribution-note">Mapa base © OpenStreetMap contributors. El uso en producción deberá configurar un proveedor de teselas con capacidad adecuada.</p>
  </section>;
}
