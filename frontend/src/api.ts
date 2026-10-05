// Thin client for the backend's three endpoints. No credentials live here --
// the backend holds the LLM API key, and this file never sees it.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ExtractedFields {
  legal_business_name: string | null;
  registration_number: string | null;
  registered_address: string | null;
  issue_date: string | null;
  expiration_date: string | null;
}

export interface ReviewIssue {
  field: string;
  code: string;
  message: string;
}

export type ReviewStatus = "ready_for_reviewer" | "needs_attention";

export interface ReviewResult {
  id: number;
  document_name: string;
  status: ReviewStatus;
  extracted_fields: ExtractedFields;
  issues: ReviewIssue[];
  created_at: string;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // response wasn't JSON; fall through to generic message
  }
  return `Request failed with status ${response.status}.`;
}

export async function submitReview(documentName: string, text: string): Promise<ReviewResult> {
  const response = await fetch(`${API_BASE_URL}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_name: documentName, text }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  return response.json();
}

export async function fetchReviewHistory(limit = 10): Promise<ReviewResult[]> {
  const response = await fetch(`${API_BASE_URL}/reviews?limit=${limit}`);

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  return response.json();
}
