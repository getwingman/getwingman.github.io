/**
 * Wingman Connect — the small secure server boundary Wingman needs for providers that can't be
 * reached safely from a static page.  Deploy as a Cloudflare Worker (module syntax).
 *
 *   Yahoo  : OAuth 2.0 authorization-code flow + API proxy. The client secret and refresh token never reach
 *            the browser; the page only holds an AES-GCM-encrypted session blob it cannot read.
 *   ESPN   : optional proxy for PRIVATE leagues. Your espn_s2 / SWID cookies live here as secrets,
 *            are only ever sent to ESPN's fantasy host, and never to the page.
 *
 * Required secrets / vars (wrangler secret put …):
 *   ALLOWED_ORIGIN       e.g. https://yourname.github.io          (the https origin serving wingman.html)
 *   SESSION_KEY          32+ random characters (encrypts the Yahoo session blob)
 *   YAHOO_CLIENT_ID      from https://developer.yahoo.com/apps/  (Fantasy Sports: Read)
 *   YAHOO_CLIENT_SECRET  from the same Yahoo app
 * Optional (private ESPN leagues):
 *   ESPN_S2, ESPN_SWID   your own ESPN cookies (treat them like a password)
 * Custom Import (screenshot reading):
 *   Binding  AI          Workers AI binding (Settings → Bindings → Add → Workers AI, variable name AI). No API key needed.
 *   Optional RATE_LIMITER  a Rate Limiting binding; otherwise a built-in per-IP limit is used
 *   Optional VISION_MODEL  override the model (default @cf/google/gemma-4-26b-a4b-it, fallback Llama 4 Scout)
 * Also proxies MyFantasyLeague (/mfl/…), Fleaflicker (/ff/…) and Sleeper Pick'em lines (/sleeper/scores/…) if CORS blocks the browser.
 *
 * Yahoo app redirect URI must be:  https://<your-worker-domain>/yahoo/callback
 */
const YAHOO_AUTH = "https://api.login.yahoo.com/oauth2/request_auth";
const YAHOO_TOKEN = "https://api.login.yahoo.com/oauth2/get_token";
const YAHOO_API = "https://fantasysports.yahooapis.com/fantasy/v2/";
const ESPN_HOST = "https://lm-api-reads.fantasy.espn.com";

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "X-WM-Session, X-WM-Pickem-Key, Content-Type",
      "Access-Control-Expose-Headers": "X-WM-Session",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Vary": "Origin",
    };
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    try {
      if (url.pathname === "/yahoo/login") return yahooLogin(url, env);
      if (url.pathname === "/yahoo/callback") return await yahooCallback(url, env);
      if (url.pathname.startsWith("/yahoo/api/")) return await yahooApi(req, url, env, cors);
      if (url.pathname.startsWith("/espn/apis/v3/games/ffl/")) return await espnProxy(url, env, cors);
      if (url.pathname === "/vision/roster" && req.method === "POST") return await visionRoster(req, env, cors);
      if (url.pathname === "/vision/ping") return await visionPing(req, env, cors);
      if (url.pathname === "/news/quip") return await newsQuip(req, url, env, cors);
      if (url.pathname === "/pickem/season" && req.method === "GET") return await pickemSeason(req, url, env, cors);
      if (url.pathname.startsWith("/mfl/")) return await passThrough("https://api.myfantasyleague.com" + url.pathname.slice(4) + url.search, cors);
      if (url.pathname.startsWith("/sleeper/scores/")) return await passThrough("https://api.sleeper.app" + url.pathname.slice(8) + url.search, cors);
      if (url.pathname.startsWith("/ff/api/")) return await passThrough("https://www.fleaflicker.com" + url.pathname.slice(3) + url.search, cors);
      return new Response("Not found", { status: 404, headers: cors });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e.message || e) }), { status: 500, headers: { ...cors, "Content-Type": "application/json" } });
    }
  },
};


/* -------- Authenticated, read-only Sleeper Pick'em pool reader --------
   Secrets (worker ONLY): SLEEPER_TOKEN (Sleeper session authorization header),
   WM_PICKEM_VIEW_KEY (separate random 24+ char viewer key), WM_PICKEM_POOL_ID.
   Picks are exposed only once a particular game's Sleeper score is complete.
   "outcome" is NOT a scoring result; Wingman uses ESPN final + verified pool lock instead.
   This endpoint never accepts writes or returns any secrets.
*/
async function pickemSeason(req, url, env, cors) {
  const H={...cors,"Content-Type":"application/json","Cache-Control":"private, no-store"};
  const J=(code,obj)=>new Response(JSON.stringify(obj),{status:code,headers:H});
  const origin=req.headers.get("Origin")||"";
  if(env.ALLOWED_ORIGIN&&origin&&origin!==env.ALLOWED_ORIGIN)return J(403,{ok:false,error:"Origin not authorized"});
  if(!env.SLEEPER_TOKEN||!env.WM_PICKEM_VIEW_KEY)return J(503,{ok:false,error:"Sleeper reader is not configured in Wingman Connect"});
  const a=new TextEncoder().encode(req.headers.get("X-WM-Pickem-Key")||""),
        b=new TextEncoder().encode(String(env.WM_PICKEM_VIEW_KEY));
  if(a.length!==b.length||a.length<16)return J(401,{ok:false,error:"Invalid viewer key"});
  let same=0;for(let i=0;i<a.length;i++)same|=a[i]^b[i];
  if(same)return J(401,{ok:false,error:"Invalid viewer key"});
  const from=Math.max(1,Math.min(18,Number.parseInt(url.searchParams.get("week")||"1")||1)),
        upto=Math.max(from,Math.min(18,Number.parseInt(url.searchParams.get("upto")||String(from))||from));
  const season=String(Number.parseInt(url.searchParams.get("season")||String(new Date().getUTCFullYear()))||"");
  if(!/^(20[2-9]\d)$/.test(season))return J(400,{ok:false,error:"Bad season"});
  const league=String(env.WM_PICKEM_POOL_ID||"1392587441361129472");
  if(!/^\d{12,24}$/.test(league))return J(503,{ok:false,error:"Pool ID not configured"});
  const UA="Wingman-Pickem/1.0 (+https://getwingman.github.io)";
  const get=async path=>{const r=await fetch("https://api.sleeper.app"+path,{headers:{"Accept":"application/json","User-Agent":UA}});
    if(!r.ok)throw Error("Sleeper REST HTTP "+r.status);return r.json()};
  const gql=async w=>{
    const leg="v1:regular:"+w;
    const query='query { get_pickem_picks_for_league(league_id: "'+league+'", leg_id: "'+leg+'", include_tiebreaker: true) }';
    const r=await fetch("https://sleeper.com/graphql",{method:"POST",headers:{
      "Authorization":String(env.SLEEPER_TOKEN),"Content-Type":"application/json","Accept":"application/json","User-Agent":UA
    },body:JSON.stringify({query})});
    if(!r.ok)throw Error("Sleeper authenticated picks HTTP "+r.status);
    const j=await r.json();if(j.errors&&j.errors.length)throw Error("Sleeper pick query: "+String(j.errors[0].message||"failed").slice(0,90));
    const d=j.data&&j.data.get_pickem_picks_for_league;
    if(!d||typeof d!=="object"||Array.isArray(d))throw Error("Sleeper returned no readable pool picks");
    return d;
  };
  try {
    const [rosters,users]=await Promise.all([get("/v1/league/"+league+"/rosters"),get("/v1/league/"+league+"/users")]);
    if(!Array.isArray(rosters)||!Array.isArray(users))throw Error("Sleeper pool roster mapping unavailable");
    const byId=new Map(users.map(u=>[String(u.user_id),u]));
    const entries=rosters.map(r=>{
      const u=byId.get(String(r.owner_id))||{},id=String(r.roster_id||"");
      return{id,name:String(u.display_name||u.username||id),username:String(u.username||"")};
    }).filter(e=>e.id);
    if(!entries.length)throw Error("Sleeper pool entries unavailable");
    const weeks=await Promise.all(Array.from({length:upto-from+1},(_,i)=>from+i).map(async w=>{
      const [picks,scores]=await Promise.all([gql(w),get("/scores/nfl/regular/"+season+"/"+w)]);
      if(!Array.isArray(scores))throw Error("Sleeper scoreboard unavailable for W"+w);
      const games=scores.map(g=>{
        const m=g.metadata||{},final=g.status==="complete";
        return{id:String(g.game_id||g.id||""),home:String(m.home_team||"").toUpperCase(),
          away:String(m.away_team||"").toUpperCase(),homeScore:final?Number(m.home_score):null,
          awayScore:final?Number(m.away_score):null,status:String(g.status||""),final,
          picks:final?Object.entries(picks).flatMap(([entryId,item])=>{
            const raw=item&&item.picks&&item.picks[g.game_id];const team=raw&&String(raw.team||"").toUpperCase();
            return team?[{entryId:String(entryId),team}]:[];
          }):[]};
      }).filter(g=>g.id&&g.home&&g.away);
      return{week:w,games};
    }));
    return J(200,{ok:true,pool:{id:league,entries},weeks,syncedAt:new Date().toISOString()});
  } catch(e){return J(502,{ok:false,error:String(e.message||e).slice(0,160)})}
}

/* ---------------- Yahoo OAuth ---------------- */
function yahooLogin(url, env) {
  const ret = url.searchParams.get("return") || "";
  if (!ret.startsWith(env.ALLOWED_ORIGIN)) return new Response("Return URL not allowed", { status: 400 });
  const state = btoa(JSON.stringify({ ret, n: crypto.randomUUID() }));
  /* ask explicitly for Fantasy Sports read access (fspt-r); without it Yahoo can issue a token that
     its Fantasy API rejects with "This application is not authorized to perform this action" */
  const q = new URLSearchParams({ client_id: env.YAHOO_CLIENT_ID, redirect_uri: `${url.origin}/yahoo/callback`, response_type: "code", scope: env.YAHOO_SCOPE || "fspt-r", state });
  return Response.redirect(`${YAHOO_AUTH}?${q}`, 302);
}
async function yahooCallback(url, env) {
  const code = url.searchParams.get("code");
  let ret = env.ALLOWED_ORIGIN;
  try { ret = JSON.parse(atob(url.searchParams.get("state") || "")).ret || ret; } catch (e) {}
  if (!ret.startsWith(env.ALLOWED_ORIGIN)) ret = env.ALLOWED_ORIGIN;
  if (!code) return Response.redirect(ret + "#wm_error=yahoo_denied", 302);
  let tok;
  try { tok = await yahooToken(env, { grant_type: "authorization_code", code, redirect_uri: `${url.origin}/yahoo/callback` }); }
  catch (e) { return Response.redirect(ret + "#wm_error=yahoo_token", 302); }   /* back to the app with a plain error, never a raw 500 page */
  const blob = await seal(env, { rt: tok.refresh_token, at: tok.access_token, exp: Date.now() + (tok.expires_in - 60) * 1000 });
  return Response.redirect(`${ret}#wm_yahoo=${encodeURIComponent(blob)}`, 302);
}
async function yahooToken(env, params) {
  const r = await fetch(YAHOO_TOKEN, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded", Authorization: "Basic " + btoa(`${env.YAHOO_CLIENT_ID}:${env.YAHOO_CLIENT_SECRET}`) },
    body: new URLSearchParams(params),
  });
  if (!r.ok) throw new Error("Yahoo token exchange failed: " + r.status);
  return r.json();
}
async function yahooApi(req, url, env, cors) {
  const blob = req.headers.get("X-WM-Session");
  if (!blob) return new Response("No session", { status: 401, headers: cors });
  let s;
  try { s = await open(env, blob); } catch (e) { return new Response("Bad session", { status: 401, headers: cors }); }
  let newBlob = null;
  if (!s.at || Date.now() > s.exp) {
    const t = await yahooToken(env, { grant_type: "refresh_token", refresh_token: s.rt });
    s = { rt: t.refresh_token || s.rt, at: t.access_token, exp: Date.now() + (t.expires_in - 60) * 1000 };
    newBlob = await seal(env, s);
  }
  const path = url.pathname.slice("/yahoo/api/".length);
  if (!/^[A-Za-z0-9_.;=,\/\-]+$/.test(path)) return new Response("Bad path", { status: 400, headers: cors });
  const r = await fetch(YAHOO_API + path + url.search, { headers: { Authorization: "Bearer " + s.at, Accept: "application/json", "User-Agent": "Wingman/1.0 (+https://getwingman.github.io)" } });
  if (!r.ok) {   /* pass Yahoo's own reason back so Wingman can show it */
    const body = (await r.text()).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300);
    return new Response(JSON.stringify({ error: `Yahoo ${r.status}`, detail: body, www: r.headers.get("www-authenticate") || "" }), { status: r.status, headers: { ...cors, "Content-Type": "application/json", ...(newBlob ? { "X-WM-Session": newBlob } : {}) } });
  }
  const h = { ...cors, "Content-Type": "application/json" };
  if (newBlob) h["X-WM-Session"] = newBlob;
  return new Response(await r.text(), { status: r.status, headers: h });
}

/* ---------------- ESPN private-league proxy ---------------- */
async function espnProxy(url, env, cors) {
  const target = ESPN_HOST + url.pathname.slice("/espn".length) + url.search;   // only ever ESPN's fantasy host
  const headers = { Accept: "application/json" };
  if (env.ESPN_S2 && env.ESPN_SWID) headers.Cookie = `espn_s2=${env.ESPN_S2}; SWID=${env.ESPN_SWID}`;
  const r = await fetch(target, { headers });
  return new Response(await r.text(), { status: r.status, headers: { ...cors, "Content-Type": "application/json" } });
}

/* ---------------- encrypted session blob (AES-GCM) ---------------- */
async function key(env) {
  const raw = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(env.SESSION_KEY));
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}
const b64 = (u8) => btoa(String.fromCharCode(...u8)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
async function seal(env, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await key(env), new TextEncoder().encode(JSON.stringify(obj))));
  return b64(iv) + "." + b64(ct);
}
async function open(env, blob) {
  const [iv, ct] = blob.split(".");
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(iv) }, await key(env), unb64(ct));
  return JSON.parse(new TextDecoder().decode(pt));
}

/* ---------------- public-API pass-through (fixed hosts only) ---------------- */
async function passThrough(target, cors) {
  const r = await fetch(target, { headers: { Accept: "application/json" }, redirect: "follow" });
  return new Response(await r.text(), { status: r.status, headers: { ...cors, "Content-Type": "application/json" } });
}

/* ---------------- screenshot → candidate roster (Workers AI vision; images are processed in memory, never stored) ----------------
   Needs one binding: Workers AI, variable name AI.  Optional: a Rate Limiting binding named RATE_LIMITER.
   Model: Gemma 4 (vision + JSON schema output); Llama 4 Scout as an automatic fallback. Override with VISION_MODEL. */
const VISION_MODELS = ["@cf/google/gemma-4-26b-a4b-it", "@cf/meta/llama-4-scout-17b-16e-instruct"];
const POS = ["QB", "RB", "WR", "TE", "K", "DEF", ""];
const SECTIONS = ["starter", "bench", "ir"];
const ROSTER_SCHEMA = {
  type: "object", additionalProperties: false,
  required: ["provider", "screen", "teams", "scoring"],
  properties: {
    provider: { type: "string" },
    screen: { type: "string", enum: ["roster", "matchup", "scoring", "other"] },
    teams: { type: "array", maxItems: 2, items: { type: "object", additionalProperties: false, required: ["name", "players"],
      properties: { name: { type: "string" }, owner: { type: "string" }, position_on_screen: { type: "string", enum: ["left", "right", "top", "bottom", "only"] },
        players: { type: "array", maxItems: 40, items: { type: "object", additionalProperties: false, required: ["name", "pos", "slot", "section"],
          properties: { name: { type: "string" }, pos: { type: "string", enum: POS }, nfl_team: { type: "string" }, slot: { type: "string" }, section: { type: "string", enum: SECTIONS }, legible: { type: "boolean" } } } } } } },
    scoring: { type: "object", additionalProperties: false, required: ["format", "evidence"],
      properties: { format: { type: "string", enum: ["ppr", "half", "standard", "custom", "unknown"] }, evidence: { type: "string" },
        rules: { type: "array", maxItems: 40, items: { type: "object", additionalProperties: false, required: ["label", "points"], properties: { label: { type: "string" }, points: { type: "number" } } } } } },
  },
};
const VISION_PROMPT = `You are reading screenshots from a fantasy football app (Sleeper, ESPN, Yahoo, CBS, Fantrax, NFL, MyFantasyLeague, Fleaflicker, Underdog or any other).
If several images are given they are consecutive parts of ONE long screenshot (top to bottom) — never list a player twice.
Return JSON matching the schema:
- provider: app name if clearly identifiable from logos/colors/layout, else "".
- screen: "roster" (one team's lineup), "matchup" (two teams side by side or stacked), "scoring" (league scoring settings), "other".
- teams: one entry per fantasy team shown. name = the fantasy team name exactly as shown (or ""), owner = manager name if shown. position_on_screen = where that team appears.
  players: EVERY player row that is visible, in on-screen order. name = the player's name exactly as written (keep initials like "J. Allen"); pos = QB/RB/WR/TE/K/DEF (team defenses, D/ST, DEF => "DEF", and name them like "Bills D/ST"); nfl_team = NFL team abbreviation if shown; slot = the lineup slot label exactly as shown (QB, RB, WR, TE, FLEX, W/R/T, SUPER FLEX, OP, K, DEF, D/ST, BN, IR …); section = starter for lineup slots, bench for bench, ir for injured reserve. legible=false if you had to guess any part of the name.
- scoring: format only if the screenshot itself shows it (e.g. "PPR", "Half PPR", "0.5 PPR", "Standard", or a scoring settings page). Put the exact supporting text in evidence. If nothing on screen states the scoring, use "unknown" and evidence "". Add rules only when a scoring settings screen lists them.
Never invent players, teams, slots or scoring. If no fantasy roster is visible, return teams: [].`;

async function visionRoster(req, env, cors) {
  const J = (status, obj) => new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json" } });
  if (!env.AI) return J(503, { error: "Screenshot reading isn't switched on yet.", code: "NO_AI_BINDING", fix: "In Cloudflare: Worker → Settings → Bindings → Add → Workers AI → name it AI → Deploy." });
  /* abuse protection: only the Wingman site may call this, bounded size, per-IP rate limit */
  const origin = req.headers.get("Origin") || "";
  if (env.ALLOWED_ORIGIN && origin !== env.ALLOWED_ORIGIN) return J(403, { error: "Not allowed from this site.", code: "ORIGIN" });
  const len = +(req.headers.get("Content-Length") || 0);
  if (len > 6_500_000) return J(413, { error: "Those screenshots are too large. Try fewer at once.", code: "TOO_LARGE" });
  const ip = req.headers.get("CF-Connecting-IP") || "anon";
  if (!(await allow(env, ip))) return J(429, { error: "Too many screenshots in a short time. Wait a minute and try again.", code: "RATE_LIMIT" });
  let body;
  try { body = await req.json(); } catch (e) { return J(400, { error: "That upload didn't arrive correctly. Try again.", code: "BAD_JSON" }); }
  const imgs = Array.isArray(body && body.images) ? body.images : body && body.data ? [{ mediaType: body.mediaType, data: body.data }] : [];
  if (!imgs.length || imgs.length > 4) return J(400, { error: "Send one screenshot at a time (up to 4 slices).", code: "COUNT" });
  for (const im of imgs) {
    if (!/^image\/(png|jpeg|webp)$/.test(im.mediaType || "")) return J(415, { error: "Use a PNG or JPG screenshot.", code: "TYPE" });
    if (typeof im.data !== "string" || im.data.length < 2000 || im.data.length > 2_800_000 || !/^[A-Za-z0-9+/=]+$/.test(im.data.slice(0, 2000))) return J(400, { error: "That image couldn't be read. Try a fresh screenshot.", code: "IMAGE" });
  }
  const models = env.VISION_MODEL ? [env.VISION_MODEL, ...VISION_MODELS] : VISION_MODELS;
  const content = [{ type: "text", text: imgs.length > 1 ? `These ${imgs.length} images are top-to-bottom slices of one screenshot.` : "One screenshot." }, ...imgs.map((im) => ({ type: "image_url", image_url: { url: `data:${im.mediaType};base64,${im.data}` } }))];
  let lastErr = "";
  const t0 = Date.now();
  for (const model of models) {
    const left = 80000 - (Date.now() - t0);
    if (left < 8000) break;
    try {
      const r = await withTimeout(env.AI.run(model, {
        messages: [{ role: "system", content: VISION_PROMPT }, { role: "user", content }],
        response_format: { type: "json_schema", json_schema: { name: "fantasy_roster", schema: ROSTER_SCHEMA, strict: true } },
        max_tokens: 1800, temperature: 0,
      }), Math.min(45000, left), model);
      console.log(JSON.stringify({ vision: model, ms: Date.now() - t0, images: imgs.length }));
      const out = clean(extract(r));
      if (!out) { lastErr = "unreadable model output"; continue; }
      if (!out.teams.length || !out.teams.some((t) => t.players.length)) {
        if (out.screen === "scoring" && out.scoring.format !== "unknown") return J(200, { ...out, model });
        return J(422, { error: "No fantasy roster found in that screenshot.", code: "NO_ROSTER", hint: "Open your lineup or matchup page, make the player names visible, and take the screenshot again." });
      }
      return J(200, { ...out, model });
    } catch (e) { lastErr = String(e && e.message || e).slice(0, 160); console.log(JSON.stringify({ vision: model, error: lastErr, ms: Date.now() - t0 })); }
  }
  return J(502, { error: /timed out/.test(lastErr) ? "The screenshot reader took too long. Try a screenshot of just the lineup." : "The screenshot reader is busy right now. Try again in a minute.", code: "MODEL", detail: lastErr });
}
/* model output → plain object (handles chat-completions shape, plain response, or already-parsed JSON) */
function extract(r) {
  let t = r && r.choices && r.choices[0] && r.choices[0].message ? r.choices[0].message.content : r && r.response != null ? r.response : r;
  if (t && typeof t === "object") return t;
  t = String(t || "").replace(/<think>[\s\S]*?<\/think>/g, "").replace(/```json|```/g, "").trim();
  const a = t.indexOf("{"), b = t.lastIndexOf("}");
  if (a < 0 || b < a) return null;
  try { return JSON.parse(t.slice(a, b + 1)); } catch (e) { return null; }
}
/* strict schema validation + sanitising: anything malformed is dropped, nothing is filled in */
function clean(o) {
  if (!o || typeof o !== "object") return null;
  const str = (v, n = 48) => String(v == null ? "" : v).replace(/[<>]/g, "").trim().slice(0, n);
  const teams = (Array.isArray(o.teams) ? o.teams : []).slice(0, 2).map((t) => ({
    name: str(t && t.name), owner: str(t && t.owner), position_on_screen: str(t && t.position_on_screen, 8),
    players: (Array.isArray(t && t.players) ? t.players : []).slice(0, 40).map((p) => ({
      name: str(p && p.name, 40), pos: POS.includes(String(p && p.pos).toUpperCase()) ? String(p.pos).toUpperCase() : "",
      nfl_team: str(p && p.nfl_team, 4).toUpperCase(), slot: str(p && p.slot, 14).toUpperCase(),
      section: SECTIONS.includes(p && p.section) ? p.section : "starter", legible: p && p.legible !== false,
    })).filter((p) => p.name.length >= 2 && /[a-z]/i.test(p.name)),
  }));
  const sc = o.scoring && typeof o.scoring === "object" ? o.scoring : {};
  const fmt = ["ppr", "half", "standard", "custom", "unknown"].includes(sc.format) ? sc.format : "unknown";
  const evidence = str(sc.evidence, 120);
  return {
    provider: str(o.provider, 30), screen: ["roster", "matchup", "scoring", "other"].includes(o.screen) ? o.screen : "other", teams,
    scoring: { format: evidence || fmt === "custom" ? fmt : "unknown", evidence, rules: (Array.isArray(sc.rules) ? sc.rules : []).slice(0, 40).map((r) => ({ label: str(r && r.label, 40), points: Number(r && r.points) })).filter((r) => r.label && isFinite(r.points)) },
  };
}
/* rate limit: Cloudflare Rate Limiting binding if configured, otherwise a per-location cache counter (8 reads / 10 min / IP) */
async function allow(env, ip, max = 8) {
  try { if (env.RATE_LIMITER) { const { success } = await env.RATE_LIMITER.limit({ key: (max > 8 ? "news:" : "vision:") + ip }); return success; } } catch (e) {}
  try {
    const bucket = Math.floor(Date.now() / 600000), key = new Request(`https://rl.wingman/${encodeURIComponent(ip)}/${bucket}`);
    const hit = await caches.default.match(key), n = hit ? +(await hit.text()) || 0 : 0;
    if (n >= max) return false;
    await caches.default.put(key, new Response(String(n + 1), { headers: { "Cache-Control": "max-age=660" } }));
  } catch (e) {}
  return true;
}

function withTimeout(p, ms, label) {
  return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`${label} timed out after ${Math.round(ms / 1000)}s`)), ms))]);
}
/* GET /vision/ping — quick health check you can open in a browser: is the AI binding there, and does each model answer? */
async function visionPing(req, env, cors) {
  const J = (status, obj) => new Response(JSON.stringify(obj, null, 1), { status, headers: { ...cors, "Content-Type": "application/json" } });
  if (!env.AI) return J(503, { ok: false, error: "No Workers AI binding named AI on this worker." });
  const ip = req.headers.get("CF-Connecting-IP") || "anon";
  if (!(await allow(env, "ping:" + ip))) return J(429, { ok: false, error: "Too many checks; wait a minute." });
  const out = [];
  for (const model of (env.VISION_MODEL ? [env.VISION_MODEL, ...VISION_MODELS] : VISION_MODELS)) {
    const t = Date.now();
    try {
      const r = await withTimeout(env.AI.run(model, { messages: [{ role: "user", content: "Reply with the single word: ready" }], max_tokens: 20 }), 30000, model);
      const txt = r && r.choices && r.choices[0] && r.choices[0].message ? r.choices[0].message.content : r && r.response;
      out.push({ model, ok: true, ms: Date.now() - t, reply: String(txt || "").slice(0, 40) });
    } catch (e) { out.push({ model, ok: false, ms: Date.now() - t, error: String(e && e.message || e).slice(0, 200) }); }
  }
  return J(200, { ok: out.some((x) => x.ok), models: out });
}

/* ---------------- player news with Wingman's voice ----------------
   GET /news/quip?espn=<ESPN athlete id>&name=&pos=&team=&since=<ms>
   Real ESPN fantasy news only. If nothing was published since the player's last game, no headline is invented. */
const NEWS_PROMPT = (n) => `You are Wingman: a sharp, funny fantasy football friend who talks a little trash.
Write ONE sentence (max 26 words) about ${n.name} (${n.pos}${n.team ? ", " + n.team : ""}) based ONLY on the news items below.
Rules:
- Use only facts stated in the items. Never invent stats, injuries, quotes, depth-chart moves or opponents.
- Focus on what matters for fantasy right now (role, injury, usage, performance).
- Good news: hype him up with swagger or a confident, clever line.
- Bad news (injury, benching, lost role, dud game): light roast, sarcasm or blunt honesty about his fantasy value. Joke about fantasy impact, never about someone being hurt.
- No hashtags, emojis, quotation marks or "Wingman says".
Return JSON {"tone":"good"|"bad"|"neutral","quip":"..."}.`;
async function newsQuip(req, url, env, cors) {
  const J = (status, obj, extra = {}) => new Response(JSON.stringify(obj), { status, headers: { ...cors, "Content-Type": "application/json", ...extra } });
  const origin = req.headers.get("Origin") || "";
  if (env.ALLOWED_ORIGIN && origin && origin !== env.ALLOWED_ORIGIN) return J(403, { error: "Not allowed from this site." });
  const espn = url.searchParams.get("espn") || "";
  if (!/^\d{2,10}$/.test(espn)) return J(400, { error: "Unknown player." });
  const n = { name: (url.searchParams.get("name") || "").replace(/[^A-Za-z .'\-]/g, "").slice(0, 40), pos: (url.searchParams.get("pos") || "").replace(/[^A-Z]/g, "").slice(0, 3), team: (url.searchParams.get("team") || "").replace(/[^A-Z]/g, "").slice(0, 3) };
  const since = Math.max(0, +url.searchParams.get("since") || 0);
  const ip = req.headers.get("CF-Connecting-IP") || "anon";
  if (!(await allow(env, "news:" + ip, 60))) return J(429, { error: "Easy on the hover. Try again in a minute." });
  let feed;
  try {
    const r = await fetch(`https://site.api.espn.com/apis/fantasy/v2/games/ffl/news/players?limit=8&playerId=${espn}`, { headers: { Accept: "application/json" }, cf: { cacheTtl: 900 } });
    if (!r.ok) return J(502, { error: "The news feed is unavailable right now." });
    const j = await r.json();
    const strip = (t) => String(t || "").replace(/<[^>]+>/g, " ").replace(/&[a-z#0-9]+;/gi, " ").replace(/\s+/g, " ").trim();
    feed = (Array.isArray(j && j.feed) ? j.feed : []).map((f) => ({ id: String(f.id || f.headline || "").slice(0, 60), headline: strip(f.headline).slice(0, 200), body: strip(f.story || f.description).slice(0, 700), published: Date.parse(f.published || f.lastModified || "") || 0 }))
      .filter((f) => f.headline || f.body).sort((a, b) => b.published - a.published);
  } catch (e) { return J(502, { error: "The news feed is unavailable right now." }); }
  const fresh = feed.filter((f) => f.published > since).slice(0, 3);
  if (!fresh.length) return J(200, { tone: "neutral", quip: null, latest: feed[0] ? { headline: feed[0].headline, published: feed[0].published } : null });
  const ck = new Request(`https://quip.wingman/${espn}/${encodeURIComponent(fresh[0].id + ":" + fresh[0].published)}`);
  try { const hit = await caches.default.match(ck); if (hit) return J(200, await hit.json(), { "X-Cache": "hit" }); } catch (e) {}
  const plain = { tone: "neutral", quip: fresh[0].headline || fresh[0].body.slice(0, 160), published: fresh[0].published, source: "ESPN", plain: true };
  if (!env.AI) return J(200, plain);
  const items = fresh.map((f, i) => `${i + 1}. [${new Date(f.published).toISOString().slice(0, 10)}] ${f.headline}. ${f.body}`).join("\n");
  let res = null;
  for (const model of VISION_MODELS) {
    try {
      const r = await withTimeout(env.AI.run(model, {
        messages: [{ role: "system", content: NEWS_PROMPT(n) }, { role: "user", content: "News items:\n" + items }],
        response_format: { type: "json_schema", json_schema: { name: "quip", strict: true, schema: { type: "object", additionalProperties: false, required: ["tone", "quip"], properties: { tone: { type: "string", enum: ["good", "bad", "neutral"] }, quip: { type: "string" } } } } },
        max_tokens: 160, temperature: 0.7,
      }), 20000, model);
      const o = extract(r);
      const q = o && typeof o.quip === "string" ? o.quip.replace(/[#"“”]/g, "").replace(/\s+/g, " ").trim() : "";
      if (q.length >= 12 && q.length <= 240) { res = { tone: ["good", "bad", "neutral"].includes(o.tone) ? o.tone : "neutral", quip: q, published: fresh[0].published, source: "ESPN" }; break; }
    } catch (e) {}
  }
  res = res || plain;
  try { await caches.default.put(ck, new Response(JSON.stringify(res), { headers: { "Cache-Control": "max-age=21600", "Content-Type": "application/json" } })); } catch (e) {}
  return J(200, res);
}
