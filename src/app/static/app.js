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
    history.replaceState(null, "", "#demo-guide");
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
  requestAnimationFrame(() => document.querySelector("#demo-guide")?.scrollIntoView({block: "start"}));
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

// Guide links reveal the real control instead of duplicating write actions.
document.querySelectorAll("[data-guide-target]").forEach(link => {
  link.addEventListener("click", () => {
    const target = document.getElementById(link.hash.slice(1));
    if (!target) return;
    revealGuideTarget(target);
    if (target.tagName === "DETAILS") target.open = true;
    target.querySelectorAll("details.technical").forEach(details => {
      if (target.classList.contains("message")) details.open = true;
    });
    const control = target.querySelector("button, input, select, summary");
    (control || target).focus({preventScroll: true});
  });
});

// Refresh guidance when the displayed grant expires; never retry an action.
const demoGuide = document.querySelector("[data-guide-expires]");
if (demoGuide) {
  const remaining = Number(demoGuide.dataset.guideExpires) * 1000 - Date.now();
  if (remaining > 0) setTimeout(() => location.reload(), remaining + 250);
}

/** Reveal only the controls or receipt needed by the current guide action. */
function revealGuideTarget(target) {
  document.querySelectorAll(".guide-concealed").forEach(item => item.classList.remove("guide-concealed"));
  document.body.classList.add("guide-open");
  const grant = target.closest(".grant");
  const message = target.closest(".message");
  document.querySelector(".permissions-panel").classList.toggle("guide-concealed", Boolean(message));
  document.querySelector(".inbox-panel").classList.toggle("guide-concealed", !message);
  document.querySelector(".new-authorization").classList.toggle("guide-concealed", target.id !== "new-authorization");
  document.querySelectorAll(".grant").forEach(item => item.classList.toggle("guide-concealed", item !== grant));
  document.querySelectorAll(".message").forEach(item => item.classList.toggle("guide-concealed", item !== message));
  if (grant) {
    if (target !== grant) {
      Array.from(grant.children).forEach(item => item.classList.toggle("guide-concealed", item !== target));
    } else {
      grant.querySelectorAll(".delegation, .delivery-result, .technical, .safety-test, .secondary, .quiet").forEach(item => item.classList.add("guide-concealed"));
    }
    target.querySelectorAll(".safety-test, .technical").forEach(item => item.classList.add("guide-concealed"));
  }
  document.querySelector(".guide-next").classList.toggle("guide-concealed", target.id === "new-authorization");
}

const workspaceMode = document.querySelector("#workspace-mode");
if (workspaceMode) {
  document.body.classList.add("guided-mode");
  if (sessionStorage.getItem("ledger-full-workspace") === "true") {
    document.body.classList.add("full-workspace");
    workspaceMode.textContent = "Return to step-by-step demo";
    workspaceMode.setAttribute("aria-expanded", "true");
  }
  workspaceMode.addEventListener("click", () => {
    const full = document.body.classList.toggle("full-workspace");
    sessionStorage.setItem("ledger-full-workspace", String(full));
    workspaceMode.textContent = full ? "Return to step-by-step demo" : "Show full workspace";
    workspaceMode.setAttribute("aria-expanded", String(full));
  });
}
