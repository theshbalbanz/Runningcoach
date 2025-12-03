import json
import base64
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

class DriveClient:
    def __init__(self, raw_folder_id, processed_folder_id, logs_folder_id):
        self.raw_folder_id = raw_folder_id
        self.processed_folder_id = processed_folder_id
        self.logs_folder_id = logs_folder_id

        # Carica la chiave privata dal valore della variabile d'ambiente
        service_account_json = json.loads(
            base64.b64decode(
                str.encode(
                    # Render salva il JSON come variabile di ambiente unica
                    # Qui lo ripristiniamo e convertiamo in dict
                    json.dumps(
                        json.loads(
                            json.loads(
                                base64.b64encode(
                                    json.dumps(json.loads(
                                        service_account_json_env := json.loads(
                                            json.dumps(
                                                json.loads(
                                                    base64.b64decode(
                                                        service_account_json_env
                                                    )
                                                )
                                            )
                                        )
                                    ).encode("utf-8")
                                ).decode("utf-8")
                            )
                        )
                    )
                )
            )
        )

        credentials = service_account.Credentials.from_service_account_info(
            service_account_json,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        self.drive = build("drive", "v3", credentials=credentials)

    # ---------------------------------------------------------
    # RAW FILES
    # ---------------------------------------------------------

    def list_raw_files(self):
        """Ritorna lista di file nella cartella RAW (nome, id)."""
        query = f"'{self.raw_folder_id}' in parents"
        results = self.drive.files().list(q=query, fields="files(id, name)").execute()
        return [(f["name"], f["id"]) for f in results.get("files", [])]

    def download_file(self, file_id):
        """Scarica un file da Google Drive e ritorna il contenuto (stringa TCX)."""
        request = self.drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        return fh.getvalue().decode("utf-8")

    # ---------------------------------------------------------
    # PROCESSED FILES
    # ---------------------------------------------------------

    def upload_processed_file(self, filename, json_content):
        """Salva un file JSON nella cartella processed."""
        file_metadata = {
            "name": filename,
            "parents": [self.processed_folder_id]
        }

        media = MediaIoBaseUpload(
            io.BytesIO(json.dumps(json_content).encode("utf-8")),
            mimetype="application/json",
            resumable=False
        )

        self.drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

    def list_processed_files(self):
        """Elenca file JSON già processati."""
        query = f"'{self.processed_folder_id}' in parents"
        results = self.drive.files().list(q=query, fields="files(id, name)").execute()
        return [f["name"] for f in results.get("files", [])]

    def get_processed_file(self, filename):
        """Legge un file JSON dalla cartella processed."""
        query = f"name='{filename}' and '{self.processed_folder_id}' in parents"
        results = self.drive.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if not files:
            return None

        file_id = files[0]["id"]
        content = self.download_file(file_id)
        return json.loads(content)

    # ---------------------------------------------------------
    # LOGGING
    # ---------------------------------------------------------

    def log_error(self, message):
        """Scrive un file di log nella cartella logs."""
        filename = "error_log.txt"
        file_metadata = {
            "name": filename,
            "parents": [self.logs_folder_id]
        }

        media = MediaIoBaseUpload(
            io.BytesIO(message.encode("utf-8")),
            mimetype="text/plain",
            resumable=False
        )

        self.drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

    # ---------------------------------------------------------
    # MOVE RAW → PROCESSED
    # ---------------------------------------------------------

    def move_raw_to_processed(self, file_id):
        """Sposta un file dalla cartella RAW a quella PROCESSED."""
        file = self.drive.files().get(fileId=file_id, fields="parents").execute()

        # Rimuove parent esistente
        previous_parents = ",".join(file.get("parents"))
        self.drive.files().update(
            fileId=file_id,
            addParents=self.processed_folder_id,
            removeParents=previous_parents,
            fields="id, parents"
        ).execute()
