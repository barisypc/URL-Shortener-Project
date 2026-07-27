import { getAuthHeaders } from "./auth";
import { API_BASE } from "../config";

export async function listAuditLog(limit = 100) {
  const response = await fetch(`${API_BASE}/api/admin/audit-log?limit=${limit}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to load audit log");
  }

  return data;
}