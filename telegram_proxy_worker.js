/**
 * Cloudflare Worker - Telegram API Proxy
 * 
 * Deploy this to Cloudflare Workers (free tier) to bypass
 * ISP-level blocking of api.telegram.org.
 * 
 * Steps:
 * 1. Go to https://workers.cloudflare.com and create a free account
 * 2. Create a new Worker
 * 3. Paste this code and deploy
 * 4. Copy your worker URL (e.g. https://tg-proxy.your-name.workers.dev)
 * 5. Set TELEGRAM_API_URL=https://tg-proxy.your-name.workers.dev in .env
 */

export default {
  async fetch(request) {
    const url = new URL(request.url);
    
    // Rewrite to api.telegram.org
    const telegramUrl = `https://api.telegram.org${url.pathname}${url.search}`;
    
    // Forward the request
    const response = await fetch(telegramUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== "GET" ? request.body : undefined,
    });

    // Return the response with CORS headers
    return new Response(response.body, {
      status: response.status,
      headers: {
        ...Object.fromEntries(response.headers),
        "Access-Control-Allow-Origin": "*",
      },
    });
  },
};
