import { useEffect, useState } from "react";
import { ApiError, fetchReviewHistory, submitReview, type ReviewResult } from "./api";
import { SAMPLE_DOCUMENTS } from "./sampleDocuments";

type ViewState = "idle" | "loading" | "success" | "error";

const FIELD_LABELS: Record<string, string> = {
  legal_business_name: "Legal business name",
  registration_number: "Registration number",
  registered_address: "Registered address",
  issue_date: "Issue date",
  expiration_date: "Expiration date",
};

function formatStatus(status: ReviewResult["status"]): string {
  return status === "ready_for_reviewer" ? "Ready for reviewer" : "Needs attention";
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function App() {
  const [selectedId, setSelectedId] = useState(SAMPLE_DOCUMENTS[0].id);
  const [documentText, setDocumentText] = useState(SAMPLE_DOCUMENTS[0].text);
  const [viewState, setViewState] = useState<ViewState>("idle");
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [history, setHistory] = useState<ReviewResult[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const selectedDocument = SAMPLE_DOCUMENTS.find((doc) => doc.id === selectedId) ?? SAMPLE_DOCUMENTS[0];

  async function loadHistory() {
    try {
      const rows = await fetchReviewHistory(10);
      setHistory(rows);
      setHistoryError(null);
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : "Could not load review history.");
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  function handleSelectSample(id: string) {
    const doc = SAMPLE_DOCUMENTS.find((d) => d.id === id);
    if (!doc) return;
    setSelectedId(id);
    setDocumentText(doc.text);
    setViewState("idle");
    setResult(null);
    setErrorMessage(null);
  }

  async function handleReview() {
    setViewState("loading");
    setErrorMessage(null);
    setResult(null);

    try {
      const review = await submitReview(selectedDocument.documentName, documentText);
      setResult(review);
      setViewState("success");
      loadHistory();
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Something went wrong while reviewing this document.");
      setViewState("error");
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Client Onboarding Document Review</h1>
        <span className="demo-badge">Synthetic demo data — not real client records</span>
        <p className="disclaimer">
          This is an independent portfolio demo inspired by a public job posting. It is not affiliated with or
          endorsed by CIBC. AI extracts fields below; deterministic checks decide which ones need attention; a
          human reviewer makes the actual onboarding decision.
        </p>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>1. Choose a sample document</h2>
          <div className="sample-list">
            {SAMPLE_DOCUMENTS.map((doc) => (
              <label key={doc.id} className={`sample-option ${doc.id === selectedId ? "selected" : ""}`}>
                <input
                  type="radio"
                  name="sample-document"
                  value={doc.id}
                  checked={doc.id === selectedId}
                  onChange={() => handleSelectSample(doc.id)}
                />
                {doc.label}
              </label>
            ))}
          </div>

          <h3>Document text</h3>
          <textarea
            className="document-text"
            value={documentText}
            onChange={(e) => setDocumentText(e.target.value)}
            rows={14}
            spellCheck={false}
          />

          <button className="review-button" onClick={handleReview} disabled={viewState === "loading"}>
            {viewState === "loading" ? "Reviewing…" : "Review document"}
          </button>
        </section>

        <section className="panel">
          <h2>2. Review result</h2>

          {viewState === "idle" && <p className="empty-state">Select a document and click Review document.</p>}

          {viewState === "loading" && <p className="loading-state">Extracting fields and running checks…</p>}

          {viewState === "error" && (
            <div className="error-state">
              <p>
                <strong>Could not complete this review.</strong>
              </p>
              <p>{errorMessage}</p>
              <p className="muted">No review was saved for this attempt.</p>
            </div>
          )}

          {viewState === "success" && result && (
            <div className="result">
              <div className={`status-banner ${result.status}`}>{formatStatus(result.status)}</div>

              <h3>Extracted fields</h3>
              <dl className="field-list">
                {Object.entries(result.extracted_fields).map(([key, value]) => (
                  <div className="field-row" key={key}>
                    <dt>{FIELD_LABELS[key] ?? key}</dt>
                    <dd>{value ?? <span className="muted">(not found)</span>}</dd>
                  </div>
                ))}
              </dl>

              <h3>Checks</h3>
              {result.issues.length === 0 ? (
                <p className="checks-passed">All deterministic checks passed.</p>
              ) : (
                <ul className="issue-list">
                  {result.issues.map((issue, i) => (
                    <li key={i} className="issue-item">
                      <strong>{FIELD_LABELS[issue.field] ?? issue.field}:</strong> {issue.message}
                    </li>
                  ))}
                </ul>
              )}

              <p className="muted small">
                This status reflects automated checks only. A human reviewer is responsible for the onboarding
                decision.
              </p>
            </div>
          )}
        </section>
      </main>

      <section className="panel history-panel">
        <h2>Review history</h2>
        {historyError && <p className="error-state">{historyError}</p>}
        {!historyError && history.length === 0 && <p className="empty-state">No reviews saved yet.</p>}
        {!historyError && history.length > 0 && (
          <table className="history-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Status</th>
                <th>Issues</th>
                <th>Reviewed at</th>
              </tr>
            </thead>
            <tbody>
              {history.map((row) => (
                <tr key={row.id}>
                  <td>{row.document_name}</td>
                  <td>
                    <span className={`status-pill ${row.status}`}>{formatStatus(row.status)}</span>
                  </td>
                  <td>{row.issues.length}</td>
                  <td>{formatTimestamp(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
