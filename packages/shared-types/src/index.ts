export type UserRole = "student" | "moderator" | "admin" | "superadmin";
export type VerificationStatus = "demonstration" | "pending" | "verified" | "rejected";
export type TrackingStatus = "live" | "stale" | "offline" | "demonstration";

export interface Facility {
  id: number;
  name: string;
  category: string;
  description?: string | null;
  lat: number;
  lon: number;
  verification_status?: VerificationStatus;
  opening_hours?: string | null;
  accessibility?: string | null;
  distance_m?: number | null;
}

export interface Paginated<T> {
  data: T[];
  limit?: number;
  offset?: number;
  total?: number;
}

export interface ApiHealth {
  status: "ok" | "degraded";
  database?: string;
  postgis?: string;
  geo_places?: number;
}
