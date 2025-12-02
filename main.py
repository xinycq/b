import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def redeploy_app(target_url="https://containers.back4app.com/apps/8b776070-a50c-4390-a92f-4e41d9cd9f9f"):

    b4a_cookie = os.environ.get("BACK4APP_COOKIE")
    b4a_email = os.environ.get("BACK4APP_EMAIL")
    b4a_password = os.environ.get("BACK4APP_PASSWORD")

    if not (b4a_cookie or (b4a_email and b4a_password)):
        print("❌ 缺少登录凭据。")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(90000)

        try:
            # -----------------------------
            # 1. COOKIE 登录
            # -----------------------------
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
                    print("⚠ Cookie 登录失败，使用邮箱密码登录")
                    page.context.clear_cookies()
                    b4a_cookie = None

            # -----------------------------
            # 2. 邮箱密码登录
            # -----------------------------
            if not b4a_cookie:
                login_url = "https://www.back4app.com/login"
                print(f"访问登录页面: {login_url}")
                page.goto(login_url)

                page.wait_for_selector('input[name="email"]')
                page.wait_for_selector('input[name="password"]')

                page.fill('input[name="email"]', b4a_email)
                page.fill('input[name="password"]', b4a_password)

                print("点击登录按钮...")
                with page.expect_navigation():
                    page.click('button[type="submit"]')

                if "login" in page.url:
                    print("❌ 邮箱密码登录失败")
                    page.screenshot(path="login_fail.png")
                    return False
                else:
                    print("✅ 邮箱密码登录成功！")

            # -----------------------------
            # 3. 进入目标页面
            # -----------------------------
            if page.url != target_url:
                print(f"导航到容器页面: {target_url}")
                page.goto(target_url)

            time.sleep(3)
            print("页面加载完成，开始查找 Redeploy App 按钮...")

            # ==========================
            # 超级强化按钮查找系统
            # ==========================

            def try_click(selector, use_locator=True):
                try:
                    if use_locator:
                        btn = page.locator(selector)
                        btn.wait_for(state='visible', timeout=5000)
                        btn.scroll_into_view_if_needed()
                        btn.click()
                    else:
                        page.wait_for_selector(selector, timeout=5000)
                        page.locator(selector).scroll_into_view_if_needed()
                        page.locator(selector).click()
                    print(f"⭐ 成功点击: {selector}")
                    return True
                except Exception:
                    return False

            # ---- 第一层：Playwright 标准选择器 ----
            selectors = [
                'button:has-text("Redeploy App")',
                'text=Redeploy App',
                'button.btn-success',
                '//button[contains(., "Redeploy")]',
                '//a[contains(., "Redeploy")]',
            ]

            for sel in selectors:
                print(f"尝试定位按钮：{sel}")
                if try_click(sel, use_locator=not sel.startswith("//")):
                    print("🎉 成功 Redeploy App！")
                    return True

            # ---- 第二层：滚动页面并重试 ----
            print("尝试滚动页面寻找按钮...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            for sel in selectors:
                if try_click(sel, use_locator=not sel.startswith("//")):
                    print("🎉 成功 Redeploy App！")
                    return True

            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            for sel in selectors:
                if try_click(sel, use_locator=not sel.startswith("//")):
                    print("🎉 成功 Redeploy App！")
                    return True

            # ---- 第三层：暴力全文搜索包含 Redeploy 的节点 ----
            print("进入暴力搜索模式（扫描 DOM 文本）...")
            found = page.evaluate("""
                () => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                    const targets = [];
                    while (walker.nextNode()) {
                        if (walker.currentNode.innerText && walker.currentNode.innerText.includes("Redeploy")) {
                            targets.push(walker.currentNode);
                        }
                    }
                    if (targets.length > 0) {
                        targets[0].click();
                        return true;
                    }
                    return false;
                }
            """)

            if found:
                print("🎉 成功点击（暴力模式）！")
                return True

            # ---- 第四层：Shadow DOM 深度搜索 ----
            print("尝试 Shadow DOM 搜索...")
            shadow_click = page.evaluate("""
                () => {
                    function deepSearch(node) {
                        if (!node) return null;
                        if (node.innerText && node.innerText.includes("Redeploy")) return node;
                        if (node.shadowRoot) {
                            const result = deepSearch(node.shadowRoot);
                            if (result) return result;
                        }
                        for (const child of node.children) {
                            const result = deepSearch(child);
                            if (result) return result;
                        }
                        return null;
                    }
                    const btn = deepSearch(document.body);
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                }
            """)

            if shadow_click:
                print("🎉 成功点击（Shadow DOM 模式）！")
                return True

            # ==========================
            # 全部方法尝试完仍然失败
            # ==========================
            print("❌ 未找到 Redeploy App 按钮（所有方法失败）")
            page.screenshot(path="redeploy_not_found.png")
            return False

        except Exception as e:
            print(f"❌ 运行出错：{e}")
            page.screenshot(path="general_error.png")
            return False


if __name__ == "__main__":
    print("开始自动 Redeploy App 任务...")
    success = redeploy_app()
    exit(0 if success else 1)
