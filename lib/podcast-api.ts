"use client"

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export type GenerateBody = {
  topic: string
  description: string
  tone: "funny" | "factual" | "serious" | "humorous" | "neutral"
  length: 5 | 10 | 15
}

export type ProgressResponse = {
  stage: number
  message: string
  percent: number
  log: string[]
}

export type ResultResponse = {
  status: "ready" | "error" | "running"
  title?: string
  mp3Url?: string
  notesUrl?: string
  durationSeconds?: number
  metrics?: {
    lufs?: number
    sourcesKept?: number
    ttsSeconds?: number
    runtimeSeconds?: number
  }
  error?: string
}

type ApiClient = {
  generate: (body: GenerateBody) => Promise<{ jobId: string }>
  getProgress: (jobId: string) => Promise<ProgressResponse>
  getResult: (jobId: string) => Promise<ResultResponse>
  cancel: (jobId: string) => Promise<{ ok: true }>
}

export function createPodcastApi(opts?: { mock?: boolean }): ApiClient {
  if (opts?.mock) return createMockApi()
  return createHttpApi()
}

// HTTP client with timeout and friendly errors
function createHttpApi(): ApiClient {
  const fetchWithTimeout = async (url: string, init?: RequestInit, timeoutMs = 15000) => {
    const ctrl = new AbortController()
    const id = setTimeout(() => ctrl.abort(), timeoutMs)
    try {
      const res = await fetch(url, { ...init, signal: ctrl.signal })
      if (!res.ok) {
        // 202 is OK for POST /generate per contract
        throw new Error(`Request failed (${res.status})`)
      }
      return res
    } catch (err: any) {
      if (err?.name === "AbortError") throw new Error("Request timed out")
      throw err
    } finally {
      clearTimeout(id)
    }
  }

  return {
    async generate(body) {
      const res = await fetchWithTimeout(`${BASE_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = (await res.json()) as { jobId: string }
      if (!data?.jobId) throw new Error("Invalid response from server")
      return data
    },
    async getProgress(jobId) {
      const res = await fetchWithTimeout(`${BASE_URL}/api/progress/${encodeURIComponent(jobId)}`)
      return (await res.json()) as ProgressResponse
    },
    async getResult(jobId) {
      const res = await fetchWithTimeout(`${BASE_URL}/api/result/${encodeURIComponent(jobId)}`)
      return (await res.json()) as ResultResponse
    },
    async cancel(jobId) {
      const res = await fetchWithTimeout(`${BASE_URL}/api/cancel/${encodeURIComponent(jobId)}`, {
        method: "POST",
      })
      return (await res.json()) as { ok: true }
    },
  }
}

// In-memory mock that simulates progress and a final result
function createMockApi(): ApiClient {
  type MockJob = {
    id: string
    createdAt: number
    canceled: boolean
    stage: number
    percent: number
    log: string[]
    title?: string
    done?: boolean
    error?: string
  }

  const jobs = new Map<string, MockJob>()

  const STAGES = [
    "Sharpening pencils…",
    "Picking the best news from the web",
    "Skimming so you don’t have to",
    "Checking what the hotshots have to say about this",
    "Connecting the dots",
    "Adding dramatic pauses (tastefully)",
    "Finding the right voice",
    "Laying down a smooth bed",
    "Dialing in the vibes to −16 LUFS",
    "Pressing the big red Export button",
    "All set. Ready when you are.",
  ]

  const interval = 1000

  // simple ticker
  const ensureTicker = () => {
    if ((ensureTicker as any)._timer) return
    ;(ensureTicker as any)._timer = setInterval(() => {
      const now = Date.now()
      for (const job of jobs.values()) {
        if (job.canceled || job.done || job.error) continue
        // advance stage and percent
        const inc = 8 + Math.floor(Math.random() * 12)
        job.percent = Math.min(98, job.percent + inc)
        if (Math.random() < 0.6) {
          job.log.push(randomLog())
          job.log = job.log.slice(-120)
        }
        if (job.percent >= (job.stage + 1) * (100 / STAGES.length)) {
          job.stage = Math.min(STAGES.length - 1, job.stage + 1)
        }
        // finish after ~12-18s
        if (now - job.createdAt > 12000 && Math.random() < 0.4) {
          job.percent = 100
          job.stage = STAGES.length - 1
          job.done = true
          job.title = job.title || "Daily Briefing — " + new Date().toLocaleDateString()
        }
      }
    }, interval)
  }

  function randomLog() {
    const msgs = [
      "Gathering headlines",
      "Summarizing key points",
      "Pulling expert quotes",
      "Removing filler words",
      "Mixing in ambience",
      "Balancing EQ",
      "Converting text to speech",
      "Exporting MP3",
    ]
    return msgs[Math.floor(Math.random() * msgs.length)]
  }

  return {
    async generate(body) {
      const id = Math.random().toString(36).slice(2, 10)
      const job: MockJob = {
        id,
        createdAt: Date.now(),
        stage: 0,
        percent: 3,
        log: ["Job accepted", `Topic: ${body.topic}`, `Tone: ${body.tone}, Length: ${body.length}m`],
        canceled: false,
        done: false,
        title: `“${body.topic}”`,
      }
      jobs.set(id, job)
      ensureTicker()
      await delay(300) // feel responsive
      return { jobId: id }
    },
    async getProgress(jobId) {
      await delay(150)
      const job = jobs.get(jobId)
      if (!job) throw new Error("Job not found")
      if (job.canceled) {
        return {
          stage: job.stage,
          message: "Canceled",
          percent: job.percent,
          log: job.log,
        }
      }
      return {
        stage: job.stage,
        message: STAGES[job.stage] || "Working…",
        percent: job.percent,
        log: job.log,
      }
    },
    async getResult(jobId) {
      await delay(200)
      const job = jobs.get(jobId)
      if (!job) throw new Error("Job not found")
      if (job.canceled) {
        return { status: "error", error: "Job canceled" }
      }
      if (job.error) {
        return { status: "error", error: job.error }
      }
      if (!job.done) {
        return { status: "running" }
      }
      return {
        status: "ready",
        title: job.title,
        mp3Url: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        notesUrl: "https://example.com",
        durationSeconds: 60 * 10,
        metrics: {
          lufs: -16,
          sourcesKept: 7,
          ttsSeconds: 42,
          runtimeSeconds: Math.floor((Date.now() - job.createdAt) / 1000),
        },
      }
    },
    async cancel(jobId) {
      await delay(200)
      const job = jobs.get(jobId)
      if (job) {
        job.canceled = true
      }
      return { ok: true }
    },
  }
}

function delay(ms: number) {
  return new Promise((res) => setTimeout(res, ms))
}
