// Runs the real assistant engine (app/assets/chat.js) under node and prints its answers as JSON.
// usage: node tests/chat_engine_run.js dash|pub '["question", ...]' ['{"page":"overview","p":{}}']
const fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "..", "app");
const mode = process.argv[2], queries = JSON.parse(process.argv[3]), ctx = process.argv[4] ? JSON.parse(process.argv[4]) : null;
const load = (rel, name) => { const t = fs.readFileSync(path.join(root, rel), "utf8"); globalThis[name] = JSON.parse(t.slice(t.indexOf("{"), t.lastIndexOf("}") + 1)); };
if (mode === "dash") load("dashboard/data/dash_data.js", "DASH"); else { load("data/site_data.js", "SITE_DATA"); load("data/map_data.js", "MAP_DATA"); }
const chat = require(path.join(root, "assets", "chat.js"));
const fn = process.env.CHAT_FACTS ? (q) => chat.facts(q, ctx) : (q) => chat.answer(q, ctx);
console.log(JSON.stringify(queries.map(fn)));
