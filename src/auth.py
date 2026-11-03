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

def get_credentials():
    """
    Lấy thông tin xác thực Service Account.
    Ưu tiên 1: Biến môi trường GCP_SA_KEY (chứa chuỗi JSON, thiết lập trên GitHub Secrets).
    Ưu tiên 2: Biến môi trường GOOGLE_APPLICATION_CREDENTIALS (chứa đường dẫn file).
    Ưu tiên 3: File 'credentials.json' nằm ở thư mục gốc dự án (khi chạy test local).
    """
    # 1. GitHub Actions Secrets
    sa_json = os.environ.get('GCP_SA_KEY')
    if sa_json:
        try:
            clean_json = sa_json.strip().lstrip('\ufeff')
            info = json.loads(clean_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            raise ValueError(f"Không thể phân tích dữ liệu JSON từ biến môi trường GCP_SA_KEY: {e}")

    # 2. File đường dẫn
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    if os.path.exists(creds_path):
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
