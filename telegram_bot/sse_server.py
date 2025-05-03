from fastapi import FastAPI, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import asyncio
import json
import os
from fastmcp import FastMCP
#from fastmcp.models import ToolCall
#from fastmcp.types import ToolCall

def load_telegram_token():
    try:
        with open(".telegram_token.txt", "r") as f:
            token = f.read().strip()
            print("DEBUG: Token loaded successfully")
            print(f"DEBUG: Token length: {len(token)}")
            return token
    except Exception as e:
        print(f"DEBUG: Error loading token: {e}")
        raise

mcp: FastMCP = FastMCP("TelegramApp")
app = FastAPI()
messages = asyncio.Queue()
pending_telegram_messages = asyncio.Queue()

TELEGRAM_TOKEN = load_telegram_token()

last_chat_id = None

# Handler for incoming Telegram messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_chat_id
    text = update.message.text
    old_chat_id = last_chat_id
    last_chat_id = update.message.chat_id
    print(f"DEBUG: Chat ID updated from {old_chat_id} to {last_chat_id}")
    print(f"DEBUG: Message received: {text}")
    await pending_telegram_messages.put({"user_id": last_chat_id, "text": text})

@app.on_event("startup")
async def startup_event():
    global last_chat_id
    print(f"DEBUG: Initial last_chat_id state: {last_chat_id}")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.initialize()
    asyncio.create_task(application.start())
    asyncio.create_task(application.updater.start_polling())


@mcp.tool(name="ask-anything")
async def send_telegram_message(text: str) -> str:
    """
    Send a message to the Telegram bot's chat.

    Arguments:
        text (str): The message to send.

    Usage:
        send-telegram-message|text="Hello from the agent!"

    Returns:
        str: Confirmation message with details of the sent message
    """
    global last_chat_id
    if not last_chat_id:
        print("[telegram_sse_server.py][send_telegram_message] DEBUG: No chat_id available")
        return "No chat_id available"
    
    print(f"[telegram_sse_server.py][send_telegram_message] DEBUG: Attempting to send message:")
    print(f"[telegram_sse_server.py][send_telegram_message] - Chat ID: {last_chat_id}")
    print(f"[telegram_sse_server.py][send_telegram_message] - Message: {text}")
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        await application.bot.send_message(
            chat_id=last_chat_id, 
            text=text
        )
        print(f"[telegram_sse_server.py][send_telegram_message] DEBUG: Message successfully sent")
        return f"Message sent successfully to {last_chat_id}: {text}"
    except Exception as e:
        print(f"[telegram_sse_server.py][send_telegram_message] DEBUG: Error details:")
        print(f"[telegram_sse_server.py][send_telegram_message] - Error type: {type(e).__name__}")
        print(f"[telegram_sse_server.py][send_telegram_message] - Error message: {str(e)}")
        print(f"[telegram_sse_server.py][send_telegram_message] - Chat ID type: {type(last_chat_id)}")
        return f"Error sending message: {str(e)}"

@mcp.tool(name="get-next-telegram-message")
async def get_next_telegram_message() -> dict:
    """
    Fetch the next pending Telegram message.

    Usage:
        get-next-telegram-message

    Returns:
        dict: {"user_id": int, "text": str}
    """
    try:
        print(f"DEBUG: Current queue size: {pending_telegram_messages.qsize()}")
        msg = await pending_telegram_messages.get()
        print(f"DEBUG: Retrieved message: {msg}")
        return msg
    except Exception as e:
        print(f"DEBUG: Queue error: {repr(e)}")
        raise

@app.get("/test")
async def test():
    """Test endpoint to verify the server is running."""
    return {"message": "Hello from Telegram SSE MCP server!"}

@app.get("/list_tools")
async def list_tools():
    # List all registered MCP tools
    tools = mcp.list_tools()
    # Convert to dict if needed
    tools_dict = [t.dict() if hasattr(t, "dict") else t for t in tools]
    return JSONResponse(content=tools_dict)

app.mount("/", mcp.sse_app())