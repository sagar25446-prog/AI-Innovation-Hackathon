# Third-Party Component Disclosure

GuruFlow uses the following third-party components, libraries, and APIs.

## APIs and Cloud Services

| Service | Purpose | License | Usage |
|---------|---------|---------|-------|
| Google Gemini 2.5 Flash (`gemini-2.5-flash`) | LLM-powered lesson planning and answer evaluation | Google AI Studio Terms | Free tier, optional |
| D-ID API | Lip-synced avatar video generation | D-ID Terms of Service | **Optional and not wired into the running app.** GuruFlow renders its own teaching video locally; the adapter is retained only as an alternative provider |
| edge-tts | Text-to-speech synthesis (Microsoft neural voices) | MIT License | Free, no API key needed. **Requires >= 7.2**: 7.0.x returns HTTP 403 after Microsoft changed the Sec-MS-GEC token scheme |
| gTTS | Fallback text-to-speech | MIT License | Free, used only if edge-tts fails |

## Python Libraries

| Library | Purpose | License |
|---------|---------|---------|
| FastAPI | Backend API framework | MIT License |
| Pydantic | Data validation | MIT License |
| uvicorn | ASGI server | BSD-3-Clause |
| httpx | HTTP client | BSD-3-Clause |
| google-generativeai | Gemini API client | Apache 2.0 |
| edge-tts | Microsoft Neural TTS | MIT License |
| gTTS | Fallback TTS | MIT License |
| Manim Community Edition | Programmatic teaching animation (video generation) | MIT License |
| imageio-ffmpeg | Bundled static ffmpeg binary for muxing audio and video | BSD-2-Clause |
| PyMuPDF | PDF document parsing | AGPL-3.0 |
| sentence-transformers | Semantic text embeddings | Apache 2.0 | *(optional, see requirements-vector.txt)* |
| ChromaDB | Vector database | Apache 2.0 | *(optional, see requirements-vector.txt)* |
| python-multipart | File upload support | BSD License |

## Frontend Libraries

| Library | Purpose | License |
|---------|---------|---------|
| Vanilla JavaScript | Frontend framework (no build step) | N/A |
| SVG | Visual rendering (circuits, graphs, equations) | N/A |

## Pre-trained Models

| Model | Purpose | License |
|-------|---------|---------|
| all-MiniLM-L6-v2 (sentence-transformers) | Semantic text embeddings for RAG | Apache 2.0 |

## Educational Content

| Source | Usage |
|--------|-------|
| NCERT Class 9 Science, Chapter 12: Electricity | Built-in demo corpus for Ohm's Law lesson. Used under fair use for educational demonstration purposes. |

## Deterministic Fallback Path

Every cloud service and API has a deterministic fallback:
- **No Gemini API key**: The planner and evaluator use hardcoded deterministic logic
- **No D-ID API key**: A CSS-animated teacher panel with captions is shown
- **No edge-tts**: Browser Web Speech API is used as fallback
- **No embeddings**: Keyword-overlap retrieval is used instead

The entire demo can run with **zero API keys** and **zero network access** using the built-in Ohm's Law corpus and demo fixtures.
