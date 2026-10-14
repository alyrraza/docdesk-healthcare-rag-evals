// Turns API results into DOM nodes. Every string from the server goes in as text.
import { el, clear, show } from "/static/dom.js";

const BADGES = {
  answered: ["Answered", ""],
  abstained: ["Abstained", "The sources do not cover this."],
  refused: ["Refused", "Dose or diagnosis questions are not answered."],
  unavailable: ["Answer unavailable", "Generation is not available, the search results are below."],
};

// Abstained with reason unsafe_request is the policy refusal; other abstains are not.
export function outcomeOf(data) {
  if (!data.abstained) return "answered";
  return data.abstain_reason === "unsafe_request" ? "refused" : "abstained";
}

export function renderBadge(kind) {
  const badge = document.getElementById("badge");
  badge.className = "badge " + kind;
  badge.textContent = BADGES[kind][0];
  document.getElementById("badge-note").textContent = BADGES[kind][1];
}

function toggle(head, body, forceOpen = false) {
  const open = forceOpen || head.getAttribute("aria-expanded") !== "true";
  head.setAttribute("aria-expanded", String(open));
  body.hidden = !open;
}

// Splits the answer on [c1] style labels and swaps each known one for a numbered button.
function answerNodes(text, numbers, onCite) {
  const nodes = [];
  for (const part of text.split(/(\[c\d+\])/)) {
    const label = part.slice(1, -1);
    if (part.startsWith("[") && numbers.has(label)) {
      const n = numbers.get(label);
      const button = el("button", { type: "button", class: "cite-btn", "aria-label": "Source " + n }, "[" + n + "]");
      button.addEventListener("click", () => onCite(label));
      nodes.push(button);
    } else {
      nodes.push(document.createTextNode(part));
    }
  }
  return nodes;
}

function citationItem(citation, number) {
  const body = el("div", { class: "src", id: "src-" + citation.label, hidden: "" });
  const page = citation.page ? ", page " + citation.page : "";
  body.append(el("small", { text: citation.document_title + page }), document.createTextNode(citation.text));
  const head = el("button", { type: "button", "aria-expanded": "false", "aria-controls": body.id });
  head.append(el("strong", { text: "[" + number + "]" }), el("span", { text: citation.document_title }));
  head.addEventListener("click", () => toggle(head, body));
  return el("div", { class: "cite" }, head, body);
}

export function renderAnswer(data) {
  const numbers = new Map(data.citations.map((c, i) => [c.label, i + 1]));
  const list = document.getElementById("citations");
  clear(list);
  list.append(...data.citations.map((c, i) => citationItem(c, i + 1)));
  const open = (label) => {
    const body = document.getElementById("src-" + label);
    toggle(body.previousElementSibling, body, true);
    body.previousElementSibling.focus();
  };
  const answer = document.getElementById("answer");
  clear(answer);
  answer.append(...answerNodes(data.answer, numbers, open));
  document.getElementById("result-disclaimer").textContent = data.disclaimer;
}

export function renderUnavailable(message) {
  clear(document.getElementById("citations"));
  document.getElementById("answer").textContent = message;
  document.getElementById("result-disclaimer").textContent =
    "This is general information from the provided documents and is not medical advice.";
}

export function renderChunks(chunks, note) {
  const list = document.getElementById("chunks");
  clear(list);
  document.getElementById("retrieval-note").textContent = note;
  for (const chunk of chunks) {
    const meta = chunk.document_title + ", score " + chunk.score.toFixed(3);
    list.append(el("li", {}, el("div", { class: "meta", text: meta }), el("div", { class: "snippet", text: chunk.text })));
  }
  document.getElementById("retrieval").open = false;
}

export function showResult(visible) {
  show(document.getElementById("result"), visible);
}
