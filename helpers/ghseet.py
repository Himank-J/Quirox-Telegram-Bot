from typing import Any, List, Dict
import argparse
import os
import asyncio
import json
import logging
import base64
from email.message import EmailMessage
from email.header import decode_header
from base64 import urlsafe_b64decode
from email import message_from_bytes
import webbrowser

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

class GoogleSheetsService:
    def __init__(self,
                 token_path: str = 'token.json',
                 credentials_path: str = 'credentials.json',
                 drive_folder_id: str = None):
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.drive_folder_id = drive_folder_id

        self.creds = self._authenticate()
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_sheet_data(self, spreadsheet_id: str, sheet: str, range_: str = None) -> list:
        full_range = f"{sheet}!{range_}" if range_ else sheet
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=full_range).execute()
        return result.get('values', [])

    def update_cells(self, spreadsheet_id: str, sheet: str, range_: str, data: list) -> dict:
        full_range = f"{sheet}!{range_}"
        value_range_body = {'values': data}
        result = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption='USER_ENTERED',
            body=value_range_body
        ).execute()
        return result

    def batch_update_cells(self, spreadsheet_id: str, sheet: str, ranges: dict) -> dict:
        data = []
        for range_str, values in ranges.items():
            full_range = f"{sheet}!{range_str}"
            data.append({'range': full_range, 'values': values})
        batch_body = {'valueInputOption': 'USER_ENTERED', 'data': data}
        result = self.sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=batch_body).execute()
        return result

    def add_rows(self, spreadsheet_id: str, sheet: str, count: int, start_row: int = None) -> dict:
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = next((s['properties']['sheetId'] for s in spreadsheet['sheets'] if s['properties']['title'] == sheet), None)
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_row if start_row is not None else 0,
                            "endIndex": (start_row if start_row is not None else 0) + count
                        },
                        "inheritFromBefore": start_row is not None and start_row > 0
                    }
                }
            ]
        }
        result = self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body).execute()
        return result

    def add_columns(self, spreadsheet_id: str, sheet: str, count: int, start_column: int = None) -> dict:
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = next((s['properties']['sheetId'] for s in spreadsheet['sheets'] if s['properties']['title'] == sheet), None)
        if sheet_id is None:
            return {"error": f"Sheet '{sheet}' not found"}
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column if start_column is not None else 0,
                            "endIndex": (start_column if start_column is not None else 0) + count
                        },
                        "inheritFromBefore": start_column is not None and start_column > 0
                    }
                }
            ]
        }
        result = self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body).execute()
        return result

    def list_sheets(self, spreadsheet_id: str) -> list:
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

    def create_spreadsheet(self, title: str) -> dict:
        spreadsheet_body = {'properties': {'title': title}}
        spreadsheet = self.sheets_service.spreadsheets().create(
            body=spreadsheet_body, fields='spreadsheetId,properties,sheets').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        if self.drive_folder_id:
            file = self.drive_service.files().get(fileId=spreadsheet_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=self.drive_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        return {
            'spreadsheetId': spreadsheet_id,
            'title': spreadsheet.get('properties', {}).get('title', title),
            'sheets': [sheet.get('properties', {}).get('title', 'Sheet1') for sheet in spreadsheet.get('sheets', [])],
            'folder': self.drive_folder_id if self.drive_folder_id else 'root'
        }
    
    def share_spreadsheet(self, spreadsheet_id: str, recipients: List[Dict[str, str]], send_notification: bool = True,) -> Dict[str, List[Dict[str, Any]]]:
        """
        Share a Google Spreadsheet with multiple users via email, assigning specific roles.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet to share.
            recipients: A list of dictionaries, each containing 'email_address' and 'role'.
                        The role should be one of: 'reader', 'commenter', 'writer'.
                        Example: [
                            {'email_address': 'user1@example.com', 'role': 'writer'},
                            {'email_address': 'user2@example.com', 'role': 'reader'}
                        ]
            send_notification: Whether to send a notification email to the users. Defaults to True.

        Returns:
            A dictionary containing lists of 'successes' and 'failures'. 
            Each item in the lists includes the email address and the outcome.
        """
        drive_service = self.drive_service
        successes = []
        failures = []
        
        for recipient in recipients:
            email_address = recipient.get('email_address')
            role = recipient.get('role', 'writer') 
            
            if not email_address:
                failures.append({
                    'email_address': None,
                    'error': 'Missing email_address in recipient entry.'
                })
                continue
                
            if role not in ['reader', 'commenter', 'writer']:
                failures.append({
                    'email_address': email_address,
                    'error': f"Invalid role '{role}'. Must be 'reader', 'commenter', or 'writer'."
                })
                continue

            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email_address
            }
            
            try:
                result = drive_service.permissions().create(
                    fileId=spreadsheet_id,
                    body=permission,
                    sendNotificationEmail=send_notification,
                    fields='id'
                ).execute()
                successes.append({
                    'email_address': email_address, 
                    'role': role, 
                    'permissionId': result.get('id')
                })
            except Exception as e:
                # Try to provide a more informative error message
                error_details = str(e)
                if hasattr(e, 'content'):
                    try:
                        error_content = json.loads(e.content)
                        error_details = error_content.get('error', {}).get('message', error_details)
                    except json.JSONDecodeError:
                        pass # Keep the original error string
                failures.append({
                    'email_address': email_address,
                    'error': f"Failed to share: {error_details}"
                })
                
        return {"successes": successes, "failures": failures}