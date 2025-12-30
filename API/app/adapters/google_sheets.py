from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class GoogleSheetsAdapter:
    def __init__(self, credentials_path: str, sheet_name: str):
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
        self.service = build("sheets", "v4", credentials=self.creds)
        self.sheet_name = sheet_name

    def salvar_notas(self, notas):
        # implementação
        pass