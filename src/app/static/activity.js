"use strict";

// Filtering changes only this view; signed records and export remain complete.
const filters = document.querySelector("#activity-filters");
const results = document.querySelector("#activity-results");
const timeline = document.querySelector("#event-list");
const events = Array.from(timeline.querySelectorAll("[data-event]"));
const search = document.querySelector("#activity-search");
const category = document.querySelector("#activity-type");
const participant = document.querySelector("#activity-actor");
const grouping = document.querySelector("#activity-group");
const noResults = document.querySelector("#activity-no-results");
const count = document.querySelector("#activity-count");

/** Update the visible history while retaining the original signed sequence. */
function filterActivity() {
  const query = search.value.trim().toLocaleLowerCase("en");
  const visible = events.filter(item =>
    (category.value === "all" || item.dataset.category === category.value) &&
    (participant.value === "all" || item.dataset.actor === participant.value) &&
    (!query || item.textContent.toLocaleLowerCase("en").includes(query))
  );
  results.replaceChildren();
  if (grouping.value === "actor") {
    const groups = new Map();
    visible.forEach(item => {
      const actor = item.dataset.actor;
      if (!groups.has(actor)) {
        const section = document.createElement("section");
        section.className = "activity-group";
        const heading = document.createElement("h3");
        heading.textContent = item.dataset.actorLabel;
        const list = document.createElement("ol");
        list.className = "events";
        section.append(heading, list);
        results.append(section);
        groups.set(actor, list);
      }
      groups.get(actor).append(item);
    });
  } else {
    timeline.replaceChildren(...visible);
    results.append(timeline);
  }
  count.textContent = `Showing ${visible.length} of ${events.length} events`;
  noResults.hidden = visible.length !== 0 || events.length === 0;
  if (events.length === 0) {
    const message = document.createElement("p");
    message.className = "empty";
    message.textContent = "Approve an authorization to record the first event.";
    results.append(message);
  }
}

filters.hidden = false;
document.querySelector(".activity-meta").hidden = false;
filters.addEventListener("submit", event => event.preventDefault());
filters.addEventListener("input", filterActivity);
filters.addEventListener("change", filterActivity);
filters.addEventListener("reset", () => setTimeout(filterActivity, 0));
document.querySelector("#activity-clear").addEventListener("click", () => {
  filters.reset();
  search.focus();
});
filterActivity();
