import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import type { Connect, Plugin } from 'vite'

interface ArtFields {
  title: string
  year: string
  place: string
  sentence: string
}

interface PackageShape {
  claims: Array<{ id: number; text: string; time_label: string; region_ids: number[]; event_id: number | null }>
  events: Array<{ id: number; title: string }>
  regions: Array<{ id: number; name: string }>
  people: Array<{ id: number; name: string; birth_year: number | null; death_year: number | null; description: string }>
}

function pngToWebp(png: string, webp: string): Promise<boolean> {
  const code = 'from PIL import Image\nimport sys\nImage.open(sys.argv[1]).save(sys.argv[2], "WEBP", quality=80)'
  return new Promise((resolve) => {
    const child = spawn('python', ['-c', code, png, webp], { windowsHide: true })
    child.on('error', () => resolve(false))
    child.on('exit', (code) => resolve(code === 0 && fs.existsSync(webp)))
  })
}

async function generate(file: string, prompt: string): Promise<boolean> {
  const key = process.env.LONGRIVER_IMAGE_KEY
  if (!key) return false
  const endpoint = process.env.LONGRIVER_IMAGE_URL || 'https://api.openai.com/v1/images/generations'
  const model = process.env.LONGRIVER_IMAGE_MODEL || 'dall-e-3'
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      prompt: prompt.slice(0, 900),
      size: '1024x1024',
      response_format: 'b64_json',
    }),
  })
  if (!response.ok) return false
  const body = await response.json() as { data?: Array<{ b64_json?: string }> }
  const encoded = body.data?.[0]?.b64_json
  if (!encoded) return false
  fs.mkdirSync(path.dirname(file), { recursive: true })
  const png = file.replace(/\.webp$/, '.png')
  fs.writeFileSync(png, Buffer.from(encoded, 'base64'))
  const converted = await pngToWebp(png, file)
  if (converted) fs.unlinkSync(png)
  return converted
}

export function detailArtPlugin(distDir: string): Plugin {
  const artDir = path.join(distDir, 'detail-art')
  const packPath = path.join(distDir, 'knowledge-package.json')
  let pack: PackageShape | null = null
  let packMtime = 0
  const pending = new Map<string, Promise<boolean>>()

  function loadPack(): PackageShape | null {
    if (!fs.existsSync(packPath)) return null
    const mtime = fs.statSync(packPath).mtimeMs
    if (!pack || mtime !== packMtime) {
      pack = JSON.parse(fs.readFileSync(packPath, 'utf8')) as PackageShape
      packMtime = mtime
    }
    return pack
  }

  function lookup(kind: string, id: number): ArtFields | null {
    const data = loadPack()
    if (!data) return null
    if (kind === 'claim') {
      const claim = data.claims.find((item) => item.id === id)
      if (!claim) return null
      const event = data.events.find((item) => item.id === claim.event_id)
      const region = data.regions.find((item) => item.id === claim.region_ids[0])
      return {
        title: event?.title || claim.text,
        year: claim.time_label,
        place: region?.name || '',
        sentence: claim.text,
      }
    }
    const person = data.people.find((item) => item.id === id)
    if (!person) return null
    const years = [person.birth_year, person.death_year].filter((value) => value != null).join('–')
    return {
      title: person.name,
      year: years,
      place: '',
      sentence: person.description || person.name,
    }
  }

  const handler: Connect.NextHandleFunction = (req, res, next) => {
    const match = req.url?.split('?')[0]?.match(/^\/detail-art\/(claim|person)\/(\d+)\.webp$/)
    if (!match) {
      next()
      return
    }
    const kind = match[1]
    const id = match[2]
    const file = path.join(artDir, kind, `${id}.webp`)
    const send = () => {
      if (!fs.existsSync(file)) {
        res.statusCode = 404
        res.end()
        return
      }
      res.setHeader('Content-Type', 'image/webp')
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
      fs.createReadStream(file).pipe(res)
    }
    if (fs.existsSync(file)) {
      send()
      return
    }
    const key = `${kind}:${id}`
    let job = pending.get(key)
    if (!job) {
      job = (async () => {
        const fields = lookup(kind, Number(id))
        if (!fields) return false
        const prompt = [
          'A quiet historical atlas illustration, no letters, no watermark.',
          fields.title,
          fields.year,
          fields.place,
          fields.sentence,
          'This picture is an illustration, not a historical source.',
        ].filter(Boolean).join('. ')
        return generate(file, prompt)
      })().finally(() => pending.delete(key))
      pending.set(key, job)
    }
    void job.then(send).catch(() => {
      res.statusCode = 404
      res.end()
    })
  }

  return {
    name: 'longriver-detail-art',
    configureServer(server) {
      server.middlewares.use(handler)
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler)
    },
  }
}
