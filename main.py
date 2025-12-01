import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def redeploy_app(target_url="https://containers.back4app.com/apps/8b776070-a50c-4390-a92f-4e41d9cd9f9f"):
    """
    自动登录 Back4App 并点击容器页面的 "Redeploy App" 按钮。
    优先使用 _hjSessionUser_1071997 Cookie，如果失败再使用邮箱密码登录。
    """

    b4a_cookie = os.environ.get("BACK4APP_COOKIE")
    b4a_email = os.environ.get("BACK4APP_EMAIL")
    b4a_password = os.environ.get("BACK4APP_PASSWORD")

    if not (b4a_cookie or (b4a_email and b4a_password)):
        print("❌ 缺少登录凭据。请设置 BACK4APP_COOKIE 或 BACK4APP_EMAIL 和 BACK4APP_PASSWORD。")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(90000)

        try:
            # === 1. 优先使用 Cookie 登录 ===
            if b4a_cookie:
                print("尝试使用 COOKIE 登录...")
                cookies = [{
                    "name": "_hjSessionUser_1071997",
                    "value": b4a_cookie,
                    "domain": "www.back4app.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }]
                page.context.add_cookies(cookies)
                page.goto(target_url, wait_until="domcontentloaded")

                if "login" not in page.url:
                    print("✅ Cookie 登录成功！")
                else:
                    print("⚠ Cookie 登录失败，将尝试邮箱密码登录。")
                    page.context.clear_cookies()
                    b4a_cookie = None

            # === 2. 如果 Cookie 失败或未提供，使用邮箱密码登录 ===
            if not b4a_cookie:
                if not (b4a_email and b4a_password):
                    print("❌ Cookie 无效，且未提供邮箱密码。无法登录。")
                    browser.close()
                    return False

                login_url = "https://www.back4app.com/login"
                print(f"访问登录页面: {login_url}")
                page.goto(login_url, wait_until="domcontentloaded")

                print("等待登录表单加载...")
                page.wait_for_selector('input[name="email"]')
                page.wait_for_selector('input[name="password"]')

                print("填写邮箱和密码...")
                page.fill('input[name="email"]', b4a_email)
                page.fill('input[name="password"]', b4a_password)

                print("点击登录按钮...")
                with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                    page.click('button[type="submit"]')

                if "login" in page.url:
                    print("❌ 邮箱密码登录失败")
                    page.screenshot(path="login_fail.png")
                    browser.close()
                    return False
                else:
                    print("✅ 邮箱密码登录成功！")

            # === 3. 确保进入目标容器页面 ===
            if page.url != target_url:
                print(f"导航至容器页面: {target_url}")
                page.goto(target_url, wait_until="domcontentloaded")
                if "login" in page.url:
                    print("❌ 导航失败，可能需要重新登录")
                    page.screenshot(path="container_nav_fail.png")
                    browser.close()
                    return False

            # === 4. 查找并点击 Redeploy App 按钮 ===
            print("寻找 'Redeploy App' 按钮...")
            deploy_selector = 'button:has-text("Redeploy App")'

            try:
                btn = page.locator(deploy_selector)
                btn.wait_for(state='visible', timeout=30000)
                print("点击 Redeploy App 按钮...")
                btn.click()
                time.sleep(5)
                print("🎉 Redeploy App 操作完成！")
                browser.close()
                return True

            except PlaywrightTimeoutError:
                print("❌ 未找到 'Redeploy App' 按钮")
                page.screenshot(path="redeploy_button_not_found.png")
                browser.close()
                return False

        except Exception as e:
            print(f"❌ 执行中出现错误: {e}")
            page.screenshot(path="general_error.png")
            browser.close()
            return False


if __name__ == "__main__":
    print("开始自动 Redeploy App 任务...")
    success = redeploy_app()
    if success:
        print("任务成功完成。")
        exit(0)
    else:
        print("任务失败。")
        exit(1)
