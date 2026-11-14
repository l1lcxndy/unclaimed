const form = document.getElementById("ask");
const input = document.getElementById("question");
const log = document.getElementById("log");
const button = form.querySelector("button");
const history = [];

function add(tag, text, className) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text;
  return el;
}

function list(items) {
  const ul = document.createElement("ul");
  items.forEach((item) => ul.append(add("li", item)));
  return ul;
}

function programCard(p) {
  const card = document.createElement("article");
  card.className = "program";
  card.append(add("h3", p.program_name));
  card.append(add("p", p.benefit, "benefit"));
  if (p.eligibility === "some_facts_unknown") card.append(add("p", "You may qualify. A few details still need checking.", "maybe"));
  card.append(add("h4", "Why you match"), add("p", p.why_you_match));
  if (p.documents_required.length) card.append(add("h4", "Documents to bring"), list(p.documents_required));
  card.append(p.cited
    ? add("p", `Source: ${p.source_file}, page ${p.page}`, "source")
    : add("p", `Unverified source (${p.source_file}, page ${p.page}). Check the document yourself.`, "source unverified"));
  return card;
}

function render(question, data) {
  log.append(add("p", question, "you"));
  const reply = document.createElement("div");
  reply.className = "bot";
  reply.append(add("p", data.answer));
  data.programs?.forEach((p) => reply.append(programCard(p)));
  if (data.missing_info?.length) reply.append(add("h4", "Still needed to decide"), list(data.missing_info));
  log.append(reply);
  reply.scrollIntoView({ behavior: "smooth" });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed.");
    render(question, data);
    const names = (data.programs || []).map((p) => p.program_name).join(", ");
    history.push({ role: "user", content: question },
      { role: "assistant", content: names ? `${data.answer}\nPrograms: ${names}` : data.answer });
    input.value = "";
  } catch (err) {
    log.append(add("p", err.message, "error"));
  } finally {
    button.disabled = false;
    button.textContent = "Ask";
  }
});
