# Podcast Generator Backend

A production-ready FastAPI service that generates AI-powered podcasts from web content. This backend handles the entire podcast generation pipeline: web search, content extraction, AI script generation, text-to-speech conversion, and audio processing.

## Features

- **Web Search & Content Extraction**: Automatically finds and scrapes diverse sources about any topic
- **AI Script Generation**: Uses LLM providers (OpenAI, Anthropic, Google AI) to create engaging podcast scripts
- **Text-to-Speech**: Multiple TTS providers (ElevenLabs, OpenAI) with voice selection
- **Advanced Audio Processing**: Music bed mixing, loudness normalization, and audio enhancement
- **Job Queue System**: Asynchronous job processing with progress tracking and cancellation
- **RESTful API**: Clean, documented API endpoints for frontend integration
- **Production Ready**: Proper error handling, logging, and configuration management

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI        │    │   Services      │
│   (React)       │◄──►│   Backend        │◄──►│   Layer         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Job Queue      │    │   External      │
                       │   System         │    │   APIs          │
                       └──────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg (for audio processing)
- API keys for your chosen providers

### Installation

1. **Clone the repository**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

## Configuration

Create a `.env` file with your API keys:

```env
# LLM Providers
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here

# TTS Providers
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

## API Endpoints

### Core Endpoints

- `POST /api/v1/generate` - Start podcast generation
- `GET /api/v1/jobs/{job_id}/status` - Get job status
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel a job
- `GET /api/v1/jobs` - List all jobs
- `GET /api/v1/queue/stats` - Get queue statistics

### Static File Serving

- `GET /api/v1/static/podcasts/{filename}` - Download generated podcasts
- `GET /api/v1/static/notes/{filename}` - Download show notes
- `GET /api/v1/static/scripts/{filename}` - Download scripts

### Utility Endpoints

- `GET /health` - Health check
- `GET /api/v1/providers/llm` - List LLM providers
- `GET /api/v1/providers/tts` - List TTS providers
- `GET /api/v1/voices` - List available TTS voices

## Usage Example

### 1. Generate a Podcast

```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Artificial Intelligence in Healthcare",
    "description": "Explore how AI is transforming healthcare delivery and patient outcomes",
    "tone": "professional",
    "length": 10
  }'
```

Response:
```json
{
  "status": "running",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/status"
```

### 3. Download Generated Content

Once the job completes, download the files:
- Podcast: `/api/v1/static/podcasts/podcast_{job_id}.mp3`
- Notes: `/api/v1/static/notes/notes_{job_id}.md`
- Script: `/api/v1/static/scripts/script_{job_id}.txt`

## Service Architecture

### Core Services

- **PodcastGenerator**: Main orchestrator service
- **WebSearchService**: Web search and source discovery
- **ContentExtractor**: Web scraping and content cleaning
- **LLMProviderFactory**: AI script generation
- **TTSProviderFactory**: Text-to-speech conversion
- **AudioProcessor**: Audio enhancement and mixing
- **JobQueue**: Background job management

### Provider Support

#### LLM Providers
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude-3 models
- **Google AI**: Gemini Pro

#### TTS Providers
- **ElevenLabs**: High-quality voices with customization
- **OpenAI**: TTS-1 model with multiple voice options

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/           # API routes and endpoints
│   ├── core/          # Configuration and utilities
│   ├── models/        # Pydantic data models
│   └── services/      # Business logic services
├── static/            # Generated content storage
├── logs/              # Application logs
├── main.py            # FastAPI application entry point
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Set these in production:
- `DEBUG=false`
- `LOG_LEVEL=WARNING`
- `CORS_ORIGINS=https://yourdomain.com`
- All required API keys

### Scaling Considerations

- Use Redis for persistent job queue storage
- Implement database for job history
- Add monitoring and metrics collection
- Use load balancer for multiple instances

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Ensure FFmpeg is installed and in PATH
2. **Audio processing errors**: Check audio file permissions and disk space
3. **API key errors**: Verify all required API keys are set in `.env`
4. **Memory issues**: Reduce `max_content_length` in settings

### Logs

Check application logs in `logs/app.log` for detailed error information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation at `/docs`
- Open an issue on GitHub 