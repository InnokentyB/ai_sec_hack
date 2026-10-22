"use strict";
const feedback = document.querySelector("#feedback");
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const reasons = {
  SCOPE_ESCALATION: "Blocked: the proposal exceeds the authorized scope.",
  DOCUMENT_CHANGED: "Blocked: the document differs from the authorized snapshot.",
  LIMIT_RESERVED_OR_USED: "Blocked: the shared slot is already reserved or used.",
  REVOKED: "Blocked: the owner revoked the authorization.",
  EXPIRED: "Blocked: the authorization has expired.",
  REDELEGATION_DENIED: "Further delegation is not allowed.",
  STORAGE_UNAVAILABLE: "Storage is unavailable. Check the saved state after recovery.",
};
async function submit(url, payload, button) {
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  feedback.textContent = "Working… Keep this page open until a result arrives.";
  try {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    const result = await response.json();
    const message = response.ok ? (result.execution_status === "uncertain"
      ? "Delivery status unknown. The slot is reserved; receipt reconciliation is available."
      : "Result saved.") : `${reasons[result.reason] || "Request rejected."} ${result.reason || "INVALID_INPUT"}`;
    sessionStorage.setItem("ledger-feedback", message);
    location.reload();
  } catch (error) {
    feedback.textContent = "No response available. Reload and check the saved status; do not blindly repeat the dispatch.";
  } finally {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}
const previous = sessionStorage.getItem("ledger-feedback");
if (previous) {
  feedback.textContent = previous;
  sessionStorage.removeItem("ledger-feedback");
}
document.querySelectorAll("[data-post]").forEach(button => {
  button.addEventListener("click", () => submit(button.dataset.post, undefined, button));
});
const form = document.querySelector("#grant-form");
form.addEventListener("submit", event => {
  event.preventDefault();
  const data = new FormData(form);
  submit("/api/roots", {
    request_id: form.dataset.requestId, document_id: data.get("document_id"),
    recipient_id: data.get("recipient_id"), minutes: Number(data.get("minutes")),
    delegation_allowed: data.has("delegation_allowed"),
  }, form.querySelector('button[type="submit"]'));
});
function preview() {
  const selected = form.querySelector("#document").value;
  document.querySelectorAll("[data-document]").forEach(item => {
    item.hidden = item.dataset.document !== selected;
  });
}
form.querySelector("#document").addEventListener("change", preview);
form.addEventListener("reset", () => { setTimeout(preview, 0); feedback.textContent = "Form cancelled. No authorization was created."; });
document.querySelectorAll("[data-timestamp]").forEach(item => {
  const date = new Date(Number(item.dataset.timestamp) * 1000);
  item.textContent = date.toLocaleString("en-GB");
  item.dateTime = date.toISOString();
});
