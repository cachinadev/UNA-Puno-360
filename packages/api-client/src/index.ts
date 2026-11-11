import type { ApiHealth, Facility, Paginated } from "@una/shared-types";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export class UnaApiClient {
  constructor(private baseUrl: string, private getToken?: () => string | null) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = this.getToken?.();
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(response.status, body.detail ?? "No se pudo completar la solicitud");
    }
    return response.json() as Promise<T>;
  }

  health = () => this.request<ApiHealth>("/health");
  facilities = (query = "") => this.request<Paginated<Facility> | Facility[]>(`/facilities/search${query ? `?${query}` : ""}`);
  routes = () => this.request<Paginated<unknown> | unknown[]>("/transport/routes");
  books = (query = "") => this.request<Paginated<unknown> | unknown[]>(`/library/books${query ? `?q=${encodeURIComponent(query)}` : ""}`);
  menus = () => this.request<Paginated<unknown> | unknown[]>("/dining/menus");
  groups = () => this.request<Paginated<unknown> | unknown[]>("/community/groups");
  events = () => this.request<Paginated<unknown> | unknown[]>("/community/events");
  login = (email: string, password: string) => this.request<{access_token:string;refresh_token:string}>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}
