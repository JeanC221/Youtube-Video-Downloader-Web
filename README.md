# YouTube Video Downloader Web

A modern, web-based application for downloading YouTube videos and extracting audio in high quality, built with a distributed microservices architecture.

> **Note:** The original Flet-based desktop application has been deprecated and moved to the `legacy_desktop` directory for historical reference.

## Architecture

This project is decoupled into two primary services:

### 1. Frontend (Netlify Ready)
- **Tech Stack:** Vite, Vanilla JavaScript, HTML5, and Tailwind CSS v4.
- **Features:** 
  - Modern "glassmorphism" user interface.
  - Responsive design with smooth animations.
  - Triggers native browser downloads without consuming excessive client RAM.
- **Directory:** `/frontend`

### 2. Backend (Render Ready)
- **Tech Stack:** Python 3.11+, FastAPI, Uvicorn, and yt-dlp.
- **Features:** 
  - Streams video data directly to the client (via stdout and FastAPI StreamingResponse).
  - Bypasses persistent disk storage requirements on cloud hosting environments (like Render).
  - Uses `player-client` HTTP 403 workarounds to ensure stable downloads.
- **Directory:** `/backend`

---

## Local Development Setup

### Backend

1. Navigate to the root directory and create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

The backend API will be available at `http://localhost:8000`.

### Frontend

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

The frontend application will be accessible at `http://localhost:3000`.

---

## Deployment

### Deploying the Backend to Render
1. Connect your repository to Render.
2. Create a new **Web Service**.
3. Render will automatically detect the `render.yaml` configuration in the root directory.
4. Ensure the `FRONTEND_URL` environment variable is set to your Netlify production domain.

### Deploying the Frontend to Netlify
1. Connect your repository to Netlify.
2. Set the Base Directory to `frontend`.
3. Build command: `npm run build`
4. Publish directory: `frontend/dist`
5. The `netlify.toml` file will automatically handle SPA redirects.
6. Make sure to configure the `VITE_API_URL` environment variable in Netlify to point to your Render Backend URL.

---

## License
MIT License. See `LICENSE` for more information.
