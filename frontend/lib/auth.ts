export interface AuthUser {
  token: string;
  role: "consultant" | "client";
  engagement_id?: string;
}

export function saveAuth(user: AuthUser) {
  localStorage.setItem("token", user.token);
  localStorage.setItem("role", user.role);
  if (user.engagement_id) {
    localStorage.setItem("engagement_id", user.engagement_id);
  }
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("engagement_id");
}

export function getAuth(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("token");
  const role = localStorage.getItem("role") as "consultant" | "client" | null;
  if (!token || !role) return null;
  return {
    token,
    role,
    engagement_id: localStorage.getItem("engagement_id") || undefined,
  };
}

export function isConsultant(): boolean {
  return getAuth()?.role === "consultant";
}

export function isClient(): boolean {
  return getAuth()?.role === "client";
}
