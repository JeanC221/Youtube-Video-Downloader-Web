import os
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Media Vault API")

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

COBALT_API_URL = "https://api.cobalt.tools/api/json"

class DownloadResponse(BaseModel):
    url: str
    filename: str

@app.get("/api/download", response_model=DownloadResponse)
async def download_video(url: str = Query(..., description="URL of the YouTube video"),
                         type: str = Query("video", description="Format: video or audio")):
    if not url:
        raise HTTPException(status_code=400, detail="URL requerida")
    
    if type not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="El tipo debe ser 'video' o 'audio'")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url,
        "filenamePattern": "classic"
    }
    
    if type == "video":
        payload["vQuality"] = "1080"
    elif type == "audio":
        payload["isAudioOnly"] = True
        payload["aFormat"] = "mp3"
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(COBALT_API_URL, json=payload, headers=headers, timeout=30.0)
            
            if response.status_code != 200:
                logger.error(f"Cobalt API error: {response.text}")
                raise HTTPException(status_code=400, detail="Error procesando el enlace. Intenta de nuevo.")
                
            data = response.json()
            
            if data.get("status") == "error":
                error_msg = data.get("text", "Error desconocido en Cobalt")
                logger.error(f"Cobalt returned error: {error_msg}")
                raise HTTPException(status_code=400, detail=f"No se pudo descargar: {error_msg}")
                
            download_url = data.get("url")
            if not download_url:
                raise HTTPException(status_code=500, detail="Cobalt no retornó un enlace válido.")
                
            filename = f"media_vault_{'video' if type == 'video' else 'audio'}.{'mp4' if type == 'video' else 'mp3'}"
            
            return DownloadResponse(url=download_url, filename=filename)
            
    except httpx.RequestError as e:
        logger.error(f"HTTP Request error connecting to Cobalt: {str(e)}")
        raise HTTPException(status_code=500, detail="Error conectando con el servicio de descarga.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
