"""
Playwright test script to validate the application at http://localhost:5174/
"""
import asyncio
import sys
from playwright.async_api import async_playwright
from datetime import datetime

async def test_application():
    results = {
        "page_loaded": False,
        "screenshot_path": None,
        "elements_visible": {},
        "scroll_working": False,
        "errors": [],
        "warnings": [],
        "viewport_size": None,
        "page_title": None,
        "console_messages": [],
        "network_errors": []
    }

    async with async_playwright() as p:
        try:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Listen for console messages
            page.on("console", lambda msg: results["console_messages"].append({
                "type": msg.type,
                "text": msg.text
            }))

            # Listen for page errors
            page.on("pageerror", lambda err: results["errors"].append(f"Page error: {str(err)}"))

            # Listen for network failures
            page.on("requestfailed", lambda req: results["network_errors"].append({
                "url": req.url,
                "failure": req.failure
            }))

            print("Navigating to http://localhost:5174/...")

            # Navigate to the page with a longer timeout
            try:
                response = await page.goto("http://localhost:5174/", wait_until="networkidle", timeout=30000)
                results["page_loaded"] = response.ok if response else False
                print(f"Page loaded: {results['page_loaded']} (Status: {response.status if response else 'N/A'})")
            except Exception as e:
                results["errors"].append(f"Navigation error: {str(e)}")
                print(f"Navigation failed: {str(e)}")
                await browser.close()
                return results

            # Wait a bit for React to render
            await page.wait_for_timeout(3000)

            # Get page HTML to debug
            html_content = await page.content()
            results["html_length"] = len(html_content)

            # Check for any visible text on the page
            body_text = await page.locator('body').text_content()
            results["body_text_length"] = len(body_text) if body_text else 0

            # Get page title
            results["page_title"] = await page.title()
            print(f"Page title: {results['page_title']}")

            # Get viewport size
            results["viewport_size"] = page.viewport_size

            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/Users/inder/projects/mantrix-axis-ai/backend/screenshot_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            results["screenshot_path"] = screenshot_path
            print(f"Screenshot saved to: {screenshot_path}")
            print(f"HTML content length: {results['html_length']} characters")
            print(f"Body text length: {results['body_text_length']} characters")

            # Check for key UI elements
            print("\nChecking for key UI elements...")

            # Get all elements to see what's on the page
            all_divs = await page.locator('div').count()
            print(f"  Total div elements: {all_divs}")

            # Get all classes on the page to help identify elements
            all_classes = await page.evaluate("""
                () => {
                    const classes = new Set();
                    document.querySelectorAll('[class]').forEach(el => {
                        if (typeof el.className === 'string') {
                            el.className.split(' ').forEach(c => {
                                if (c.trim()) classes.add(c.trim());
                            });
                        }
                    });
                    return Array.from(classes).slice(0, 50);
                }
            """)
            results["page_classes"] = all_classes
            print(f"  Found {len(all_classes)} unique CSS classes")

            # Check for login/auth screen
            sign_in_button = await page.locator('button:has-text("Sign In")').count() > 0
            results["elements_visible"]["sign_in_button"] = sign_in_button
            print(f"  Sign In Button: {'✓ Found' if sign_in_button else '✗ Not found'}")

            if sign_in_button:
                results["warnings"].append("Application is showing authentication/login screen - main UI not accessible without login")

            # Sidebar
            sidebar_selector = '[class*="sidebar"], [class*="Sidebar"], aside, nav[class*="side"]'
            sidebar_visible = await page.locator(sidebar_selector).count() > 0
            results["elements_visible"]["sidebar"] = sidebar_visible
            print(f"  Sidebar: {'✓ Found' if sidebar_visible else '✗ Not found'}")

            # Top navigation bar
            nav_selectors = [
                'nav',
                '[class*="TopNav"]',
                '[class*="navbar"]',
                '[class*="NavBar"]',
                'header nav',
                'header'
            ]
            nav_visible = False
            for selector in nav_selectors:
                if await page.locator(selector).count() > 0:
                    nav_visible = True
                    break
            results["elements_visible"]["top_nav_bar"] = nav_visible
            print(f"  Top Nav Bar: {'✓ Found' if nav_visible else '✗ Not found'}")

            # Main content area
            main_selectors = ['main', '[role="main"]', '[class*="main"]', '[class*="content"]']
            main_visible = False
            for selector in main_selectors:
                if await page.locator(selector).count() > 0:
                    main_visible = True
                    break
            results["elements_visible"]["main_content"] = main_visible
            print(f"  Main Content: {'✓ Found' if main_visible else '✗ Not found'}")

            # Conversations list (likely in sidebar)
            conversation_selectors = [
                '[class*="conversation"]',
                '[class*="chat"]',
                '[class*="message"]',
                'ul li',
                '[role="list"]'
            ]
            conversations_visible = False
            conversations_element = None
            for selector in conversation_selectors:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    conversations_visible = True
                    conversations_element = locator.first
                    break
            results["elements_visible"]["conversations_list"] = conversations_visible
            print(f"  Conversations List: {'✓ Found' if conversations_visible else '✗ Not found'}")

            # Test scroll functionality in sidebar/conversations
            print("\nTesting scroll functionality...")
            if sidebar_visible or conversations_visible:
                try:
                    # Find scrollable container
                    scrollable_selectors = [
                        'aside',
                        '[class*="sidebar"]',
                        '[class*="conversation"]',
                        'nav[class*="side"]'
                    ]

                    for selector in scrollable_selectors:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            element = elements.first

                            # Check if element is scrollable
                            is_scrollable = await element.evaluate("""
                                (el) => {
                                    return el.scrollHeight > el.clientHeight;
                                }
                            """)

                            if is_scrollable:
                                # Get initial scroll position
                                initial_scroll = await element.evaluate("(el) => el.scrollTop")

                                # Scroll down
                                await element.evaluate("(el) => el.scrollTop = 100")
                                await page.wait_for_timeout(500)

                                # Get new scroll position
                                new_scroll = await element.evaluate("(el) => el.scrollTop")

                                results["scroll_working"] = new_scroll > initial_scroll
                                print(f"  Scroll test: {'✓ Working' if results['scroll_working'] else '✗ Not working'}")
                                print(f"    Initial position: {initial_scroll}, New position: {new_scroll}")
                                break
                    else:
                        results["warnings"].append("No scrollable container found or container not tall enough")
                        print("  Scroll test: ⚠ No scrollable container found")

                except Exception as e:
                    results["errors"].append(f"Scroll test error: {str(e)}")
                    print(f"  Scroll test error: {str(e)}")
            else:
                results["warnings"].append("Sidebar not found, cannot test scroll")
                print("  Scroll test: ⚠ Sidebar not found")

            # Check for any visible error messages on page
            error_selectors = [
                '[class*="error"]',
                '[class*="Error"]',
                '[role="alert"]',
                '.alert-danger'
            ]
            for selector in error_selectors:
                error_elements = page.locator(selector)
                count = await error_elements.count()
                if count > 0:
                    for i in range(count):
                        text = await error_elements.nth(i).text_content()
                        if text and text.strip():
                            results["warnings"].append(f"Error message on page: {text.strip()}")

            # Check for loading indicators (might indicate issues)
            loading_selectors = ['[class*="loading"]', '[class*="spinner"]', '.loader']
            for selector in loading_selectors:
                if await page.locator(selector).count() > 0:
                    results["warnings"].append(f"Loading indicator still visible: {selector}")

            await browser.close()

        except Exception as e:
            results["errors"].append(f"Test execution error: {str(e)}")
            print(f"Test execution error: {str(e)}")

    return results

async def main():
    print("=" * 80)
    print("PLAYWRIGHT APPLICATION VALIDATION TEST")
    print("=" * 80)
    print()

    results = await test_application()

    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    print(f"\n✓ PAGE LOAD STATUS: {'SUCCESS' if results['page_loaded'] else 'FAILED'}")
    print(f"✓ PAGE TITLE: {results['page_title']}")
    print(f"✓ VIEWPORT SIZE: {results['viewport_size']}")
    print(f"✓ SCREENSHOT: {results['screenshot_path']}")
    if 'html_length' in results:
        print(f"✓ HTML LENGTH: {results['html_length']} characters")
        print(f"✓ BODY TEXT LENGTH: {results['body_text_length']} characters")
    if 'page_classes' in results:
        print(f"\n--- PAGE CSS CLASSES (first 30) ---")
        for i, cls in enumerate(results['page_classes'][:30]):
            print(f"  {cls}")

    print("\n--- UI ELEMENTS VISIBILITY ---")
    for element, visible in results["elements_visible"].items():
        status = "✓ VISIBLE" if visible else "✗ NOT VISIBLE"
        print(f"  {element.replace('_', ' ').title()}: {status}")

    print(f"\n--- SCROLL FUNCTIONALITY ---")
    print(f"  Scroll Working: {'✓ YES' if results['scroll_working'] else '✗ NO'}")

    if results["errors"]:
        print("\n--- ERRORS ---")
        for error in results["errors"]:
            print(f"  ✗ {error}")

    if results["warnings"]:
        print("\n--- WARNINGS ---")
        for warning in results["warnings"]:
            print(f"  ⚠ {warning}")

    if results["network_errors"]:
        print("\n--- NETWORK ERRORS ---")
        for net_err in results["network_errors"]:
            print(f"  ✗ URL: {net_err['url']}")
            print(f"    Failure: {net_err['failure']}")

    if results["console_messages"]:
        print("\n--- CONSOLE MESSAGES (Last 10) ---")
        for msg in results["console_messages"][-10:]:
            print(f"  [{msg['type']}] {msg['text']}")

    print("\n" + "=" * 80)
    print()

    # Return exit code based on success
    return 0 if results["page_loaded"] and not results["errors"] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
