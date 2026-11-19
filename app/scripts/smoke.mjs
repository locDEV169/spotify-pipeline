import assert from 'node:assert/strict'

const base = process.env.APP_URL ?? 'http://127.0.0.1:3000'
const health = await fetch(new URL('/api/health', base))
assert.equal(health.status, 200)
assert.deepEqual(await health.json(), { status: 'ok', service: 'spotify-app' })

const page = await fetch(base)
assert.equal(page.status, 200)
const html = await page.text()
assert.match(html, /Spotify Pipeline/)
assert.match(html, /Charts overview/)
assert.match(html, /SAMPLE DATA/)
assert.match(html, /Midnight City/)
assert.match(html, /rel="stylesheet"/)
console.log('PASS: API health, dashboard SSR, demo rows and stylesheet link.')
