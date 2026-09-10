import { readFile } from "node:fs/promises";
import type { IncomingMessage, ServerResponse } from "node:http";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Connect, type Plugin } from "vite";

// Dev and preview serve the fixtures at the wire's routes; the production
// build carries none of this. `?fixture=<state>` selects
// fixtures/states/<section>.<state>.json, or drives a transport state.
const FIXTURES = fileURLToPath(new URL("./fixtures/", import.meta.url));
const SECTIONS = new Set([
  "directory",
  "upload",
  "analysis",
  "book",
  "run",
  "model",
  "report",
  "committee",
  "admin",
]);

// The frame a run's stream has advanced to; the next fetch of /run reads it.
let runFrame = 0;

async function readJson(path: string): Promise<string | null> {
  try {
    return await readFile(`${FIXTURES}${path}`, "utf8");
  } catch {
    return null;
  }
}

function send(res: ServerResponse, status: number, body: string): void {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(body);
}

async function serveSection(section: string, fixture: string | null, res: ServerResponse) {
  if (fixture === "offline") {
    res.socket?.destroy();
    return;
  }
  if (fixture === "unavailable") return send(res, 404, "{}");
  if (fixture === "error") {
    return send(
      res,
      503,
      JSON.stringify({ code: "STORE_UNAVAILABLE", clears: "The store answers again." }),
    );
  }
  let path = `${section}.json`;
  if (fixture && fixture !== "stale") path = `states/${section}.${fixture}.json`;
  else if (section === "run" && runFrame > 0) path = `run/frames/${runFrame}.json`;
  const body = await readJson(path);
  if (body === null) return send(res, 404, "{}");
  send(res, 200, body);
}

async function serveEvents(fixture: string | null, req: IncomingMessage, res: ServerResponse) {
  const named = fixture === "stale" ? "stale" : "events";
  const raw = await readJson(`run/${named}.json`);
  let events: { id: number; type: string }[] = [];
  try {
    events = raw ? JSON.parse(raw) : [];
  } catch {
    events = [];
  }
  const after = Number(req.headers["last-event-id"] ?? 0);
  res.statusCode = 200;
  res.setHeader("content-type", "text/event-stream");
  res.setHeader("cache-control", "no-store");
  res.flushHeaders();
  runFrame = 0;
  let index = 0;
  const pending = events.filter((event) => event.id > after);
  const tick = () => {
    const event = pending[index];
    if (res.writableEnded) return;
    if (!event) {
      res.write("event: stream_end\ndata: {}\n\n");
      res.end();
      return;
    }
    if (named === "events") runFrame = event.id;
    res.write(`id: ${event.id}\nevent: ${event.type}\ndata: {}\n\n`);
    index += 1;
    setTimeout(tick, 250);
  };
  setTimeout(tick, 250);
  // The frame is reset when a stream opens, never when it closes: the refetch
  // that run_terminal triggers races the close, and must still see the last
  // frame. The client opens its tail before its first fetch for the same reason.
  // ponytail: one process-wide frame; per-stream frames if two runs ever tail at once.
  req.on("close", () => res.end());
}

const fixtureMiddleware: Connect.NextHandleFunction = (req, res, next) => {
  const url = new URL(req.url ?? "/", "http://localhost");
  const requested = url.searchParams.get("fixture");
  // A state name is one word: never a path.
  if (requested !== null && !/^[a-z-]+$/.test(requested)) {
    send(res, 404, "{}");
    return;
  }
  const fixture = requested;
  const section = /^\/api\/sections\/([a-z]+)$/.exec(url.pathname)?.[1];
  if (section && SECTIONS.has(section)) {
    void serveSection(section, fixture, res);
    return;
  }
  if (url.pathname === "/api/events") {
    void serveEvents(fixture, req, res);
    return;
  }
  const page = /^\/api\/pages\/([A-Za-z0-9-]+\.svg)$/.exec(url.pathname)?.[1];
  if (page) {
    void readJson(`pages/${page}`).then((body) => {
      if (body === null) return send(res, 404, "{}");
      res.statusCode = 200;
      res.setHeader("content-type", "image/svg+xml");
      res.end(body);
    });
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    send(res, 404, "{}");
    return;
  }
  next();
};

const fixtures: Plugin = {
  name: "caos-fixtures",
  configureServer(server) {
    server.middlewares.use(fixtureMiddleware);
  },
  configurePreviewServer(server) {
    server.middlewares.use(fixtureMiddleware);
  },
};

export default defineConfig({
  plugins: [react(), tailwindcss(), fixtures],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  publicDir: false,
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  build: { sourcemap: false, target: "es2022" },
});
