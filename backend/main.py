import os
import subprocess
import logging
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Downloader API")

# Configure CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
origins = [FRONTEND_URL] if FRONTEND_URL != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_video_info(url: str, type_selection: str):
    """
    Obtiene la información del video. 
    type_selection puede ser 'video' o 'audio'.
    """
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'best[ext=mp4]/best' if type_selection == "video" else 'bestaudio[ext=m4a]/bestaudio/best',
        'extractor_args': {'youtube': ['player-client=ios,android,web']}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("No se pudo extraer la información.")
            
            title = info.get('title', 'download')
            # Limpiar nombre de archivo
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
            
            ext = info.get('ext', 'mp4')
            filename = f"{safe_title}.{ext}"
            return filename, info
    except Exception as e:
        logger.error(f"Error extrayendo info de {url}: {e}")
        raise ValueError(f"Bloqueo de YouTube detectado: {str(e)}")

@app.get("/api/download")
async def download_video(url: str = Query(..., description="URL of the YouTube video"),
                         type: str = Query("video", description="Format: video or audio")):
    if not url:
        raise HTTPException(status_code=400, detail="URL requerida")
    
    if type not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="El tipo debe ser 'video' o 'audio'")
    
    try:
        filename, info = get_video_info(url, type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # yt-dlp stream generator
    def iter_file():
        import sys
        format_sel = 'best[ext=mp4]/best' if type == 'video' else 'bestaudio[ext=m4a]/bestaudio/best'
        
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '-f', format_sel,
            '-o', '-',
            '--quiet',
            '--no-playlist',
            '--extractor-args', 'youtube:player-client=ios,android,web',
            url
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
            
            # Check for errors after the stream is done
            stderr_output = process.stderr.read().decode('utf-8')
            if stderr_output and "ERROR" in stderr_output:
                logger.error(f"yt-dlp error: {stderr_output}")
                
        finally:
            process.stdout.close()
            process.stderr.close()
            process.wait()

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Access-Control-Expose-Headers': 'Content-Disposition'
    }
    
    return StreamingResponse(iter_file(), media_type="application/octet-stream", headers=headers)
