from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import os
from app.drive.drive_client import DriveClient
from app.parsers.tcx_parser import parse_tcx_file

app = FastAPI(
    title="Running Coach API",
    description="API che legge file TCX da Google Drive, li processa e li rende disponibili al GPT Running Coach",
    version="1.0.0"
)

# Inizializzazione client Google Drive
drive_client = DriveClient(
    raw_folder_id=os.getenv("GOOGLE_DRIVE_RAW_FOLDER_ID"),
    processed_folder_id=os.getenv("GOOGLE_DRIVE_PROCESSED_FOLDER_ID"),
    logs_folder_id=os.getenv("GOOGLE_DRIVE_LOGS_FOLDER_ID")
)

# INTERVALLO CRON AUTOMATICO (in minuti)
CRON_INTERVAL = int(os.getenv("CRON_INTERVAL_MINUTES", 10))


@app.get("/")
async def root():
    return {"message": "Running Coach API attiva"}


@app.get("/workouts")
async def list_processed_workouts():
    """Ritorna la lista dei file JSON già processati."""
    files = drive_client.list_processed_files()
    return {"processed_files": files}


@app.get("/workout/{filename}")
async def get_processed_workout(filename: str):
    """Scarica un singolo file JSON processato."""
    content = drive_client.get_processed_file(filename)
    if not content:
        return JSONResponse(status_code=404, content={"error": "File non trovato"})
    return content


async def cron_job():
    """Esegue periodicamente l’importazione e il parsing dei file TCX."""
    while True:
        print("🔄 Avvio controllo nuovi allenamenti...")
        
        # Lista dei file TCX da processare
        raw_files = drive_client.list_raw_files()

        for file_name, file_id in raw_files:
            print(f"📥 File trovato: {file_name} — ID: {file_id}")

            # Scarica contenuto
            tcx_content = drive_client.download_file(file_id)

            # Parsing
            try:
                json_data = parse_tcx_file(tcx_content)
            except Exception as e:
                drive_client.log_error(f"Errore parsing {file_name}: {str(e)}")
                continue

            # Salva il JSON nella cartella processed
            drive_client.upload_processed_file(file_name.replace(".tcx", ".json"), json_data)

            # Sposta il file TCX nella cartella processed
            drive_client.move_raw_to_processed(file_id)

            print(f"✅ Processato: {file_name}")

        await asyncio.sleep(CRON_INTERVAL * 60)


@app.on_event("startup")
async def startup_event():
    """Avvia il cron quando l'app parte."""
    asyncio.create_task(cron_job())


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)

