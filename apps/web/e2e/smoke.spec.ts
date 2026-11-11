import { expect, test } from "@playwright/test";

test("student dashboard exposes the principal services", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Buenas tardes/ })).toBeVisible();
  await expect(page.getByText("Rutas universitarias")).toBeVisible();
  await expect(page.getByText("Biblioteca", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Comedor universitario")).toBeVisible();
  await expect(page.getByText("MVP independiente")).toBeVisible();
});

test("admin page does not fabricate metrics without authorization", async ({ page }) => {
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Centro de administración" })).toBeVisible();
  await expect(page.getByText("Acceso administrativo")).toBeVisible();
  await expect(page.getByText(/API vuelve a validar el rol/)).toBeVisible();
});

test("login form performs browser validation", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill("estudiante@example.edu.pe");
  await page.getByLabel("Contraseña").fill("corta");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByLabel("Contraseña")).toHaveJSProperty("validity.tooShort", true);
});

test("transport demo exposes working simulation controls", async ({ page }) => {
  await page.route("**/transport/demo/snapshot?**", async route => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({ mode:"demonstration", generated_at:"2026-11-10T15:00:00Z",
      disclaimer:"Datos sintéticos", data:[{ id:"DEMO-UNA-1", name:"Circuito Lago (DEMO)",
        description:"Recorrido sintético", official_verified:false,
        geometry:{type:"LineString",coordinates:[[-70.02,-15.83],[-70.01,-15.825],[-70.02,-15.83]]},
        stops:[{id:"S1",name:"Inicio DEMO",stop_order:0,lat:-15.83,lon:-70.02,official_verified:false}],
        vehicles:[{id:"B1",public_label:"Bus demo 01",route_id:"DEMO-UNA-1",provider:"demo",
          position:{lon:-70.015,lat:-15.827},heading:90,speed_kph:22,status:"moving",occupancy:"medium",age_seconds:0,
          next_stop:{id:"S1",name:"Inicio DEMO",distance_m:320,eta_seconds:55},upcoming_stops:[{id:"S1",name:"Inicio DEMO",distance_m:320,eta_seconds:55}]}]}] })
  }));
  await page.goto("/transporte");
  await expect(page.getByRole("heading",{name:"Transporte universitario"})).toBeVisible();
  await expect(page.getByText("Bus demo 01")).toBeVisible();
  await page.getByRole("button",{name:"Pausar simulación"}).click();
  await expect(page.getByText("Simulación pausada")).toBeVisible();
  await page.getByRole("button",{name:"5×"}).click();
  await expect(page.getByRole("button",{name:"5×"})).toHaveClass(/selected/);
});

test("campus map distinguishes unreviewed imported records", async ({ page }) => {
  await page.route("**/geo/places?**", async route => route.fulfill({contentType:"application/json",body:JSON.stringify({data:[{
    id:1,source:"osm",source_id:"node/1",name:"Biblioteca importada",category:"library",reviewed:false,latitude:-15.827,longitude:-70.016,tags:{}
  }]})}));
  await page.goto("/mapa-campus");
  await expect(page.getByRole("heading",{name:"Mapa del campus"})).toBeVisible();
  await expect(page.getByText("Biblioteca importada")).toBeVisible();
  await expect(page.getByText(/pendiente de revisión/)).toBeVisible();
});
