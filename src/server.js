import { createServer } from "node:http";

const PORT = Number(process.env.PORT ?? 3000);
const ideas = [];

function sendJson(res, status, body) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 1_000_000) {
        reject(new Error("payload too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!data) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(data));
      } catch {
        reject(new Error("invalid json"));
      }
    });
    req.on("error", reject);
  });
}

const server = createServer(async (req, res) => {
  const { method, url } = req;

  if (method === "GET" && url === "/api/health") {
    sendJson(res, 200, { status: "ok" });
    return;
  }

  if (method === "GET" && url === "/api/ideas") {
    sendJson(res, 200, { ideas });
    return;
  }

  if (method === "POST" && url === "/api/ideas") {
    try {
      const body = await readJson(req);
      const title = typeof body.title === "string" ? body.title.trim() : "";
      if (!title) {
        sendJson(res, 400, { error: "title is required" });
        return;
      }
      const idea = { id: ideas.length + 1, title };
      ideas.push(idea);
      sendJson(res, 201, idea);
    } catch {
      sendJson(res, 400, { error: "invalid request body" });
    }
    return;
  }

  sendJson(res, 404, { error: "not found" });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`new-idea API listening on http://0.0.0.0:${PORT}`);
});
