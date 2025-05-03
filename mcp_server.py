import sys, os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from typing import List
from helpers.gmail_tools import GmailService
from rich.console import Console
from rich.panel import Panel
import traceback, logging
from helpers.search_tools import DuckDuckGoSearcher, WebContentFetcher
from helpers.ghseet import GoogleSheetsService
from dotenv import load_dotenv

load_dotenv()   
console = Console(stderr=True)

mcp = FastMCP("web-search-agent")
searcher = DuckDuckGoSearcher()
fetcher = WebContentFetcher()
sheet_service = GoogleSheetsService(
    token_path=os.environ.get('TOKEN_PATH'),
    credentials_path=os.environ.get('CREDENTIALS_PATH'),
    drive_folder_id=os.environ.get('DRIVE_FOLDER_ID')
)

# Initialize Gmail service
# gmail_service = GmailService(os.environ.get('CREDENTIALS_PATH'), os.environ.get('TOKEN_PATH'))

@mcp.tool()
async def search(query: str) -> str:
    """
    Search DuckDuckGo for user query and return formatted results.
    """
    try:

        results = await searcher.search(query)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"

@mcp.tool()
async def fetch_content(url: str) -> str:
    """
    Fetch and parse content from a webpage URL.

    Args:
        url: The webpage URL to fetch content from
    """
    return await fetcher.fetch_and_parse(url)

@mcp.tool()
def create_excel_sheet(title: str) -> str:
    """
    Create a new excel sheet in the Google Drive folder.

    Args:
        title: The title of the excel sheet
    """
    return sheet_service.create_spreadsheet(title)

@mcp.tool()
def bulk_update_cells(spreadsheet_id: str, sheet: str, ranges) -> str:
    """
    Bulk update cells in a spreadsheet.

    Args:
        The ID of the spreadsheet (found in the URL)
        The name of the sheet
        Dictionary mapping range strings to 2D arrays of values
        e.g., {'A1:B2': [[1, 2], [3, 4]], 'D1:E2': [['a', 'b'], ['c', 'd']]}
    """
    if isinstance(ranges, str):
        ranges = eval(ranges)
    return sheet_service.batch_update_cells(spreadsheet_id, sheet, ranges)

@mcp.tool()
def share_excel_sheet(spreadsheet_id: str, recipients) -> str:
    """
    Share a spreadsheet with a user.

    Args:
        spreadsheet_id: The ID of the spreadsheet to share.
        recipients: A list of dictionaries, each containing 'email_address' and 'role'.
                    The role should be one always be reader.
                    Example: [
                        {'email_address': 'user1@example.com', 'role': 'reader'},
                        {'email_address': 'user2@example.com', 'role': 'reader'}
                    ]
    """
    if isinstance(recipients, str):
        recipients = eval(recipients)
    return sheet_service.share_spreadsheet(spreadsheet_id, recipients)

if __name__ == "__main__":
    print("STARTING ...")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run() 
    else:
        mcp.run(transport="stdio") 