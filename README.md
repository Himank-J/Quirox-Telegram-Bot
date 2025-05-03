# Quirox Telegram Bot Backend

This project provides the backend services for the Quirox Telegram Bot, featuring an AI agent capable of interacting with various tools like Google Sheets, Gmail (currently commented out), and web search via DuckDuckGo. It uses the Model Context Protocol (MCP) to manage communication between the AI model (Google Gemini) and the available tools. The backend is exposed via a FastAPI web server.

## Demo

[![Watch how Mecro works](https://img.youtube.com/vi/QLJ6gHT2mnI/0.jpg)](https://www.youtube.com/watch?v=sJX0b5UoOCY)

## Features

*   **AI Agent:** Uses Google Gemini (Flash model) for reasoning and task execution.
*   **Tool Integration:**
    *   **Google Sheets:** Create spreadsheets, read/write data, manage sheets (list, copy, rename), share. Uses `helpers/ghseet.py` (via `GoogleSheetsService`).
    *   **Web Search:** Search the web using DuckDuckGo (`helpers/search_tools.py`).
    *   **Web Content Fetching:** Fetch and parse text content from URLs (`helpers/search_tools.py`).
    *   **(Experimental/Disabled) Gmail:** Functions for sending, reading, and managing emails are present in `helpers/gmail_tools.py` but appear commented out in `mcp_server.py`.
*   **MCP Framework:**
    *   `mcp_server.py`: Runs the MCP server, exposing tools (Sheets, Search, Fetch) to the AI model.
    *   `mcp_client.py`: Communicates with the MCP server, sends user queries to the Gemini model, handles tool calls, and manages the conversation flow.
*   **FastAPI Interface:**
    *   `main.py`: Starts a FastAPI web server, providing a `/chat` endpoint to interact with the AI agent via HTTP requests.

## Project Structure
├── README.md # This file
├── .env # Environment variables (API keys, paths) - MUST BE CREATED
├── .gitignore # Git ignore patterns
├── requirements.txt # Python dependencies
├── main.py # FastAPI application entry point
├── mcp_client.py # MCP client logic interacting with Gemini and MCP Server
├── mcp_server.py # MCP server exposing tools
├── helpers/ # Directory for helper modules and tools
│ ├── config.py # Loads Gemini API key
│ ├── gsheet_tools.py # (Potentially older) MCP tool definitions for Google Sheets
│ ├── ghseet.py # Standalone GoogleSheetsService class
│ ├── gmail_tools.py # Gmail service class and MCP tool definitions (currently unused)
│ ├── search_tools.py # DuckDuckGo search and Web Content Fetcher classes
│ └── init.py
├── telegram_bot/ # (Empty/Placeholder?) Directory for Telegram bot specific code
└── bot/ # (Empty/Placeholder?) Another potential bot directory
```

## Setup

### 1. Prerequisites

*   Python 3.8+
*   Access to Google Cloud Platform for Sheets/Drive API and potentially Gmail API.
*   Google Gemini API Key.

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file in the root directory by copying `.env.example` (if it existed) or creating it from scratch. Add the following variables:

```dotenv
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key

# Google Cloud Credentials (Choose ONE method: Service Account or OAuth)

# Method 1: Service Account (Recommended for servers)
# Path to your service account JSON key file
SERVICE_ACCOUNT_PATH=path/to/your/service_account.json
# Optional: Google Drive Folder ID to work within
DRIVE_FOLDER_ID=your_google_drive_folder_id

# Method 2: OAuth 2.0 (Requires user interaction for the first run)
# Path to your OAuth client secrets file (credentials.json)
CREDENTIALS_PATH=path/to/your/credentials.json
# Path where the OAuth token will be stored after authorization
TOKEN_PATH=token.json # Keep default unless you have a reason to change

# Method 3: Base64 Encoded Service Account Config (Alternative)
# CREDENTIALS_CONFIG=your_base64_encoded_service_account_json_string
```

**Important:**
*   Ensure the Google Sheets API and Google Drive API are enabled in your Google Cloud project.
*   If using OAuth (`CREDENTIALS_PATH`), the first time `mcp_server.py` (or code using `GoogleSheetsService`/`GmailService`) runs, it will open a browser window for you to authorize the application. The resulting `token.json` will be saved.
*   If using a Service Account (`SERVICE_ACCOUNT_PATH`), ensure the service account email has been granted appropriate permissions (e.g., Editor) on the target Google Sheets or Drive Folder.

### 5. Google Cloud Authentication Setup

*   **Service Account:**
    1.  Go to the Google Cloud Console -> IAM & Admin -> Service Accounts.
    2.  Create a service account or use an existing one.
    3.  Create a key (JSON format) for the service account and download it.
    4.  Set `SERVICE_ACCOUNT_PATH` in `.env` to the path of the downloaded JSON file.
    5.  Share any specific Google Drive folders or Sheets with the service account's email address.
*   **OAuth 2.0:**
    1.  Go to Google Cloud Console -> APIs & Services -> Credentials.
    2.  Create "OAuth 2.0 Client ID" of type "Desktop app".
    3.  Download the client secrets JSON file.
    4.  Rename it to `credentials.json` (or update `CREDENTIALS_PATH` in `.env`).

## Usage

The application consists of two main parts that need to run concurrently: the MCP Server and the FastAPI frontend (which uses the MCP Client).

### 1. Run the MCP Server

This server provides the tools (Sheets, Search) to the AI.

```bash
python mcp_server.py
```

Keep this terminal window open.

### 2. Run the FastAPI Application

This starts the web server that listens for chat requests.

```bash
python main.py
# or using uvicorn directly for more options:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Interact via API

You can now send POST requests to the `/chat` endpoint:

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Create an excel sheet named '\''Test Sheet'\'' and add the headers Name, Age, City in the first row."}'
```

The response will contain the final answer generated by the AI after potentially interacting with the tools via the MCP server.

## Key Modules (`helpers/`)

*   `config.py`: Loads the `GEMINI_API_KEY` from the environment.
*   `search_tools.py`: Contains `DuckDuckGoSearcher` for web searches and `WebContentFetcher` for retrieving content from URLs. Includes rate limiting.
*   `ghseet.py`: Implements `GoogleSheetsService` providing a class-based interface to Google Sheets and Drive APIs (Create, Read, Update, Batch Update, Add Rows/Cols, List Sheets, Share, etc.). Handles authentication internally.
*   `gmail_tools.py`: Implements `GmailService` (similar structure to `GoogleSheetsService`) for Gmail operations. Contains MCP tool definitions for email tasks, though currently seems disabled in the `mcp_server.py`.
*   `gsheet_tools.py`: Contains older, function-based MCP tool definitions for Google Sheets, likely superseded by `ghseet.py`.

## Dependencies

Key dependencies include:

*   `fastapi`, `uvicorn`: For the web server.
*   `mcp`: Model Context Protocol library.
*   `google-api-python-client`, `google-auth-oauthlib`, `google-auth`: Google API libraries.
*   `google-generativeai`: Google Gemini client library.
*   `python-dotenv`: For loading environment variables.
*   `httpx`, `beautifulsoup4`: For web search and content fetching.
*   `rich`: For formatted console output.

See `requirements.txt` for the full list.