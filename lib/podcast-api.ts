"use client"

interface PodcastRequest {
  topic: string;
}

interface ResultResponse {
  id: string;
  topic: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'unknown';
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

interface GenerateResponse {
  id: string;
}

interface PodcastApi {
  generate: (request: PodcastRequest) => Promise<GenerateResponse>;
  getResult: (id: string) => Promise<ResultResponse>;
}

// Debug logging utility for client-side
const debugLog = {
  info: (message: string, data?: any) => {
    if (typeof window !== 'undefined') {
      console.log(`🔧 [PODCAST-API] ${message}`, data || '');
    }
  },
  error: (message: string, error?: any) => {
    if (typeof window !== 'undefined') {
      console.error(`❌ [PODCAST-API] ${message}`, error || '');
    }
  },
  success: (message: string, data?: any) => {
    if (typeof window !== 'undefined') {
      console.log(`✅ [PODCAST-API] ${message}`, data || '');
    }
  },
  warn: (message: string, data?: any) => {
    if (typeof window !== 'undefined') {
      console.warn(`⚠️ [PODCAST-API] ${message}`, data || '');
    }
  }
};

const createHttpApi = (useMock: boolean = false): PodcastApi => {
  const baseUrl = 'http://localhost:8000/api/v1';
  const endpoint = useMock ? 'mock' : '';
  
  debugLog.info(`Creating HTTP API client`, { baseUrl, useMock, endpoint });

  return {
    generate: async (request: PodcastRequest): Promise<GenerateResponse> => {
      debugLog.info('Starting podcast generation request', request);
      
      try {
        const url = `${baseUrl}/${endpoint}${endpoint ? '/' : ''}generate`;
        
        // For real backend, we need additional fields
        const payload = useMock ? request : {
          topic: request.topic,
          description: "",
          tone: "neutral" as const,
          length: 10 as const
        };
        
        debugLog.info('Making POST request', { url, payload });
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        debugLog.info('Response received', { 
          status: response.status, 
          ok: response.ok,
          headers: Object.fromEntries(response.headers.entries())
        });

        if (!response.ok) {
          const errorText = await response.text();
          debugLog.error('Error response received', { status: response.status, body: errorText });
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        debugLog.success('Generate request successful', result);
        
        // Validate that we got an ID
        if (!result.id) {
          debugLog.error('No ID in generate response', result);
          throw new Error('Invalid response: missing job ID');
        }
        
        debugLog.info('Returning generate response', { id: result.id });
        return { id: result.id };
      } catch (error) {
        debugLog.error('Generate request failed', { 
          error: error instanceof Error ? error.message : String(error),
          type: typeof error 
        });
        throw error;
      }
    },

    getResult: async (id: string): Promise<ResultResponse> => {
      debugLog.info('Getting result', { jobId: id });
      
      // Validate input
      if (!id || id === 'undefined' || id === 'null') {
        debugLog.error('Invalid job ID provided', { id });
        throw new Error(`Invalid job ID: ${id}`);
      }
      
      try {
        const url = `${baseUrl}/${endpoint}${endpoint ? '/' : ''}result/${id}`;
        debugLog.info('Making GET request', { url });
        
        const response = await fetch(url);
        
        debugLog.info('Result response received', { 
          status: response.status, 
          ok: response.ok 
        });

        if (!response.ok) {
          const errorText = await response.text();
          debugLog.error('Result error response', { status: response.status, body: errorText });
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        debugLog.info('API Response details', { 
          status: response.status, 
          headers: response.headers,
          url: response.url 
        });
        
        const resultResponse: ResultResponse = await response.json();
        debugLog.info('Result response data', resultResponse);
        
        // Fallback: If job is completed but audio_url is missing, construct it manually
        if (resultResponse.status === 'completed' && !resultResponse.audio_url && resultResponse.id) {
          debugLog.info('Job completed but missing audio_url, constructing fallback URLs');
          const baseUrl = 'http://localhost:8000';
          resultResponse.audio_url = `${baseUrl}/api/v1/static/podcasts/podcast_${resultResponse.id}.mp3`;
          
          // Also try to construct transcript URL if missing
          if (!resultResponse.transcript) {
            try {
              const scriptResponse = await fetch(`${baseUrl}/api/v1/static/scripts/script_${resultResponse.id}.txt`);
              if (scriptResponse.ok) {
                resultResponse.transcript = await scriptResponse.text();
                debugLog.info('Successfully fetched transcript from file');
              }
            } catch (error) {
              debugLog.warn('Could not fetch transcript file', { error });
            }
          }
          
          // Construct basic metrics if missing
          if (!resultResponse.metrics && resultResponse.transcript) {
            const wordCount = resultResponse.transcript.split(/\s+/).length;
            const estimatedDuration = (wordCount / 150) * 60; // 150 WPM
            
            resultResponse.metrics = {
              duration_seconds: estimatedDuration,
              word_count: wordCount,
              average_speaking_rate: 150
            };
            debugLog.info('Constructed fallback metrics', resultResponse.metrics);
          }
          
          debugLog.info('Fallback URLs constructed', { 
            audio_url: resultResponse.audio_url,
            has_transcript: !!resultResponse.transcript,
            has_metrics: !!resultResponse.metrics
          });
        }
        
        return resultResponse;
      } catch (error) {
        debugLog.error('Get result request failed', { 
          error: error instanceof Error ? error.message : String(error),
          type: typeof error,
          jobId: id
        });
        throw error;
      }
    },
  };
};

export const createPodcastApi = (useMock: boolean = false): PodcastApi => {
  debugLog.info('Creating podcast API client', { useMock });
  return createHttpApi(useMock);
};

// Export debug utilities for use in components
export { debugLog };