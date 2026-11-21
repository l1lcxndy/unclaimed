const form = document.getElementById("ask");
const input = document.getElementById("question");
const log = document.getElementById("log");
const button = form.querySelector("button");
const region = document.getElementById("region");
const history = [];

fetch("/regions").then((r) => r.json()).then((names) => {
  if (names.length < 2) return;
  names.forEach((name) => region.append(new Option(name, name)));
  document.getElementById("region-row").hidden = false;
}).catch(() => {});

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

async function* events(res) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  for (;;) {
    const { done, value } = await reader.read();
    buffered += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffered.split("\n");
    buffered = lines.pop();
    for (const line of lines) if (line.trim()) yield JSON.parse(line);
    if (done) return;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  button.disabled = true;
  button.textContent = "Checking…";
  log.append(add("p", question, "you"));
  const reply = document.createElement("div");
  reply.className = "bot";
  const status = add("p", "Searching the program documents…", "status");
  reply.append(status);
  log.append(reply);
  reply.scrollIntoView({ behavior: "smooth" });
  const found = [];
  try {
    const res = await fetch("/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, region: region.value || null }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(typeof data.detail === "string" ? data.detail : "Request failed.");
    }
    for await (const ev of events(res)) {
      if (ev.type === "start" && ev.checking.length) {
        status.textContent = `Checking ${ev.checking.length} possible program${ev.checking.length > 1 ? "s" : ""}: ${ev.checking.join(", ")}`;
      } else if (ev.type === "checked") {
        status.textContent = `Checked ${ev.done} of ${ev.of}…`;
      } else if (ev.type === "program") {
        found.push(ev.program_name);
        reply.append(programCard(ev));
      } else if (ev.type === "done") {
        status.remove();
        reply.prepend(add("p", ev.answer));
        if (ev.missing_info.length) reply.append(add("h4", "Still needed to decide"), list(ev.missing_info));
        history.push({ role: "user", content: question },
          { role: "assistant", content: found.length ? `${ev.answer}\nPrograms: ${found.join(", ")}` : ev.answer });
        input.value = "";
      } else if (ev.type === "error") {
        throw new Error(ev.message);
      }
    }
  } catch (err) {
    status.remove();
    reply.append(add("p", err.message, "error"));
  } finally {
    button.disabled = false;
    button.textContent = "Ask";
  }
});
