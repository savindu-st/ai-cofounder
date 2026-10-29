import { FounderInput, VentureState, HumanReviewPayload } from '../types/venture';

export type ExportFormat = 'pdf' | 'docx' | 'html';

export interface DownloadedExport {
  blob: Blob;
  filename: string;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function startVenture(input: FounderInput): Promise<{ venture_id: string; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/ventures/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to start venture: ${res.statusText}`);
  }

  return res.json();
}

export async function getVentureState(ventureId: string): Promise<VentureState> {
  const res = await fetch(`${API_BASE}/api/ventures/${ventureId}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to fetch venture state: ${res.statusText}`);
  }
  return res.json();
}

export async function submitHumanReview(
  ventureId: string,
  review: HumanReviewPayload
): Promise<{ venture_id: string; status: string; action_taken?: string }> {
  const res = await fetch(`${API_BASE}/api/ventures/${ventureId}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(review),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to submit review: ${res.statusText}`);
  }

  return res.json();
}

export function getVentureStreamUrl(ventureId: string): string {
  return `${API_BASE}/api/ventures/${ventureId}/stream`;
}


function extractFilename(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) return fallback;
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return fallback;
    }
  }
  const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return asciiMatch?.[1] || fallback;
}

export async function downloadVentureExport(
  ventureId: string,
  format: ExportFormat,
): Promise<DownloadedExport> {
  const res = await fetch(`${API_BASE}/api/ventures/${ventureId}/export/${format}`, {
    method: 'GET',
    headers: { Accept: format === 'pdf' ? 'application/pdf' : '*/*' },
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to download ${format.toUpperCase()} export: ${res.statusText}`);
  }

  return {
    blob: await res.blob(),
    filename: extractFilename(
      res.headers.get('Content-Disposition'),
      `venture-roadmap.${format}`,
    ),
  };
}

export function saveBlobAsFile(blob: Blob, filename: string): void {
  if (typeof window === 'undefined') {
    throw new Error('File downloads are only available in the browser.');
  }
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}

export async function downloadAndSaveVentureExport(
  ventureId: string,
  format: ExportFormat,
): Promise<void> {
  const { blob, filename } = await downloadVentureExport(ventureId, format);
  saveBlobAsFile(blob, filename);
}
