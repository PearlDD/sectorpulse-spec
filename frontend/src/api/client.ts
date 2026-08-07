const BASE = "/api";

// --- Types ---

export interface HealthStatus {
  status: string;
  last_run: string | null;
}

export interface SectorScore {
  [ticker: string]: number;
}

export interface Allocation {
  [ticker: string]: number;
}

export interface RRGPoint {
  ticker: string;
  rs_ratio: number;
  rs_momentum: number;
  quadrant: string;
  trail?: { rs_ratio: number; rs_momentum: number }[];
}

export interface Report {
  id: number;
  created_at: string | null;
  trigger: string;
  cycle_phase: string;
  cycle_confidence: number;
  risk_level: string;
  narrative: string;
  sector_scores: SectorScore;
  allocation: Allocation;
  rrg_data: Record<string, RRGPoint> | null;
  raw_macro_data: Record<string, unknown> | null;
}

export interface ReportSummary {
  id: number;
  created_at: string | null;
  cycle_phase: string;
  risk_level: string;
  trigger: string;
}

export interface SectorData {
  sector_scores: SectorScore;
  allocation: Allocation;
}

export interface RRGData {
  rrg_data: Record<string, RRGPoint> | null;
}

export interface ScheduleInfo {
  active: boolean;
  next_run: string | null;
}

// --- Fetch helper ---

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// --- API functions ---

export function fetchHealth(): Promise<HealthStatus> {
  return request("/health");
}

export function fetchReports(
  limit = 20,
  offset = 0,
): Promise<ReportSummary[]> {
  return request(`/reports?limit=${limit}&offset=${offset}`);
}

export function fetchLatestReport(): Promise<Report | null> {
  return request<Report>("/reports/latest").catch((err: Error) => {
    if (err.message.includes("404")) return null;
    throw err;
  });
}

export function fetchReport(id: number): Promise<Report> {
  return request(`/reports/${id}`);
}

export function triggerRun(): Promise<Report> {
  return request("/run", { method: "POST" });
}

export function fetchSectors(): Promise<SectorData> {
  return request("/sectors");
}

export function fetchRRG(): Promise<RRGData> {
  return request("/sectors/rrg");
}

export function fetchSchedule(): Promise<ScheduleInfo> {
  return request("/schedule");
}
