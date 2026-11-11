import { Link } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

const cards=[
  ["🚌","Transporte","Rutas y estado de telemetría","/transport"],
  ["📍","Mapa y servicios","Lugares verificados cerca de ti","/services"],
  ["📚","Biblioteca","Catálogo y sedes",null],
  ["🍽️","Comedor","Menús y anuncios",null],
  ["💬","Comunidad","Grupos y publicaciones",null],
  ["📅","Eventos","Agenda universitaria",null],
] as const;

export default function Home(){return <ScrollView style={s.screen} contentContainerStyle={s.content}><View style={s.hero}><Text style={s.eyebrow}>PANEL ESTUDIANTIL</Text><Text style={s.title}>Buenas tardes 👋</Text><Text style={s.subtitle}>Tu universidad en tus manos, con información clara y responsable.</Text></View><Text style={s.heading}>Servicios para ti</Text><View style={s.grid}>{cards.map(([emoji,title,desc,href])=>{const card=<View style={s.card}><Text style={s.emoji}>{emoji}</Text><Text style={s.cardTitle}>{title}</Text><Text style={s.cardText}>{desc}</Text></View>;return href?<Link key={title} href={href} asChild><View style={{width:"48%"}}>{card}</View></Link>:<View key={title} style={{width:"48%"}}>{card}</View>})}</View><View style={s.notice}><Text style={s.noticeTitle}>MVP independiente</Text><Text style={s.cardText}>Los datos demostrativos se identifican y no se presentan como información oficial de la universidad.</Text></View></ScrollView>}

const s=StyleSheet.create({screen:{flex:1,backgroundColor:"#f4f7fb"},content:{padding:18,paddingBottom:50},hero:{backgroundColor:"#123d6a",borderRadius:22,padding:24,marginBottom:24},eyebrow:{color:"#e0b85f",fontSize:11,fontWeight:"800",letterSpacing:1.5},title:{color:"white",fontSize:30,fontWeight:"800",marginTop:9},subtitle:{color:"#d5e5f5",fontSize:15,lineHeight:22,marginTop:6},heading:{fontSize:19,fontWeight:"800",color:"#10243b",marginBottom:12},grid:{flexDirection:"row",flexWrap:"wrap",gap:12},card:{backgroundColor:"white",borderRadius:16,padding:15,minHeight:145,borderWidth:1,borderColor:"#dce4ed"},emoji:{fontSize:26},cardTitle:{fontWeight:"800",color:"#10243b",marginTop:11},cardText:{color:"#66768a",fontSize:12,lineHeight:18,marginTop:4},notice:{backgroundColor:"#fff6e4",borderLeftWidth:4,borderLeftColor:"#d6a84b",padding:16,borderRadius:12,marginTop:22},noticeTitle:{fontWeight:"800",color:"#5c4215"}});
