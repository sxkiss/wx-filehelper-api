from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
import bot
import os
import shutil
import tempfile
import asyncio

# Global bot instance
import processor

# Create downloads directory
DOWNLOAD_DIR = "/Users/aq/Desktop/myproject/wechat-filehelper-api/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Global bot instance
wechat_bot = bot.WeChatHelperBot()
command_processor = processor.CommandProcessor(wechat_bot)
listener_task = None

async def background_listener():
    """Polls for new messages and processes them."""
    # Use a set to track processed message IDs or content to avoid dupes
    # Since we added 'id' extraction, we can try to use it.
    processed_ids = set()
    sent_buffer = []  # Keep track of last ~10 sent messages to avoid loops
    print("Background listener started.")
    
    while True:
        try:
            # If not logged in, try to detect if login happened
            if not wechat_bot.is_logged_in:
                if await wechat_bot.check_login_status():
                    print("Login detected by background listener!")
            
            if wechat_bot.is_logged_in:
                messages = await wechat_bot.get_latest_messages(limit=8)
                
                # Process oldest first
                for msg in reversed(messages):
                    content = msg.get('text', '').strip()
                    msg_id = msg.get('id')
                    
                    # Deduplication
                    unique_key = msg_id if msg_id else content
                    if not unique_key or unique_key in processed_ids:
                        continue
                        
                    # Loop prevention: If content matches something we just sent, skip it
                    if content in sent_buffer:
                        processed_ids.add(unique_key)
                        continue

                    print(f"New message detected: {content[:30]}...")
                    processed_ids.add(unique_key)
                    
                    # Auto-download for images and files
                    if msg.get('type') in ['image', 'file']:
                        file_name = msg.get('file_name') or f"download_{msg_id or unique_key[:8]}"
                        if msg.get('type') == 'image' and not file_name.endswith('.png'):
                            file_name += ".png"
                        
                        save_path = os.path.join(DOWNLOAD_DIR, file_name)
                        print(f"Auto-downloading {msg.get('type')}: {file_name}")
                        success = await wechat_bot.download_message_content(msg_id or unique_key, save_path)
                        if success:
                            reply = f"✅ 已成功接收保存: {file_name}"
                            await wechat_bot.send_text(reply)
                            sent_buffer.append(reply)
                            if len(sent_buffer) > 10: sent_buffer.pop(0)

                    # Standard command processing
                    reply = await command_processor.process(msg)
                    if reply:
                        print(f"Replying: {reply}")
                        await wechat_bot.send_text(reply)
                        sent_buffer.append(reply)
                        if len(sent_buffer) > 10: sent_buffer.pop(0)
            
        except Exception as e:
            print(f"Listener error: {e}")
        
        await asyncio.sleep(2) # Poll every 2 seconds

async def periodic_session_saver():
    """Periodically saves session state."""
    while True:
        await asyncio.sleep(60)  # Save every 60 seconds
        try:
            if wechat_bot.is_logged_in:
                await wechat_bot.save_session()
        except Exception as e:
            print(f"Session save error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Now that we have a persistent session, we can run headless.
    await wechat_bot.start(headless=True)
    
    # Start background tasks
    global listener_task
    listener_task = asyncio.create_task(background_listener())
    session_saver_task = asyncio.create_task(periodic_session_saver())
    
    yield
    
    # Shutdown
    for task in [listener_task, session_saver_task]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
    await wechat_bot.stop()

app = FastAPI(lifespan=lifespan, title="WeChat FileHelper API")

# Mount downloads directory to be accessible via /static
app.mount("/static", StaticFiles(directory=DOWNLOAD_DIR), name="static")

class Message(BaseModel):
    content: str
    
@app.get("/")
async def root():
    """Check service status and login state."""
    is_logged_in = await wechat_bot.check_login_status()
    return {
        "service": "WeChat FileHelper IPC",
        "logged_in": is_logged_in,
        "instructions": "Go to /qr to see the login code. Send POST to /send to send text. POST /upload to send file."
    }

@app.get("/qr")
async def get_qr():
    """Get the login QR code as an image."""
    try:
        # If already logged in, inform the user
        if await wechat_bot.check_login_status():
             return Response(content="Already logged in. You can now use /send.", media_type="text/plain")
        
        png_bytes = await wechat_bot.get_login_qr()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send")
async def send_message(msg: Message):
    """Send a message to yourself (File Transfer Assistant)."""
    # Double check login status before acting
    is_logged_in = await wechat_bot.check_login_status()
    if not is_logged_in:
        raise HTTPException(
            status_code=401, 
            detail="Session not active. Please open the browser window or scan the QR code at /qr"
        )
    
    success = await wechat_bot.send_text(msg.content)
    if success:
        return {"status": "sent", "content": msg.content}
    else:
        raise HTTPException(
            status_code=500, 
            detail="Failed to send message. Browser interaction failed."
        )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to yourself."""
    is_logged_in = await wechat_bot.check_login_status()
    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Session not active.")

    # Save uploaded file to temp
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        success = await wechat_bot.send_file(tmp_path)
        if success:
            return {"status": "sent", "filename": file.filename}
        else:
            raise HTTPException(status_code=500, detail="Failed to send file via browser.")
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/messages")
async def get_messages(limit: int = 10):
    """Get recent messages from the chat window."""
    messages = await wechat_bot.get_latest_messages(limit)
    return {"messages": messages}

@app.post("/save_session")
async def trigger_save_session():
    """Force save session state."""
    success = await wechat_bot.save_session()
    if success:
        return {"status": "saved"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save session")

@app.get("/downloads")
async def list_downloads():
    """List all received files."""
    files = os.listdir(DOWNLOAD_DIR)
    return {
        "files": files,
        "base_url": "/static/"
    }

@app.get("/debug_html")
async def debug_html():
    """Dump current page HTML for debugging selectors."""
    source = await wechat_bot.get_page_source()
    return Response(content=source, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0 to be accessible
    uvicorn.run(app, host="0.0.0.0", port=8000)
