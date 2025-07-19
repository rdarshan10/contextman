# server/test_playwright.py

import asyncio
import sys

# --- FIX FOR WINDOWS ASYNCIO BUG ---
# We apply the same fix here to test it in isolation.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# --- END FIX ---

from playwright.async_api import async_playwright

async def main():
    print("Starting Playwright test...")
    try:
        async with async_playwright() as p:
            print("Launching browser...")
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            print("Navigating to example.com...")
            await page.goto("http://example.com")
            
            title = await page.title()
            print(f"Successfully retrieved page title: '{title}'")
            
            await browser.close()
            print("Browser closed. Test successful!")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # In Python 3.7+, this is the standard way to run the main async function.
    asyncio.run(main())