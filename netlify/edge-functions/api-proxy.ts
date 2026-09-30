// Proxies every /api/* request to the external FreightWise Flask backend.
// Set BACKEND_API_URL (e.g. https://freightwise-api.onrender.com) in the Netlify site's environment variables.
declare const Netlify: { env: { get(name: string): string | undefined } }

const json = (body: unknown, status: number) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

export default async (req: Request) => {
  const backend = Netlify.env.get('BACKEND_API_URL')?.replace(/\/+$/, '')
  if (!backend) {
    return json({ success: false, error: 'FreightWise backend is not connected yet. Set BACKEND_API_URL in the Netlify environment variables.' }, 503)
  }

  const url = new URL(req.url)
  const target = backend + url.pathname + url.search
  const headers = new Headers(req.headers)
  headers.delete('host')

  try {
    const res = await fetch(target, {
      method: req.method,
      headers,
      body: req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.arrayBuffer(),
      redirect: 'manual',
    })
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers: res.headers })
  } catch {
    return json({ success: false, error: 'FreightWise backend is currently unavailable. Please try again shortly.' }, 502)
  }
}

export const config = {
  path: '/api/*',
}
