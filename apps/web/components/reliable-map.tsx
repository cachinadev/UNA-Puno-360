"use client";

import { useEffect,useRef,useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { AlertTriangle,LoaderCircle,RefreshCw } from "lucide-react";

type MapLibrary=typeof import("maplibre-gl");
type Props={
  className:string; ariaLabel:string; center:[number,number]; zoom:number;
  onReady:(map:MapLibreMap,library:MapLibrary)=>void;
  onDispose?:()=>void;
};

const tileUrl=process.env.NEXT_PUBLIC_MAP_TILE_URL||"https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const tileAttribution=process.env.NEXT_PUBLIC_MAP_ATTRIBUTION||'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export function ReliableMap({className,ariaLabel,center,zoom,onReady,onDispose}:Props){
  const node=useRef<HTMLDivElement>(null),map=useRef<MapLibreMap|null>(null);
  const readyCallback=useRef(onReady),disposeCallback=useRef(onDispose);
  const [attempt,setAttempt]=useState(0),[status,setStatus]=useState<"loading"|"ready"|"error">("loading"),[message,setMessage]=useState("");
  useEffect(()=>{readyCallback.current=onReady},[onReady]);
  useEffect(()=>{disposeCallback.current=onDispose},[onDispose]);
  useEffect(()=>{
    if(!node.current)return;let disposed=false;setStatus("loading");setMessage("");
    if(typeof window.WebGLRenderingContext==="undefined"){setStatus("error");setMessage("Este navegador no ofrece WebGL, requerido para mostrar el mapa.");return}
    let observer:ResizeObserver|undefined;let timeout:number|undefined;
    void import("maplibre-gl").then(maplibregl=>{
      if(disposed||!node.current)return;
      try{
        const instance=new maplibregl.Map({container:node.current,center,zoom,
          style:{version:8,sources:{basemap:{type:"raster",tiles:[tileUrl],tileSize:256,attribution:tileAttribution}},layers:[{id:"basemap",type:"raster",source:"basemap"}]}});
        map.current=instance;instance.addControl(new maplibregl.NavigationControl(),"top-right");
        instance.once("load",()=>{if(disposed)return;readyCallback.current(instance,maplibregl);instance.resize()});
        instance.once("idle",()=>{if(!disposed)setStatus("ready")});
        instance.on("error",event=>{if(disposed)return;const text=event.error?.message||"No se pudieron cargar las teselas del mapa.";setMessage(text);setStatus("error")});
        observer=new ResizeObserver(()=>instance.resize());observer.observe(node.current);
        timeout=window.setTimeout(()=>{if(!disposed)setStatus(value=>{if(value==="loading"){setMessage("El mapa tardó demasiado en cargar. Comprueba la conexión con el proveedor de teselas.");return "error"}return value})},12000);
      }catch(reason){setMessage(reason instanceof Error?reason.message:"MapLibre no pudo inicializar WebGL.");setStatus("error")}
    }).catch(reason=>{setMessage(reason instanceof Error?reason.message:"No se pudo cargar MapLibre.");setStatus("error")});
    return()=>{disposed=true;if(timeout)window.clearTimeout(timeout);observer?.disconnect();disposeCallback.current?.();map.current?.remove();map.current=null};
  },[attempt,center[0],center[1],zoom]);
  return <div className={`reliable-map ${className}`} data-map-status={status}>
    <div ref={node} className="reliable-map-canvas" aria-label={ariaLabel}/>
    {status==="loading"&&<div className="map-state loading" role="status"><LoaderCircle/><strong>Cargando mapa…</strong><span>Preparando teselas y capas geográficas.</span></div>}
    {status==="error"&&<div className="map-state error" role="alert"><AlertTriangle/><strong>No se pudo mostrar el mapa</strong><span>{message}</span><button className="button primary" onClick={()=>setAttempt(value=>value+1)}><RefreshCw/>Reintentar</button></div>}
  </div>
}
