import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout(){return <><StatusBar style="light"/><Stack screenOptions={{headerStyle:{backgroundColor:"#0a2342"},headerTintColor:"white",headerTitleStyle:{fontWeight:"700"}}}><Stack.Screen name="index" options={{title:"UNA Puno 360"}}/><Stack.Screen name="services" options={{title:"Servicios del campus"}}/><Stack.Screen name="transport" options={{title:"Transporte"}}/></Stack></>}
