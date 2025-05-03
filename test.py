from helpers.search_tools import DuckDuckGoSearcher
from helpers.ghseet import GoogleSheetsService
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
searcher = DuckDuckGoSearcher()
results = asyncio.run(searcher.search("Lakers"))
parsed_results = searcher.format_results_for_llm(results)
print(parsed_results)

# service = GoogleSheetsService(
#     token_path=os.environ.get('TOKEN_PATH', 'token.json'),
#     credentials_path=os.environ.get('CREDENTIALS_PATH', 'credentials.json'),
#     drive_folder_id=os.environ.get('DRIVE_FOLDER_ID')
# )
# spreadsheet = service.create_spreadsheet("Test Spreadsheet")
# print(spreadsheet)

# ranges =  {'A1:B2': [[1, 2], [3, 4]], 'D1:E2': [['a', 'b'], ['c', 'd']]}
# service.batch_update_cells(spreadsheet['spreadsheetId'], 'Sheet1', ranges)