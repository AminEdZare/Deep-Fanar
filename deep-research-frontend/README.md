# DeepFanar Research Frontend

A React-based frontend for the DeepFanar AI research assistant that provides comprehensive research capabilities with multilingual support.

## Features

- **AI-Powered Research**: Submit research queries and receive comprehensive, synthesized reports
- **Multilingual Support**: Research in both English and Arabic with parallel processing
- **Real-time Progress**: Stream progress updates during research execution
- **Text-to-Speech**: Convert research reports to audio using Fanar TTS
- **Export Options**: Copy reports to clipboard or download as files
- **Source Citations**: View and access all research sources with clickable links

## Text-to-Speech Feature

The application includes a text-to-speech feature that allows users to listen to research reports:

- Click the volume icon (🔊) in the side panel to convert the report to speech
- Uses Fanar-Aura-TTS-1 model for high-quality audio synthesis
- Automatically truncates very long content to ensure reasonable processing times
- Shows loading state and playing indicators for better user experience

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Ensure the backend server is running on `http://localhost:8000`

## Technology Stack

- React 18
- Vite
- FastAPI (backend)
- Fanar AI API
- OpenAI-compatible TTS API

## Development

This project uses:
- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) for Fast Refresh
- ESLint for code quality
- CSS modules for styling
