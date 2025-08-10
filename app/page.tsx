"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"
import { Check, Clipboard, Download, FileText, Loader2, RefreshCcw, RotateCcw } from "lucide-react"
import { SegmentedControl } from "@/components/segmented-control"
import { type GenerateBody, type ProgressResponse, type ResultResponse, createPodcastApi } from "@/lib/podcast-api"
import { formatSeconds } from "@/lib/format"

// App Router with a Client Component for interactive form and polling. This follows Next.js App Router conventions for routing and client-side interactivity. [^1]

type RunState = "idle" | "running" | "success" | "error"

const TONES = ["funny", "factual", "serious", "humorous", "neutral"] as const
type Tone = (typeof TONES)[number]

const LENGTHS = [5, 10, 15] as const
type Length = (typeof LENGTHS)[number]

const STAGES: string[] = [
  "Sharpening pencils…",
  "Picking the best news from the web",
  "Skimming so you don’t have to",
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

export default function Page() {
  const { toast } = useToast()

  // Config toggles
  const [mockMode, setMockMode] = useState<boolean>(true)
  const [notesOpen, setNotesOpen] = useState<boolean>(false)

  // Form
  const [topic, setTopic] = useState<string>("")
  const [description, setDescription] = useState<string>("")
  const [tone, setTone] = useState<Tone>("neutral")
  const [length, setLength] = useState<Length>(10)

  // Run State
  const [state, setState] = useState<RunState>("idle")
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [result, setResult] = useState<ResultResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Dialogs
  const [confirmCancelOpen, setConfirmCancelOpen] = useState<boolean>(false)

  // polling
  const pollTimer = useRef<number | null>(null)
  const api = useMemo(() => createPodcastApi({ mock: mockMode }), [mockMode])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollTimer.current) window.clearInterval(pollTimer.current)
    }
  }, [])

  const resetAll = useCallback(() => {
    if (pollTimer.current) {
      window.clearInterval(pollTimer.current)
      pollTimer.current = null
    }
    setJobId(null)
    setProgress(null)
    setResult(null)
    setErrorMessage(null)
    setState("idle")
  }, [])

  const startPolling = useCallback(
    (newJobId: string) => {
      if (pollTimer.current) window.clearInterval(pollTimer.current)
      pollTimer.current = window.setInterval(async () => {
        try {
          // poll progress (optional UI)
          api
            .getProgress(newJobId)
            .then((p) => setProgress(p))
            .catch(() => {
              // ignore progress fetch errors; result polling will decide
            })

          // poll result
          const res = await api.getResult(newJobId)
          if (res.status === "ready") {
            setResult(res)
            setState("success")
            if (pollTimer.current) {
              window.clearInterval(pollTimer.current)
              pollTimer.current = null
            }
          } else if (res.status === "error") {
            setErrorMessage(res.error || "Something went wrong while generating the podcast.")
            setState("error")
            if (pollTimer.current) {
              window.clearInterval(pollTimer.current)
              pollTimer.current = null
            }
          } else {
            // running, continue polling
          }
        } catch (err: any) {
          // network failure: toast and keep trying a bit
          toast({
            title: "Network issue",
            description: "We’ll keep trying in the background. Check your connection.",
            variant: "destructive",
          })
        }
      }, 1000)
    },
    [api, toast],
  )

  const onGenerate = useCallback(async () => {
    // Add topic validation
    if (!topic.trim()) {
      toast({
        title: "Topic required",
        description: "Please enter a topic before generating your podcast.",
        variant: "destructive",
      })
      return
    }

    setState("running")
    setErrorMessage(null)
    setResult(null)
    setProgress(null)

    const body: GenerateBody = {
      topic: topic.trim(),
      description: description.trim(),
      tone,
      length,
    }

    try {
      const { jobId } = await api.generate(body)
      setJobId(jobId)
      startPolling(jobId)
    } catch (err: any) {
      setState("error")
      setErrorMessage(err?.message || "Failed to start the generation.")
      toast({
        title: "Failed to start",
        description: "Please try again.",
        variant: "destructive",
      })
    }
  }, [api, description, length, startPolling, tone, topic, toast])

  const onCancel = useCallback(async () => {
    if (!jobId) return
    try {
      await api.cancel(jobId)
    } catch {
      // Even if cancel fails, we return to the form state
      toast({
        title: "Cancel may not have reached the server",
        description: "We’ll return to the form so you can try again.",
      })
    } finally {
      resetAll()
      setConfirmCancelOpen(false)
    }
  }, [api, jobId, resetAll, toast])

  const copyToClipboard = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text)
        toast({ title: "Copied to clipboard" })
      } catch {
        toast({ title: "Copy failed", variant: "destructive" })
      }
    },
    [toast],
  )

  const canGenerate = topic.trim().length > 0 && state !== "running"

  return (
    <main className="min-h-[100dvh] w-full flex items-center justify-center bg-white">
      <div className="w-full max-w-2xl px-4 py-8">
        <Card className="rounded-2xl shadow-sm">
          <CardHeader className="gap-2">
            <CardTitle className="text-2xl sm:text-3xl">AI Podcast Generator</CardTitle>
            <CardDescription className="text-base">
              We’ll generate a single MP3 you can play and download.
            </CardDescription>

            <div className="mt-2 flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2">
                <Switch
                  id="mock-mode"
                  checked={mockMode}
                  onCheckedChange={(v) => setMockMode(Boolean(v))}
                  aria-label="Toggle mock backend mode"
                />
                <Label htmlFor="mock-mode" className="cursor-pointer">
                  Mock backend mode
                </Label>
              </div>
            </div>
          </CardHeader>

          <Separator />

          <CardContent className="py-6">
            {state === "idle" && (
              <FormView
                topic={topic}
                setTopic={setTopic}
                description={description}
                setDescription={setDescription}
                tone={tone}
                setTone={setTone}
                length={length}
                setLength={setLength}
                canGenerate={canGenerate}
                onGenerate={onGenerate}
              />
            )}

            {state === "running" && <ProgressView progress={progress} onCancel={() => setConfirmCancelOpen(true)} />}

            {state === "success" && result && (
              <ResultView
                result={result}
                notesOpen={notesOpen}
                setNotesOpen={setNotesOpen}
                onCopy={copyToClipboard}
                onReset={resetAll}
              />
            )}

            {state === "error" && <ErrorView message={errorMessage || "Something went wrong."} onReset={resetAll} />}
          </CardContent>

          <CardFooter className="justify-end">
            {state !== "idle" && (
              <Button
                variant="ghost"
                className="gap-2"
                onClick={() => {
                  resetAll()
                }}
              >
                <RotateCcw className="size-4" />
                Generate another
              </Button>
            )}
          </CardFooter>
        </Card>
      </div>

      <AlertDialog open={confirmCancelOpen} onOpenChange={setConfirmCancelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel generation?</AlertDialogTitle>
            <AlertDialogDescription>
              The current job will be canceled. You can always start again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel autoFocus>Keep running</AlertDialogCancel>
            <AlertDialogAction onClick={onCancel}>Cancel job</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Notes dialog lives here for proper stacking */}
      {/* Controlled from ResultView */}
    </main>
  )
}

function FormView(props: {
  topic: string
  setTopic: (v: string) => void
  description: string
  setDescription: (v: string) => void
  tone: Tone
  setTone: (v: Tone) => void
  length: Length
  setLength: (v: Length) => void
  canGenerate: boolean
  onGenerate: () => void
}) {
  const { topic, setTopic, description, setDescription, tone, setTone, length, setLength, canGenerate, onGenerate } =
    props

  return (
    <form
      className="grid gap-6"
      onSubmit={(e) => {
        e.preventDefault()
        if (canGenerate) onGenerate()
      }}
      aria-label="Podcast generation form"
    >
      <div className="grid gap-2">
        <Label htmlFor="topic">Topic</Label>
        <Input
          id="topic"
          placeholder="e.g., The latest in AI safety"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          required
          aria-required="true"
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="description">Brief description (optional)</Label>
        <Textarea
          id="description"
          placeholder="Add context or key points to cover..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />
      </div>

      <div className="grid gap-2">
        <Label>Tone</Label>
        <SegmentedControl
          ariaLabel="Select tone"
          options={TONES.map((t) => ({ label: capitalize(t), value: t }))}
          value={tone}
          onChange={(v) => setTone(v as Tone)}
        />
      </div>

      <div className="grid gap-2">
        <Label>Length (minutes)</Label>
        <SegmentedControl
          ariaLabel="Select length in minutes"
          options={LENGTHS.map((l) => ({ label: String(l), value: String(l) }))}
          value={String(length)}
          onChange={(v) => setLength(Number(v) as Length)}
        />
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-muted-foreground">This might take a few minutes depending on the topic.</div>
        <Button type="submit" disabled={!canGenerate} aria-disabled={!canGenerate} className="min-w-32">
          Generate
        </Button>
      </div>
    </form>
  )
}

function ProgressView(props: {
  progress: ProgressResponse | null
  onCancel: () => void
}) {
  const { progress, onCancel } = props
  const percent = Math.max(0, Math.min(100, progress?.percent ?? 5))
  const stageIndex = Math.max(0, Math.min(STAGES.length - 1, progress?.stage ?? 0))
  const stageTitle = STAGES[stageIndex]
  const message = progress?.message || "Cooking up something good…"

  return (
    <section aria-live="polite" className="grid gap-6">
      <div className="flex items-center gap-3">
        <Loader2
          className={cn("size-5 animate-spin text-muted-foreground", "motion-reduce:animate-none")}
          aria-hidden="true"
        />
        <div>
          <div className="text-lg font-medium">{stageTitle}</div>
          <div className="text-sm text-muted-foreground">{message}</div>
        </div>
      </div>

      <div className="grid gap-2">
        <Progress value={percent} aria-label="Progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} />
        <div className="text-xs text-muted-foreground">{percent}%</div>
      </div>

      <div className="grid gap-2">
        <Label className="text-sm">Activity log</Label>
        <div
          className="rounded-lg border bg-muted/30 p-3 h-40 overflow-auto text-sm"
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {(progress?.log ?? []).length === 0 ? (
            <div className="text-muted-foreground">Warming up the mics…</div>
          ) : (
            <ul className="space-y-1">
              {(progress?.log ?? []).map((line, idx) => (
                <li key={idx} className="text-muted-foreground">
                  {line}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </section>
  )
}

function ResultView(props: {
  result: ResultResponse
  notesOpen: boolean
  setNotesOpen: (v: boolean) => void
  onCopy: (t: string) => void
  onReset: () => void
}) {
  const { result, notesOpen, setNotesOpen, onCopy, onReset } = props
  const { title, mp3Url, notesUrl, metrics } = result

  return (
    <section className="grid gap-6">
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          <Check className="size-5 text-green-600" aria-hidden="true" />
        </div>
        <div className="grid gap-1">
          <div className="text-xl font-semibold">Podcast ready</div>
          {title && <div className="text-muted-foreground">{title}</div>}
        </div>
      </div>

      <div className="grid gap-3">
        {mp3Url ? (
          <audio controls className="w-full" src={mp3Url}>
            Your browser does not support the audio element.
          </audio>
        ) : (
          <div className="text-sm text-muted-foreground">MP3 URL missing from result.</div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {mp3Url && (
            <a
              href={mp3Url}
              download
              className={cn(
                "inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium",
                "hover:bg-muted/50",
              )}
            >
              <Download className="size-4" />
              Download MP3
            </a>
          )}
          {notesUrl && (
            <>
              <Button variant="outline" size="sm" className="gap-2 bg-transparent" onClick={() => setNotesOpen(true)}>
                <FileText className="size-4" />
                View notes
              </Button>
              <Dialog open={notesOpen} onOpenChange={setNotesOpen}>
                <DialogContent className="max-w-3xl">
                  <DialogHeader>
                    <DialogTitle>Show Notes</DialogTitle>
                    <DialogDescription>Source links and summary</DialogDescription>
                  </DialogHeader>
                  <div className="aspect-[4/3] w-full overflow-hidden rounded-md border">
                    <iframe
                      title="Show notes"
                      src={notesUrl}
                      className="h-full w-full"
                      sandbox="allow-same-origin allow-popups allow-forms allow-scripts"
                    />
                  </div>
                  <DialogFooter className="justify-between sm:justify-between">
                    <a
                      href={notesUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm underline underline-offset-4 text-muted-foreground"
                    >
                      Open in new tab
                    </a>
                    <Button onClick={() => setNotesOpen(false)}>Close</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Button variant="ghost" size="sm" className="gap-2" onClick={() => onCopy(notesUrl!)}>
                <Clipboard className="size-4" />
                Copy notes link
              </Button>
            </>
          )}
          <Button variant="ghost" size="sm" className="gap-2 ml-auto" onClick={onReset}>
            <RefreshCcw className="size-4" />
            Generate another
          </Button>
        </div>
      </div>

      {metrics?.sources && metrics.sources.length > 0 && (
        <div className="grid gap-3">
          <div className="text-sm font-medium">Sources used:</div>
          <ol className="list-decimal list-inside space-y-1 text-sm">
            {metrics.sources.map((source, idx) => (
              <li key={idx}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline underline-offset-2"
                >
                  {source.title}
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}

      {metrics && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {typeof metrics.durationSeconds === "number" && (
            <MetricPill label="Duration" value={formatSeconds(metrics.durationSeconds)} />
          )}
          {typeof metrics.sourcesKept === "number" && (
            <MetricPill label="Sources used" value={`${metrics.sourcesKept}`} />
          )}
        </div>
      )}
    </section>
  )
}

function MetricPill(props: { label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1">
      <span className="text-muted-foreground">{props.label}:</span>
      <span className="font-medium">{props.value}</span>
    </div>
  )
}

function ErrorView(props: { message: string; onReset: () => void }) {
  return (
    <section className="grid place-items-center gap-4 text-center">
      <div className="text-lg font-medium">Something went wrong</div>
      <div className="text-sm text-muted-foreground max-w-prose">{props.message}</div>
      <Button onClick={props.onReset} className="mt-2">
        Try again
      </Button>
    </section>
  )
}

function capitalize(s: string) {
  return s.slice(0, 1).toUpperCase() + s.slice(1)
}
