// 這里需要你：伺服器端帳號密碼驗證（HTTP Basic Auth）
// 帳號密碼放在 Cloudflare 的 Secret：DEMO_USER、DEMO_PASS（不寫在程式碼裡）
// 沒設定 Secret 時一律拒絕（fail closed）

const enc = new TextEncoder();

async function sameSecret(a, b) {
  // 先各自雜湊成固定長度，再做常數時間比較，避免從回應時間推測密碼
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b)),
  ]);
  return crypto.subtle.timingSafeEqual(ha, hb);
}

function decodeBasic(header) {
  if (!header || !header.startsWith("Basic ")) return null;
  try {
    const bin = atob(header.slice(6).trim());
    const text = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
    const i = text.indexOf(":");
    return i < 0 ? null : [text.slice(0, i), text.slice(i + 1)];
  } catch {
    return null;
  }
}

const text = (body, status, extra = {}) =>
  new Response(body, {
    status,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store", ...extra },
  });

export default {
  async fetch(request, env) {
    if (!env.DEMO_USER || !env.DEMO_PASS) {
      return text("網站尚未設定帳號密碼，暫不開放。", 503);
    }
    const cred = decodeBasic(request.headers.get("Authorization"));
    const ok =
      cred &&
      (await sameSecret(cred[0], env.DEMO_USER)) &
      (await sameSecret(cred[1], env.DEMO_PASS));
    if (!ok) {
      return text("請輸入帳號密碼。", 401, {
        "WWW-Authenticate": 'Basic realm="zheli-needs-you", charset="UTF-8"',
      });
    }
    const res = await env.ASSETS.fetch(request);
    const out = new Response(res.body, res);
    out.headers.set("cache-control", "no-store, private");
    out.headers.set("X-Robots-Tag", "noindex, nofollow");
    out.headers.set("X-Content-Type-Options", "nosniff");
    out.headers.set("Referrer-Policy", "no-referrer");
    out.headers.set("X-Frame-Options", "DENY");
    return out;
  },
};
