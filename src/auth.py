"""
Module quản lý xác thực Google API thông qua Service Account.
Hỗ trợ cả môi trường GitHub Actions (biến môi trường GCP_SA_KEY) và máy tính cục bộ (credentials.json).
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def _load_env_if_needed():
    for p in [".env", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

def get_credentials():
    """
    Lấy thông tin xác thực Service Account.
    Ưu tiên 1: Biến môi trường GCP_SA_KEY (chứa chuỗi JSON hoặc đường dẫn file).
    Ưu tiên 2: Biến môi trường GOOGLE_APPLICATION_CREDENTIALS (chứa đường dẫn file).
    Ưu tiên 3: Các đường dẫn chuẩn hóa (credentials.json, Windows/Linux secret path).
    """
    _load_env_if_needed()

    # 1. Biến môi trường GCP_SA_KEY
    sa_json = os.environ.get('GCP_SA_KEY')
    if sa_json:
        if os.path.exists(sa_json):
            return Credentials.from_service_account_file(sa_json, scopes=SCOPES)
        try:
            clean_json = sa_json.strip().lstrip('\ufeff')
            info = json.loads(clean_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            raise ValueError(f"Không thể phân tích dữ liệu JSON từ biến môi trường GCP_SA_KEY: {e}")

    # 2. File đường dẫn (từ GOOGLE_APPLICATION_CREDENTIALS hoặc credentials.json)
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    if creds_path and os.path.exists(creds_path):
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    return None

def get_sheets_service(creds=None):
    """
    Trả về Google Sheets API v4 Resource.
    """
    if creds is None:
        creds = get_credentials()
    if creds is None:
        raise RuntimeError(
            "Chưa cấu hình Service Account! "
            "Vui lòng thiết lập biến môi trường GCP_SA_KEY hoặc cung cấp file credentials.json."
        )
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)

def get_drive_service(creds=None):
    """
    Trả về Google Drive API v3 Resource.
    """
    if creds is None:
        creds = get_credentials()
    if creds is None:
        raise RuntimeError(
            "Chưa cấu hình Service Account! "
            "Vui lòng thiết lập biến môi trường GCP_SA_KEY hoặc cung cấp file credentials.json."
        )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)

def get_gspread_client(creds=None):
    """
    Trả về Gspread Client tiện ích.
    """
    if creds is None:
        creds = get_credentials()
    if creds is None:
        raise RuntimeError(
            "Chưa cấu hình Service Account! "
            "Vui lòng thiết lập biến môi trường GCP_SA_KEY hoặc cung cấp file credentials.json."
        )
    return gspread.authorize(creds)
