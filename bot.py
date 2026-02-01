from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import asyncio
import os
from PIL import Image

class WeChatHelperBot:
    def __init__(self):
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.playwright = None
        self.is_logged_in = False
        self.lock = asyncio.Lock()

    async def start(self, headless=True, user_data_dir=None):
        """Starts the browser with a persistent user data directory."""
        if user_data_dir is None:
            user_data_dir = os.path.join(os.getcwd(), "user_data")
            
        print(f"Starting browser (Headless: {headless}) with persistent context at {user_data_dir}")
        self.playwright = await async_playwright().start()
        
        # Ensure user_data directory exists
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Launch persistent context
        # user_agent matches a modern Mac Chrome to reduce bot detection
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        # We get the first page or create one
        if len(self.browser_context.pages) > 0:
            self.page = self.browser_context.pages[0]
        else:
            self.page = await self.browser_context.new_page()

        # EXTREME RESOURCE OPTIMIZATION: 
        # Block CSS, Fonts, and Media to save 80% bandwidth and reduce CPU/RAM
        async def handle_route(route):
            if route.request.resource_type in ["stylesheet", "font", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await self.page.route("**/*", handle_route)
        
        print("Navigating to https://filehelper.weixin.qq.com/ ...")
        await self.page.goto("https://filehelper.weixin.qq.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2) 
        print("Page loaded in lean mode.")

    async def save_session(self, path=None):
        """Persistent context saves session automatically, no manual action needed."""
        # We can still keep the method for compatibility but it's redundant now
        return True

    async def get_login_qr(self) -> bytes:
        """Returns the screenshot of the page (focused on QR code if possible)."""
        if not self.page:
            raise Exception("Browser not initialized")
        
        # Give it a moment to render the QR code
        await asyncio.sleep(2)
        
        # In a real scenario, we might want to crop to the QR code, 
        # but full page is safer for the first version to ensure the user sees everything.
        return await self.page.screenshot(full_page=False)

    async def save_screenshot(self, path: str) -> bool:
        """Saves a screenshot to the specified path."""
        if not self.page:
            return False
        try:
            await self.page.screenshot(path=path)
            return True
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return False

    async def check_login_status(self) -> bool:
        """Checks if the user has successfully logged in."""
        if not self.page:
            return False
            
        try:
            # After login, the page changes from .page__login to a chat interface
            # We look for the chat input area (contenteditable div) OR
            # absence of the login page class
            
            # Method 1: Check for chat input area
            # Method 1: Check for chat input area
            input_locator = self.page.locator("textarea.chat-panel__input-container, div[contenteditable='true']")
            if await input_locator.count() > 0 and await input_locator.is_visible():
                self.is_logged_in = True
                return True
            
            # Method 2: Check if login page is gone or showing logined state
            logined_page = self.page.locator(".page-logined, .chat-panel")
            if await logined_page.count() > 0:
                self.is_logged_in = True
                return True
                    
        except Exception as e:
            print(f"Login check error: {e}")
            pass
        
        self.is_logged_in = False
        return False

    async def send_text(self, message: str) -> bool:
        """Sends a text message."""
        if not self.is_logged_in:
            if not await self.check_login_status():
                return False
        
        async with self.lock:
            try:
                # 1. Find and click the input box
                # Primary: textarea used in FileHelper, Secondary: generic contenteditable
                box = self.page.locator("textarea.chat-panel__input-container, div[contenteditable='true']")
                await box.click()
                
                # 2. Type the message
                await box.fill(message)
                
                # 3. Press Enter or click Send button
                # Some versions might need a button click if Enter isn't enough
                send_button = self.page.locator("a.chat-send__button")
                if await send_button.count() > 0 and await send_button.is_visible():
                    await send_button.click()
                else:
                    await self.page.keyboard.press("Enter")
                
                return True
            except Exception as e:
                print(f"Error sending message: {e}")
                return False

    async def send_file(self, file_path: str) -> bool:
        """Sends a file."""
        if not self.is_logged_in:
            if not await self.check_login_status():
                return False

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False

        async with self.lock:
            try:
                # WeChat Web usually has a hidden file input for uploads.
                # We can try to assume there is an input[type='file'] on the page.
                # If not, we might need to click the '+' button first.
                
                # Strategy 1: Direct input setting (Most robust if input exists)
                # Found input.file-input#btnFile in the HTML
                file_input = self.page.locator("input#btnFile, input[type='file']")
                if await file_input.count() > 0:
                    await file_input.set_input_files(file_path)
                    # Often sends automatically in this version, but let's wait a bit
                    await asyncio.sleep(1)
                else:
                    # If no input, maybe we need to paste the file? (Clipboard API)
                    # Or use drag and drop buffer
                    # Drag and drop buffer:
                    # Create a drag data transfer
                    # This is complex. Let's stick to 'input' first.
                    print("No file input found. Trying to find upload button.")
                    return False

                # If the file is put in the chat box but not sent (e.g. requires another Enter)
                # We press enter just in case
                await asyncio.sleep(1)
                await self.page.keyboard.press("Enter")
                return True

            except Exception as e:
                print(f"Error sending file: {e}")
                # Fallback: Try to use the 'chooser' pattern if clicking the button works
                try: 
                    # Attempt to find common upload button selectors
                    # This is speculative without DOM access
                    # await self.page.click("api-selector-for-upload-button") 
                    pass
                except:
                    pass
                return False

    async def download_message_content(self, msg_id: str, save_path: str) -> bool:
        """Trigger a download for a specific message and save it."""
        if not self.page or not msg_id:
            return False
            
        async with self.lock:
            try:
                # 1. Find the element using the same logic as get_latest_messages
                found = await self.page.evaluate_handle("""(msgId) => {
                    const all = Array.from(document.querySelectorAll('.msg-item'));
                    for (let el of all) {
                        if (el.getAttribute('id') === msgId || el.getAttribute('data-id') === msgId) return el;
                        const img = el.querySelector('.msg-image img');
                        if (img && img.src.includes('MsgID=' + msgId)) return el;
                        
                        // Check custom 'stb_' ID
                        const index = all.indexOf(el);
                        const text = (el.querySelector('.msg-text, .msg-item__content')?.innerText || el.innerText || "").trim();
                        const stbId = `stb_${index}_${text.substring(0,10)}`;
                        if (stbId === msgId) return el;
                    }
                    return null;
                }""", msg_id)

                handle = found.as_element()
                if not handle:
                    print(f"Message element not found for {msg_id}")
                    return False

                # 2. Check type and attempt download
                # Case A: External file or image with a clear download button
                download_btn = await handle.query_selector(".icon__download")
                img_el = await handle.query_selector(".msg-image img")
                
                if download_btn:
                    print(f"Found download icon for {msg_id}, clicking...")
                    async with self.page.expect_download(timeout=15000) as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(save_path)
                    return True
                
                elif img_el:
                    # Case B: It's an image. In FileHelper, images might not have a download btn
                    # but we can download the src directly using the browser's session.
                    print(f"Image message detected for {msg_id}, downloading via JS fetch...")
                    img_src = await img_el.get_attribute("src")
                    if img_src:
                        # Use JS to fetch the image as a blob and convert to base64
                        # This avoids cross-origin/session issues because it's in-page
                        b64_data = await self.page.evaluate("""async (url) => {
                            const resp = await fetch(url);
                            const blob = await resp.blob();
                            return new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                                reader.readAsDataURL(blob);
                            });
                        }""", img_src)
                        
                        import base64
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))
                        print(f"Image saved to {save_path}")
                        return True
                
                # Case C: Fallback scroll and hover
                print(f"No direct download method for {msg_id}, trying hover fallback...")
                await handle.hover()
                await asyncio.sleep(1)
                final_btn = await handle.query_selector(".icon__download, .msg-file")
                if final_btn:
                    async with self.page.expect_download(timeout=15000) as download_info:
                        await final_btn.click()
                    download = await download_info.value
                    await download.save_as(save_path)
                    return True
                
                return False
            except Exception as e:
                print(f"Download execution error for {msg_id}: {e}")
                return False

    async def get_latest_messages(self, limit=10):
        """Scrapes the last few messages from the DOM."""
        if not self.page:
            return []
        
        try:
            # Execute JS to extract text from what look like message bubbles
            # WeChat FileHelper uses various class names for messages
            
            messages = await self.page.evaluate("""(limit) => {
                const container = document.querySelector('#chatBody, .chat-panel__body');
                if (!container) return [];

                const allElements = Array.from(container.querySelectorAll('.msg-item'));
                const messageElements = allElements.slice(-limit);
                
                return messageElements.map((el) => {
                    const globalIndex = allElements.indexOf(el); // Stable index within current DOM
                    const textEl = el.querySelector('.msg-text, .msg-item__content');
                    const imgEl = el.querySelector('.msg-image img');
                    const fileEl = el.querySelector('.msg-file');
                    
                    let msgType = 'text';
                    let content = textEl ? textEl.innerText.trim() : el.innerText.trim();
                    let fileName = null;
                    let hasDownload = !!el.querySelector('.icon__download');

                    if (imgEl) {
                        msgType = 'image';
                        content = '[Image]';
                    } else if (fileEl) {
                        msgType = 'file';
                        fileName = fileEl.querySelector('.msg-file__title')?.innerText || 'unknown_file';
                        content = `[File: ${fileName}]`;
                    }

                    // Generate a MORE stable ID: 
                    let msgId = el.getAttribute('id') || el.getAttribute('data-id');
                    if (!msgId && imgEl) {
                        msgId = imgEl.src.split('MsgID=')[1]?.split('&')[0];
                    }
                    if (!msgId) {
                        // Use global index and content preview for stability
                        msgId = `stb_${globalIndex}_${content.substring(0,10)}`;
                    }

                    return {
                        text: content,
                        type: msgType,
                        file_name: fileName,
                        has_download: hasDownload,
                        is_mine: el.classList.contains('mine'),
                        id: msgId,
                        html_preview: el.outerHTML.substring(0, 300)
                    };
                });
            }""", limit)
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    async def get_page_source(self) -> str:
        """Debug method to dump HTML if selectors change."""
        if self.page:
            return await self.page.content()
        return ""

    async def stop(self):
        print("Closing browser...")
        if hasattr(self, 'browser_context') and self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
