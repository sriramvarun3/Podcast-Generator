# AI Podcast Generator

An intelligent, full-stack application that automatically generates high-quality podcasts from any topic using AI. The system combines web research, content extraction, AI-powered script generation, text-to-speech conversion, and professional audio processing to create engaging podcast episodes.

## 🎯 Overview

This application allows users to generate complete podcast episodes by simply entering a topic. The system:

1. **Researches** the topic using web search to find diverse, relevant sources
2. **Extracts** and cleans content from multiple sources
3. **Generates** an engaging podcast script using AI (OpenAI, Anthropic, or Google AI)
4. **Converts** the script to natural-sounding speech using TTS providers
5. **Enhances** the audio with music beds, normalization, and professional processing
6. **Delivers** a complete podcast with transcript and show notes

## ✨ Features

### Core Functionality
- **Intelligent Web Research**: Automatically finds and extracts content from diverse sources
- **AI Script Generation**: Creates engaging, well-structured podcast scripts using state-of-the-art LLMs
- **High-Quality TTS**: Multiple TTS provider support (ElevenLabs, OpenAI) with voice selection
- **Professional Audio Processing**: Music bed mixing, loudness normalization, and audio enhancement
- **Asynchronous Processing**: Background job queue with real-time progress tracking
- **Complete Output**: Generates podcast audio, transcript, and show notes

### User Experience
- **Modern Web Interface**: Built with Next.js and React for a smooth, responsive experience
- **Real-Time Progress**: Live updates on podcast generation progress
- **Mock Mode**: Test the interface without API calls
- **Download Support**: Download generated podcasts, transcripts, and notes
- **Metrics Display**: View podcast statistics (duration, word count, speaking rate)

## 🏗️ Architecture

### Frontend (Next.js + TypeScript)
- **Framework**: Next.js 15 with React 19
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React hooks for local state
- **API Integration**: RESTful API client with polling for job status

### Backend (FastAPI + Python)
- **Framework**: FastAPI with async/await support
- **Services**:
  - `WebSearchService`: DuckDuckGo search integration
  - `ContentExtractor`: Web scraping and content cleaning
  - `LLMProviderFactory`: Multi-provider AI script generation
  - `TTSProviderFactory`: Text-to-speech conversion
  - `AudioProcessor`: Audio enhancement and mixing
  - `JobQueue`: Background job management
- **Storage**: File-based storage for generated content

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm/pnpm
- **Python** 3.8+
- **FFmpeg** (for audio processing)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:sriramvarun3/Podcast-Generator.git
   cd podcast-generator
   ```

2. **Set up the frontend**
   ```bash
   npm install
   # or
   pnpm install
   ```

3. **Set up the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r ../requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the `backend` directory:
   ```env
   # LLM Providers (at least one required)
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   GOOGLE_API_KEY=your_google_key_here

   # TTS Providers (at least one required)
   ELEVENLABS_API_KEY=your_elevenlabs_key_here

   # Application Settings
   DEBUG=true
   HOST=0.0.0.0
   PORT=8000
   LOG_LEVEL=INFO

   # Audio Settings
   TARGET_LUFS=-16.0
   SAMPLE_RATE=44100
   BIT_RATE=192
   ```

5. **Start the backend server**
   ```bash
   cd backend
   python main.py
   ```
   The API will be available at `http://localhost:8000`

6. **Start the frontend** (in a new terminal)
   ```bash
   npm run dev
   # or
   pnpm dev
   ```
   The app will be available at `http://localhost:3000`

## 📖 Usage

1. **Open the application** in your browser at `http://localhost:3000`
2. **Enter a topic** you want to create a podcast about (e.g., "The History of Space Exploration")
3. **Click "Generate Podcast"** to start the process
4. **Monitor progress** as the system researches, generates, and processes your podcast
5. **Download or play** the completed podcast, view the transcript, and check metrics

### Mock Mode

Toggle "Use Mock Mode" in the Debug Controls section to test the interface without making actual API calls. This is useful for development and testing.

## 🔧 API Endpoints

### Core Endpoints
- `POST /api/v1/generate` - Start podcast generation
- `GET /api/v1/result/{job_id}` - Get job status and results
- `GET /api/v1/jobs/{job_id}/status` - Get detailed job status
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel a running job
- `GET /api/v1/jobs` - List all jobs

### Static File Serving
- `GET /api/v1/static/podcasts/{filename}` - Download generated podcasts
- `GET /api/v1/static/notes/{filename}` - Download show notes
- `GET /api/v1/static/scripts/{filename}` - Download scripts

### Utility Endpoints
- `GET /health` - Health check
- `GET /api/v1/providers/llm` - List configured LLM providers
- `GET /api/v1/providers/tts` - List configured TTS providers
- `GET /api/v1/voices` - List available TTS voices

## 🛠️ Technology Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - High-quality component library
- **Lucide React** - Icon library

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and settings
- **Loguru** - Advanced logging
- **Trafilatura** - Web content extraction
- **pydub** - Audio processing
- **httpx** - Async HTTP client

### AI & Audio Services
- **LLM Providers**: OpenAI GPT-4, Anthropic Claude, Google Gemini
- **TTS Providers**: ElevenLabs, OpenAI TTS
- **Audio Processing**: FFmpeg for professional audio enhancement

## 📁 Project Structure

```
podcast-generator/
├── app/                    # Next.js frontend app
│   ├── page.tsx           # Main podcast generator UI
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/                # shadcn/ui components
│   └── ...
├── lib/                   # Frontend utilities
│   └── podcast-api.ts    # API client
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Configuration
│   │   ├── models/       # Data models
│   │   └── services/     # Business logic
│   ├── static/           # Generated content
│   │   ├── podcasts/     # MP3 files
│   │   ├── scripts/      # Transcripts
│   │   └── notes/        # Show notes
│   ├── main.py           # FastAPI entry point
│   └── README.md         # Backend documentation
├── requirements.txt       # Python dependencies
├── package.json          # Node.js dependencies
└── README.md            # This file
```

## 🔐 Environment Variables

### Required (at least one LLM and one TTS provider)
- `OPENAI_API_KEY` - For OpenAI GPT models and TTS
- `ANTHROPIC_API_KEY` - For Claude models
- `GOOGLE_API_KEY` - For Gemini models
- `ELEVENLABS_API_KEY` - For ElevenLabs TTS

### Optional
- `DEBUG` - Enable debug mode (default: `false`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `TARGET_LUFS` - Target loudness (default: `-16.0`)
- `SAMPLE_RATE` - Audio sample rate (default: `44100`)
- `BIT_RATE` - Audio bit rate in kbps (default: `192`)

## 🐛 Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Ensure FFmpeg is installed and available in your PATH
   - Verify installation: `ffmpeg -version`

2. **API key errors**
   - Verify all required API keys are set in `.env`
   - Check that at least one LLM and one TTS provider is configured

3. **Audio processing errors**
   - Check file permissions on the `static/` directory
   - Ensure sufficient disk space
   - Verify FFmpeg installation

4. **CORS errors**
   - Ensure backend CORS settings allow your frontend origin
   - Check that backend is running on the expected port

5. **Job timeouts**
   - Increase polling timeout in frontend
   - Check backend logs for processing errors
   - Verify API provider rate limits

### Logs

- **Backend logs**: Check `backend/logs/app.log` for detailed error information
- **Frontend logs**: Check browser console for client-side errors

## 🚢 Deployment

### Backend Deployment

The backend can be deployed using:
- **Docker**: See `backend/README.md` for Docker configuration
- **Cloud platforms**: Vercel, Railway, Render, etc.
- **Traditional servers**: Use uvicorn with a process manager

### Frontend Deployment

The Next.js frontend can be deployed to:
- **Vercel** (recommended for Next.js)
- **Netlify**
- **Any static hosting** (after `npm run build`)

### Production Considerations

- Set `DEBUG=false` in production
- Use environment-specific API keys
- Configure CORS origins properly
- Set up monitoring and error tracking
- Use a database for job persistence (optional)
- Implement rate limiting
- Use Redis for job queue (optional, for scaling)

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation at `http://localhost:8000/docs`
- Open an issue on GitHub

---

**Built with ❤️ using Next.js, FastAPI, and AI**
