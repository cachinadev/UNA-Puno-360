"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import { Building2, Crosshair, List, MapIcon, Navigation, RefreshCw, Search, ShieldCheck, TriangleAlert } from "lucide-react";
import { ReliableMap } from "@/components/reliable-map";

type Place = { id:number; source:string; source_id:string; name:string; category:string; reviewed:boolean; latitude:number; longitude:number; tags?:Record<string,string> };
type Position = {lat:number;lon:number};
const API_URL=process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const categories:Record<string,string>={university:"Universidad",library:"Bibliotecas",restaurant:"Comida",cafe:"Cafeterías",clinic:"Salud",pharmacy:"Farmacias",atm:"Cajeros",bus_stop:"Paraderos",other:"Otros"};

function distanceMetres(a:Position,b:Position){
  const rad=Math.PI/180,dLat=(b.lat-a.lat)*rad,dLon=(b.lon-a.lon)*rad;
  const value=Math.sin(dLat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dLon/2)**2;
  return 6371008.8*2*Math.atan2(Math.sqrt(value),Math.sqrt(1-value));
}

export function CampusMap(){
  const mapRef=useRef<MapLibreMap|null>(null);
  const [places,setPlaces]=useState<Place[]>([]),[query,setQuery]=useState(""),[category,setCategory]=useState(""),[selectedId,setSelectedId]=useState<number|null>(null);
  const [view,setView]=useState<"map"|"list">("map"),[userPosition,setUserPosition]=useState<Position|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
  const [mapReady,setMapReady]=useState(0);
  const load=useCallback(async()=>{setLoading(true);try{const params=new URLSearchParams({limit:"300"});if(query.trim())params.set("q",query.trim());if(category)params.set("category",category);const response=await fetch(`${API_URL}/geo/places?${params}`,{cache:"no-store"});if(!response.ok)throw new Error("La API geográfica no respondió");const body=await response.json() as {data:Place[]};setPlaces(body.data);setError("");}catch(reason){setError(reason instanceof Error?reason.message:"No se pudo cargar el mapa");}finally{setLoading(false);}},[query,category]);
  useEffect(()=>{const timer=window.setTimeout(()=>void load(),250);return()=>window.clearTimeout(timer)},[load]);
  const selected=places.find(place=>place.id===selectedId)??null;
  const categoryOptions=useMemo(()=>Array.from(new Set(places.map(place=>place.category))).sort(),[places]);

  const prepareMap=useCallback((map:MapLibreMap)=>{mapRef.current=map;map.addSource("places",{type:"geojson",data:{type:"FeatureCollection",features:[]}});map.addLayer({id:"places",type:"circle",source:"places",paint:{"circle-radius":["case",["boolean",["get","reviewed"],false],8,6],"circle-color":["case",["boolean",["get","reviewed"],false],"#16745a","#db9d2e"],"circle-stroke-color":"#fff","circle-stroke-width":2}});map.on("click","places",event=>{const id=Number(event.features?.[0]?.properties?.id);if(id)setSelectedId(id)});map.on("mouseenter","places",()=>map.getCanvas().style.cursor="pointer");map.on("mouseleave","places",()=>map.getCanvas().style.cursor="");setMapReady(value=>value+1)},[]);
  const disposeMap=useCallback(()=>{mapRef.current=null},[]);
  useEffect(()=>{const map=mapRef.current;if(!map?.isStyleLoaded())return;(map.getSource("places") as GeoJSONSource)?.setData({type:"FeatureCollection",features:places.map(place=>({type:"Feature",properties:{id:place.id,name:place.name,reviewed:place.reviewed},geometry:{type:"Point",coordinates:[place.longitude,place.latitude]}}))})},[places,mapReady]);
  const choose=(place:Place)=>{setSelectedId(place.id);setView("map");mapRef.current?.easeTo({center:[place.longitude,place.latitude],zoom:17,duration:650})};
  const locate=()=>{if(!navigator.geolocation){setError("Este navegador no ofrece geolocalización");return}navigator.geolocation.getCurrentPosition(position=>{const point={lat:position.coords.latitude,lon:position.coords.longitude};setUserPosition(point);mapRef.current?.easeTo({center:[point.lon,point.lat],zoom:16})},()=>setError("No se concedió permiso para acceder a tu ubicación"),{enableHighAccuracy:true,timeout:8000})};
  return <section><div className="page-heading"><div><span className="eyebrow" style={{color:"#925b12"}}>Exploración geográfica</span><h1>Mapa del campus</h1><p>Consulta registros geográficos por fuente y estado de revisión. Un registro importado no equivale a información oficial de la UNA.</p></div><button className="button secondary" onClick={locate}><Crosshair size={17}/>Usar mi ubicación</button></div>
    <div className="campus-toolbar"><label className="map-search"><Search size={17}/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Buscar biblioteca, cafetería o servicio" aria-label="Buscar lugares"/></label><select value={category} onChange={event=>setCategory(event.target.value)} aria-label="Filtrar categoría"><option value="">Todas las categorías</option>{categoryOptions.map(value=><option value={value} key={value}>{categories[value]??value}</option>)}</select><div className="view-toggle"><button className={view==="map"?"active":""} onClick={()=>setView("map")}><MapIcon size={16}/>Mapa</button><button className={view==="list"?"active":""} onClick={()=>setView("list")}><List size={16}/>Lista</button></div></div>
    {error&&<div className="error-state"><TriangleAlert/><span>{error}</span><button className="button secondary" onClick={()=>void load()}><RefreshCw size={15}/>Reintentar</button></div>}
    <div className={`campus-layout ${view}`}><div className="campus-map-wrap"><ReliableMap className="campus-map" ariaLabel="Mapa interactivo del campus" center={[-70.015,-15.828]} zoom={14} onReady={prepareMap} onDispose={disposeMap}/><div className="map-legend"><span><i className="verified"/>Revisado</span><span><i/>Importado sin revisar</span></div></div><aside className="places-list">{loading?<div className="skeleton-list"/>:places.length===0?<div className="empty-state"><Building2/><strong>Sin resultados</strong><span>Ajusta la búsqueda o verifica la API.</span></div>:places.map(place=><button onClick={()=>choose(place)} className={selectedId===place.id?"selected":""} key={place.id}><div className="place-icon"><Building2 size={18}/></div><div><strong>{place.name}</strong><span>{categories[place.category]??place.category}</span><small>{place.source==="osm"?"OpenStreetMap":place.source} · {place.reviewed?"revisado":"pendiente de revisión"}</small>{userPosition&&<small>{Math.round(distanceMetres(userPosition,{lat:place.latitude,lon:place.longitude}))} m en línea recta</small>}</div></button>)}</aside></div>
    {selected&&<div className="place-detail"><button className="close-detail" onClick={()=>setSelectedId(null)} aria-label="Cerrar detalle">×</button><div className="place-icon large"><Building2/></div><div><span className={selected.reviewed?"source-badge verified":"source-badge pending"}>{selected.reviewed?<><ShieldCheck size={13}/> Revisado</>:<><TriangleAlert size={13}/> Sin revisión institucional</>}</span><h2>{selected.name}</h2><p>{categories[selected.category]??selected.category} · Fuente: {selected.source}</p>{userPosition&&<p><Navigation size={14}/> Distancia directa aproximada: {Math.round(distanceMetres(userPosition,{lat:selected.latitude,lon:selected.longitude}))} m. No constituye una ruta peatonal.</p>}</div></div>}
    <p className="map-attribution-note">Datos geográficos con atribución © OpenStreetMap contributors (ODbL). Los registros no revisados se muestran en ámbar.</p>
  </section>;
}
