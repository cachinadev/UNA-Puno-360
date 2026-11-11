import { expect, test, type APIRequestContext } from "@playwright/test";

const API="http://127.0.0.1:8000";
async function account(request:APIRequestContext,label:string){
  const nonce=`${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const email=`pw-${label}-${nonce}@example.org`;
  const password="PruebaSegura2026";
  const created=await request.post(`${API}/auth/register`,{data:{email,password,display_name:`Prueba ${label}`,faculty:"Facultad DEMO"}});
  expect(created.status()).toBe(201);
  const registration=await created.json();
  const verified=await request.post(`${API}/auth/verify-email`,{data:{token:registration.dev_verification_token}});
  expect(verified.ok()).toBeTruthy();
  const login=await request.post(`${API}/auth/login`,{data:{email,password}});
  expect(login.ok()).toBeTruthy();
  return {email,...await login.json()};
}

test("invitado ve agenda pública pero no funciones privadas",async({page})=>{
  await page.goto("/eventos");
  await expect(page.getByText("Agenda pública")).toBeVisible();
  await expect(page.locator(".event-card").first()).toBeVisible();
  await expect(page.getByRole("link",{name:"Ingresa para inscribirte"}).first()).toBeVisible();
  await page.goto("/comunidad");
  await expect(page.getByText("UNA Comunidad requiere una cuenta")).toBeVisible();
  await page.goto("/admin");
  await expect(page.getByText("Acceso administrativo")).toBeVisible();
});

test("estudiantes publican, comentan y no acceden a administración",async({page,request})=>{
  const author=await account(request,"Autor");
  const reader=await account(request,"Lector");
  const body=`Publicación persistente ${Date.now()}`;
  const edited=`${body} editada`;
  await page.goto("/");
  await page.evaluate(token=>sessionStorage.setItem("una_access_token",token),author.access_token);
  await page.goto("/comunidad");
  await expect(page.getByText("Prueba Autor").first()).toBeVisible();
  await page.getByLabel("¿Qué quieres compartir con la comunidad UNA?").fill(body);
  await page.getByRole("button",{name:"Publicar",exact:true}).click();
  const card=page.locator(".post-card").filter({hasText:body});
  await expect(card).toBeVisible();
  await page.reload();
  await expect(page.locator(".post-card").filter({hasText:body})).toBeVisible();
  const feed=await request.get(`${API}/community/feed?limit=50`,{headers:{Authorization:`Bearer ${author.access_token}`}});
  const post=(await feed.json()).data.find((item:{body:string})=>item.body===body);
  expect(post).toBeTruthy();
  const comment=await request.post(`${API}/community/posts/${post.id}/comments`,{headers:{Authorization:`Bearer ${reader.access_token}`},data:{body:"Comentario persistente de otra cuenta",parent_id:null}});
  expect(comment.status()).toBe(201);
  const reaction=await request.put(`${API}/community/posts/${post.id}/reaction`,{headers:{Authorization:`Bearer ${reader.access_token}`},data:{kind:"like"}});
  expect(reaction.ok()).toBeTruthy();
  const forbidden=await request.patch(`${API}/community/posts/${post.id}`,{headers:{Authorization:`Bearer ${reader.access_token}`},data:{body:"Intento ajeno",category:"general"}});
  expect(forbidden.status()).toBe(403);
  const adminForbidden=await request.get(`${API}/admin/overview`,{headers:{Authorization:`Bearer ${author.access_token}`}});
  expect(adminForbidden.status()).toBe(403);
  await page.reload();
  const updatedCard=page.locator(".post-card").filter({hasText:body});
  await expect(updatedCard.getByText("1 reacciones")).toBeVisible();
  await updatedCard.getByRole("button",{name:/Comentar/}).click();
  await expect(updatedCard.getByText("Comentario persistente de otra cuenta")).toBeVisible();
  page.once("dialog",dialog=>dialog.accept(edited));
  await updatedCard.getByRole("button",{name:"Editar"}).click();
  await expect(page.locator(".post-card").filter({hasText:edited})).toBeVisible();
  await expect(page.locator('a[href="/admin"]')).toHaveCount(0);
  await page.goto("/admin");
  await expect(page.getByText("Acceso denegado")).toBeVisible();
  await page.goto("/comunidad");
  const finalCard=page.locator(".post-card").filter({hasText:edited});
  page.once("dialog",dialog=>dialog.accept());
  await finalCard.getByRole("button",{name:"Eliminar"}).click();
  await expect(finalCard).toHaveCount(0);
});
