"""LinkedIn auto-posting bot using Playwright with 2FA support."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


# Path to store browser user data (for persistent logged-in session)
BROWSER_USER_DATA = Path(__file__).parent / ".linkedin_session"


async def wait_for_login(page, timeout_ms: int = 180000) -> bool:
    """
    Wait for user to complete login (including 2FA if required).
    
    Args:
        page: Playwright page object
        timeout_ms: Maximum time to wait in milliseconds
        
    Returns:
        True if login successful, False if timeout
    """
    print("⏳ Waiting for login/2FA completion...")
    print("📱 If 2FA code is required, please enter it manually in the browser")
    
    try:
        # Wait for URL to change away from login/checkpoint pages
        await page.wait_for_function(
            """() => {
                const url = window.location.href;
                return !url.includes('login') && !url.includes('checkpoint');
            }""",
            timeout=timeout_ms
        )
        print("✅ Login/2FA completed!")
        return True
        
    except Exception as e:
        print(f"⚠️ Login timeout after {timeout_ms/1000:.0f}s: {e}")
        return False


async def post_to_linkedin(content: str, headless: bool = False) -> bool:
    """
    Post content to LinkedIn using Playwright.

    Args:
        content: The LinkedIn post content to publish
        headless: Run browser in headless mode (default False for easier login)

    Returns:
        True if post was successful, False otherwise
    """
    context = None
    
    try:
        async with async_playwright() as p:
            # Launch Chromium with persistent user data directory
            # This allows reusing existing logged-in sessions
            print("🌐 Launching browser with persistent session...")
            print(f"📁 Session directory: {BROWSER_USER_DATA.absolute()}")
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_USER_DATA.absolute()),
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
                ignore_default_args=["--enable-automation"],
                timeout=180000,  # 3 minutes default timeout
            )

            page = context.pages[0] if context.pages else await context.new_page()

            # Set default timeout for all operations
            page.set_default_timeout(180000)

            # Navigate to LinkedIn feed
            print("🔗 Navigating to LinkedIn feed...")
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            
            # Wait for page to stabilize
            await page.wait_for_timeout(5000)

            # Check current URL
            current_url = page.url
            print(f"📍 Current URL: {current_url}")

            # Check if we're on login/checkpoint page (including 2FA)
            if "login" in current_url or "checkpoint" in current_url:
                print("⚠️  Login or 2FA verification detected...")
                print("📱 Please complete login and enter any 2FA code manually")
                
                # Wait for login/2FA to complete
                login_success = await wait_for_login(page, timeout_ms=180000)
                
                if not login_success:
                    print("⚠️  Login not completed within timeout")
                    print("🔄 Waiting additional 60 seconds for manual completion...")
                    await page.wait_for_timeout(60000)
                    
                    # Check URL again
                    current_url = page.url
                    if "login" in current_url or "checkpoint" in current_url:
                        print("❌ Still on login page. Please run again after logging in.")
                        print("📍 Current URL:", current_url)
                        # Keep browser open for user to complete manually
                        print("⏳ Keeping browser open for 30 more seconds...")
                        await page.wait_for_timeout(30000)
                        return False

                # Re-check URL after login
                current_url = page.url
                print(f"📍 Current URL after login: {current_url}")

            # Ensure we're on the feed page
            if "feed" not in current_url:
                print("🔄 Navigating to feed page...")
                await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
                
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                # Check if redirected back to login
                if "login" in current_url or "checkpoint" in current_url:
                    print("⚠️  Redirected to login. Please complete authentication...")
                    login_success = await wait_for_login(page, timeout_ms=180000)
                    
                    if not login_success:
                        print("❌ Authentication not completed")
                        return False
                    
                    # Navigate to feed again after successful login
                    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)

            # Wait for the post button to appear
            print("📝 Looking for 'Start a post' button...")
            
            post_button = None
            
            # Strategy 1: Button with text "Start a post"
            try:
                post_button = await page.wait_for_selector(
                    "button:has-text('Start a post')",
                    state="visible",
                    timeout=60000
                )
                print("✅ Found 'Start a post' button (text selector)")
            except Exception:
                pass

            # Strategy 2: Button containing "Start"
            if not post_button:
                try:
                    post_button = await page.wait_for_selector(
                        "button:has-text('Start')",
                        state="visible",
                        timeout=30000
                    )
                    print("✅ Found 'Start' button")
                except Exception:
                    pass

            # Strategy 3: Share box trigger by class
            if not post_button:
                try:
                    post_button = await page.wait_for_selector(
                        ".share-box-feed-entry__trigger",
                        state="visible",
                        timeout=30000
                    )
                    print("✅ Found share box trigger (class selector)")
                except Exception:
                    pass

            # Strategy 4: Aria label
            if not post_button:
                try:
                    post_button = await page.wait_for_selector(
                        "[aria-label='Start a post']",
                        state="visible",
                        timeout=30000
                    )
                    print("✅ Found share box trigger (aria-label)")
                except Exception:
                    pass

            if not post_button:
                print("❌ Could not find 'Start a post' button")
                print(f"📍 Current URL: {page.url}")
                print("⏳ Keeping browser open for manual action...")
                await page.wait_for_timeout(30000)
                return False

            # Click the post button
            await post_button.click()
            print("✅ Clicked 'Start a post'")

            # Wait for post dialog to open
            print("⏳ Waiting for post dialog to open...")
            await page.wait_for_timeout(5000)

            # Find and fill the post content area
            print("✍️ Writing post content...")
            
            content_filled = False
            
            # Strategy 1: Contenteditable div
            try:
                content_area = await page.wait_for_selector(
                    "div[contenteditable='true']",
                    state="visible",
                    timeout=30000
                )
                await content_area.fill(content)
                content_filled = True
                print("✅ Filled content (contenteditable)")
            except Exception:
                pass

            # Strategy 2: ProseMirror editor
            if not content_filled:
                try:
                    content_area = await page.wait_for_selector(
                        ".ProseMirror",
                        state="visible",
                        timeout=30000
                    )
                    await content_area.fill(content)
                    content_filled = True
                    print("✅ Filled content (ProseMirror)")
                except Exception:
                    pass

            # Strategy 3: Aria label input
            if not content_filled:
                try:
                    await page.fill(
                        "[aria-label='What do you want to talk about?']",
                        content
                    )
                    content_filled = True
                    print("✅ Filled content (aria-label)")
                except Exception:
                    pass

            # Strategy 4: Keyboard fallback
            if not content_filled:
                print("⌨️ Using keyboard fallback...")
                await page.keyboard.press("Tab")
                await page.keyboard.press("Tab")
                await page.keyboard.type(content, delay=50)
                content_filled = True
                print("✅ Filled content (keyboard)")

            await page.wait_for_timeout(3000)

            # Click the Post button
            print("🚀 Looking for 'Post' button...")
            
            post_clicked = False
            post_button_selectors = [
                "button:has-text('Post')",
                "button[aria-label='Post']",
                ".share-post-button",
            ]
            
            for selector in post_button_selectors:
                try:
                    post_btn = await page.wait_for_selector(
                        selector,
                        state="visible",
                        timeout=10000
                    )
                    await post_btn.click()
                    print("✅ Post button clicked!")
                    post_clicked = True
                    break
                except Exception:
                    continue

            if not post_clicked:
                print("⚠️ Could not find 'Post' button - you may need to click it manually")
                print("⏳ Waiting 30 seconds for manual review...")
                await page.wait_for_timeout(30000)
            else:
                # Wait for post to be published
                print("⏳ Waiting for post to publish...")
                await page.wait_for_timeout(5000)
                print("✅ Post published successfully!")

            return True

    except Exception as e:
        print(f"❌ Error posting to LinkedIn: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Note: NOT closing browser on error - user can recover


async def main():
    """Main entry point for the LinkedIn bot."""
    from agents.linkedin_agent import generate_linkedin_post

    # Generate content
    topic = "AI agents for productivity"
    content = generate_linkedin_post(topic)
    
    print("📄 Generated LinkedIn post:")
    print("=" * 60)
    print(content)
    print("=" * 60)
    print()

    # Post to LinkedIn
    success = await post_to_linkedin(content, headless=False)
    
    if success:
        print("🎉 LinkedIn posting workflow completed!")
    else:
        print("⚠️ LinkedIn posting encountered issues")


if __name__ == "__main__":
    asyncio.run(main())
