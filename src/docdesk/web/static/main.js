// Wires the page: sign in, ask, show the answer and the retrieval panel.
import { getToken, login, register, retrieve, query, logout } from "/static/api.js";
import { el, clear, show } from "/static/dom.js";
import { outcomeOf, renderBadge, renderAnswer, renderUnavailable, renderChunks, showResult } from "/static/render.js";

const EXAMPLES = [
  "How does rubella show up in someone who gets symptoms?",
  "Which foods contain folic acid?",
  "How is tetanus prevented?",
];
const $ = (id) => document.getElementById(id);

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").className = isError ? "error" : "";
}

function refreshPanels() {
  const signedIn = Boolean(getToken());
  show($("auth"), !signedIn);
  show($("ask"), signedIn);
}

function fail(result, fallback) {
  setStatus(result.error ? result.error.message : fallback, true);
}

async function submitAuth(action) {
  if (!$("auth-form").reportValidity()) return;
  setStatus("Working...");
  const email = $("email").value.trim();
  const password = $("password").value;
  if (action === "register") {
    const created = await register(email, password);
    if (created.status !== 201) return fail(created, "Could not register.");
  }
  const result = await login(email, password);
  if (!result.data) return fail(result, "Could not sign in.");
  $("password").value = "";
  setStatus("Signed in.");
  refreshPanels();
  $("question").focus();
}

function sessionExpired() {
  logout();
  refreshPanels();
  setStatus("Your session ended. Please sign in again.", true);
}

function unavailableMessage(result) {
  if (result.status === 503) return "The answer service is not available on this server right now. You can still read the search results below.";
  if (result.status === 429) return "Too many requests. Please wait a moment and try again.";
  return "Something went wrong while writing the answer. You can still read the search results below.";
}

function chunkNote(chunks) {
  return chunks.length ? "Top " + chunks.length + " chunks, best first. The score is the search rank score, higher is closer, only useful for comparing chunks here." : "The search found nothing.";
}

function showAnswered(data, chunks) {
  const kind = outcomeOf(data);
  renderBadge(kind);
  renderAnswer(data);
  show($("retrieval"), kind !== "refused");
  renderChunks(chunks, chunkNote(chunks));
}

async function ask(question) {
  $("ask-btn").disabled = true;
  showResult(false);
  setStatus("Searching the documents...");
  const found = await retrieve(question);
  setStatus("Writing the answer...");
  const answer = await query(question);
  $("ask-btn").disabled = false;
  if (found.status === 401 || answer.status === 401) return sessionExpired();
  const chunks = found.data ? found.data.chunks : [];
  if (answer.data) {
    showAnswered(answer.data, chunks);
  } else {
    renderBadge("unavailable");
    renderUnavailable(unavailableMessage(answer));
    show($("retrieval"), true);
    renderChunks(chunks, chunkNote(chunks));
  }
  setStatus("");
  showResult(true);
  $("result-title").focus();
}

function init() {
  const list = $("examples");
  clear(list);
  for (const text of EXAMPLES) {
    const button = el("button", { type: "button", text });
    button.addEventListener("click", () => { $("question").value = text; $("question").focus(); });
    list.append(el("li", {}, button));
  }
  $("result-title").setAttribute("tabindex", "-1");
  $("auth-form").addEventListener("submit", (e) => { e.preventDefault(); submitAuth("login"); });
  $("register-btn").addEventListener("click", () => submitAuth("register"));
  $("logout-btn").addEventListener("click", () => { logout(); showResult(false); refreshPanels(); setStatus(""); });
  $("ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const question = $("question").value.trim();
    if (question) ask(question);
  });
  refreshPanels();
}

init();
