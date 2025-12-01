import os
import time
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def redeploy_app(target_url="https://containers.back4app.com/apps/8b776070-a50c-4390-a92f-4e41d9cd9f9f"):
    """
    自动登录 Back4App 并点击容器页面的 "Redeploy App" 按钮。
    优先使用 Cookie (_hjSessionUser_1071997 + cf_clearance)，失败回退邮箱密码登录。
    支持异步渲染和 iframe 内按钮。
    """
    cf_clearance = os.environ.get("CF_CLEARANCE")
    hj_cookie = os.environ.get("BACK4APP_COOKIE")  # _hjSessionUser_1071997
    email = os.environ.get("BACK4APP_EMAIL")
    password = os.environ.get("BACK4APP_PASSWORD")

    if not ((cf_clearance and hj_cookie) or (email and password)):
        print("❌ 缺少登录凭据，请设置 CF_CLEARANCE + BACK4APP_COOKIE 或 BACK4APP_EMAIL + BACK4APP_PASSWORD")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(90000)

        try:
            # === 1. 优先使用 Cookie 登录 ===
            if cf_clearance and hj_cookie:
                print("尝试使用 Cookie 登录...")
                cookies = [
                    {
                        "name": "cf_clearance",
                        "value": cf_clearance,
                        "domain": "www.back4app.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                    },
                    {
                        "name": "_hjSessionUser_1071997",
                        "value": hj_cookie,
                        "domain": "www.back4app.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                    },
                ]
                page.context.add_cookies(cookies)
                page.goto(target_url, wait_until="networkidle")
                page.wait_for_timeout(5000)

                if "login" not in page.url:
                    print("✅ Cookie 登录成功！")
                else:
                    print("⚠ Cookie 登录失败，将尝试邮箱密码登录。")
                    page.context.clear_cookies()
                    cf_clearance = hj_cookie = None

            # === 2. Cookie 失败或未提供，邮箱密码登录 ===
            if not (cf_clearance and hj_cookie):
                if not (email and password):
                    print("❌ 无法使用 Cookie，且未提供邮箱密码，无法登录。")
                    browser.close()
                    return False

                login_url = "https://www.back4app.com/login"
                page.goto(login_url, wait_until="networkidle")
                page.wait_for_timeout(5000)

                # 关闭可能的 cookie 弹窗
                if page.locator('button:has-text("Accept")').count() > 0:
                    page.locator('button:has-text("Accept")').click()

                page.wait_for_selector('input[name="email"]')
                page.wait_for_selector('input[name="password"]')
                page.fill('input[name="email"]', email)
                page.fill('input[name="password"]', password)

                with page.expect_navigation(wait_until="networkidle", timeout=60000):
                    page.locator('button[type="submit"]').click()

                if "login" in page.url:
                    print("❌ 邮箱密码登录失败")
                    page.screenshot(path="login_fail.png")
                    browser.close()
                    return False
                else:
                    print("✅ 邮箱密码登录成功！")

            # === 3. 确保进入目标容器页面 ===
            if page.url != target_url:
                page.goto(target_url, wait_until="networkidle")
                page.wait_for_timeout(5000)
                if "login" in page.url:
                    print("❌ 导航失败，可能需要重新登录")
                    page.screenshot(path="container_nav_fail.png")
                    browser.close()
                    return False

            # === 4. 查找并点击 Redeploy App 按钮 ===
            print("寻找 'Redeploy App' 按钮...")
            found = False

            # 先尝试主页面
            try:
                btn = page.locator('button', has_text=re.compile("Redeploy App", re.I))
                btn.wait_for(state="visible", timeout=60000)
                btn.click()
                time.sleep(5)
                print("🎉 Redeploy App 点击成功（主页面）！")
                found = True
            except PlaywrightTimeoutError:
                print("⚠ 未在主页面找到按钮，尝试 iframe 内...")

            # 尝试 iframe
            if not found:
                for frame in page.frames:
                    try:
                        btn = frame.locator('button', has_text=re.compile("Redeploy App", re.I))
                        btn.wait_for(state="visible", timeout=30000)
                        btn.click()
                        time.sleep(5)
                        print("🎉 Redeploy App 点击成功（iframe 内）！")
                        found = True
                        break
                    except PlaywrightTimeoutError:
                        continue

            if not found:
                print("❌ 未找到 'Redeploy App' 按钮")
                page.screenshot(path="redeploy_button_not_found.png")
                browser.close()
                return False

            browser.close()
            return True

        exc
