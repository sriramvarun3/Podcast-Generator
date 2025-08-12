"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { Loader2, Download, Play } from "lucide-react"
import { createPodcastApi } from "@/lib/podcast-api"

type GenerationState = "idle" | "generating" | "completed" | "error"

interface ResultData {
  id: string;
  topic: string;
  status: string;
  progress: number;
  audio_url?: string | null;
  transcript?: string | null;
  metrics?: {
    duration_seconds?: number;
    word_count?: number;
    average_speaking_rate?: number;
  } | null;
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export default function PodcastGenerator() {
  const [topic, setTopic] = useState("")
  const [state, setState] = useState<GenerationState>("idle")
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<ResultData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [useMockMode, setUseMockMode] = useState(false)

  const handleGenerate = async () => {
    if (!topic.trim()) return;

    setState("generating");
    setProgress(0);
    setError(null);
    setResult(null);
    setJobId(null);
    
    try {
      const api = createPodcastApi(useMockMode);
      const generateResponse = await api.generate({ topic });
      const id = generateResponse.id;
      
      if (!id) {
        setError('Invalid job ID received from server');
        setState("error");
        return;
      }
      
      setJobId(id);
      
      // Poll for results
      let attempts = 0;
      const maxAttempts = useMockMode ? 10 : 60;
      
      const pollResult = async () => {
        attempts++;
        
        try {
          const resultResponse = await api.getResult(id);
          setProgress(resultResponse.progress || 0);
          
          if (resultResponse.status === 'completed') {
            setResult(resultResponse);
            setState("completed");
            setProgress(100);
            return;
          } else if (resultResponse.status === 'failed') {
            setError(resultResponse.error || 'Generation failed');
            setState("error");
            return;
          }
          
          if (attempts < maxAttempts) {
            setTimeout(pollResult, useMockMode ? 2000 : 5000);
          } else {
            setError('Generation timed out - please try again');
            setState("error");
          }
        } catch (pollError) {
          if (attempts < maxAttempts) {
            setTimeout(pollResult, useMockMode ? 2000 : 5000);
          } else {
            setError(pollError instanceof Error ? pollError.message : 'Polling failed');
            setState("error");
          }
        }
      };
      
      setTimeout(pollResult, useMockMode ? 1000 : 2000);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to generate podcast');
      setState("error");
    }
  };

  const handleReset = () => {
    setState("idle");
    setProgress(0);
    setResult(null);
    setError(null);
    setJobId(null);
    setTopic("");
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AI Podcast Generator
          </h1>
          <p className="text-gray-600">
            Generate engaging podcasts from any topic using AI
          </p>
        </div>

        {/* Debug Toggle */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Debug Controls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <Switch
                id="mock-mode"
                checked={useMockMode}
                onCheckedChange={setUseMockMode}
              />
              <Label htmlFor="mock-mode">
                Use Mock Mode {useMockMode ? '(ON)' : '(OFF)'}
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle>Create Your Podcast</CardTitle>
            <CardDescription>
              Enter a topic and we'll create an engaging podcast episode for you
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="topic">Topic</Label>
              <Input
                id="topic"
                placeholder="e.g., The History of Space Exploration"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={state === "generating"}
                className="w-full"
              />
            </div>
            
            <div className="flex gap-2">
              <Button
                onClick={handleGenerate}
                disabled={!topic.trim() || state === "generating"}
                className="flex-1"
              >
                {state === "generating" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Generate Podcast"
                )}
              </Button>
              
              {(state === "completed" || state === "error") && (
                <Button onClick={handleReset} variant="outline">
                  Start Over
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Progress */}
        {state === "generating" && (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    Generating your podcast... {useMockMode && '(Mock Mode)'}
                  </span>
                  <span className="text-sm text-gray-500">{progress}%</span>
                </div>
                <Progress value={progress} className="w-full" />
                {jobId && (
                  <p className="text-xs text-gray-500">Job ID: {jobId}</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {state === "error" && error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="text-red-700">
                <p className="font-medium">Generation Failed</p>
                <p className="text-sm mt-1">{error}</p>
                {jobId && (
                  <p className="text-xs mt-2 text-red-500">Job ID: {jobId}</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results with Audio Player */}
        {state === "completed" && result && (
          <Card className="border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="text-green-800 flex items-center">
                <Play className="mr-2 h-5 w-5" />
                🎉 Podcast Generated Successfully! {useMockMode && '(Mock)'}
              </CardTitle>
              <CardDescription>
                Your podcast about "{result.topic || 'Unknown'}" is ready
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Audio Player Section */}
              {result.audio_url && (
                <div className="space-y-3">
                  <Label className="text-base font-semibold">🎵 Audio Player</Label>
                  {useMockMode ? (
                    <div className="p-4 bg-yellow-100 border border-yellow-300 rounded-lg text-sm text-yellow-800">
                      🎭 Mock audio file - in real implementation this would be a playable MP3
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <audio 
                        controls 
                        className="w-full h-12"
                        style={{ backgroundColor: '#f3f4f6' }}
                      >
                        <source src={result.audio_url} type="audio/mpeg" />
                        Your browser does not support the audio element.
                      </audio>
                      <Button asChild size="sm" variant="outline" className="w-full">
                        <a href={result.audio_url} download={`podcast-${result.topic.replace(/\s+/g, '-').toLowerCase()}.mp3`}>
                          <Download className="mr-2 h-4 w-4" />
                          Download MP3
                        </a>
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Transcript */}
              {result.transcript && typeof result.transcript === 'string' && (
                <div className="space-y-2">
                  <Label className="text-base font-semibold">📄 Transcript</Label>
                  <div className="max-h-40 overflow-y-auto p-4 bg-white rounded-lg border text-sm leading-relaxed">
                    {result.transcript}
                  </div>
                </div>
              )}

              {/* Metrics */}
              {result.metrics && typeof result.metrics === 'object' && (
                <div className="space-y-2">
                  <Label className="text-base font-semibold">📊 Podcast Metrics</Label>
                  <div className="grid grid-cols-3 gap-4 p-4 bg-white rounded-lg border">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {result.metrics.duration_seconds ? Math.round(result.metrics.duration_seconds / 60) : 0}m
                      </div>
                      <div className="text-xs text-gray-500">Duration</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {result.metrics.word_count || 0}
                      </div>
                      <div className="text-xs text-gray-500">Words</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {result.metrics.average_speaking_rate ? Math.round(result.metrics.average_speaking_rate) : 0}
                      </div>
                      <div className="text-xs text-gray-500">WPM</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="text-xs text-gray-500 pt-2 border-t space-y-1">
                <p>Created: {result.created_at ? new Date(result.created_at).toLocaleString() : 'Unknown'}</p>
                <p>Job ID: {result.id || 'Unknown'}</p>
                {useMockMode && (
                  <p className="text-blue-500">🎭 This is mock data for testing</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
