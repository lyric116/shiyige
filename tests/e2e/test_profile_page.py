import httpx


def login_through_page(page, live_server, email: str, password: str) -> None:
    page.goto(f"{live_server}/login.html", wait_until="domcontentloaded")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.locator("#login-form button[type='submit']").click()
    page.wait_for_url(
        f"{live_server}/index.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )


def test_profile_page_reads_and_updates_profile(browser, live_server) -> None:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": "profileuser",
            "email": "profile@example.com",
            "password": "secret-pass-123",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert register_response.status_code == 201

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, "profile@example.com", "secret-pass-123")
    page.locator("#userDropdown").wait_for(timeout=5000)

    page.goto(f"{live_server}/profile.html", wait_until="domcontentloaded")
    page.locator("#username").wait_for(timeout=5000)
    assert page.locator("#sidebar-email").text_content() == "profile@example.com"

    page.locator("#username").fill("updateduser")
    page.locator("#email").fill("updated@example.com")
    page.locator("#phone").fill("13800138000")
    page.locator("#birthday").fill("2000-01-01")
    page.locator("#profile-form button[type='submit']").click()
    page.locator("body").get_by_text("个人信息已更新").wait_for(timeout=5000)

    access_token = page.evaluate("window.sessionStorage.getItem('shiyige_access_token')")
    me_response = httpx.get(
        f"{live_server}/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5.0,
        trust_env=False,
    )
    assert me_response.status_code == 200
    user = me_response.json()["data"]["user"]
    assert user["email"] == "updated@example.com"
    assert user["username"] == "updateduser"
    assert user["profile"]["phone"] == "13800138000"
    assert user["profile"]["birthday"] == "2000-01-01"

    context.close()


def test_profile_page_logout_clears_session(browser, live_server) -> None:
    register_response = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={
            "username": "logoutuser",
            "email": "logout@example.com",
            "password": "secret-pass-123",
        },
        timeout=5.0,
        trust_env=False,
    )
    assert register_response.status_code == 201

    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    login_through_page(page, live_server, "logout@example.com", "secret-pass-123")
    page.goto(f"{live_server}/profile.html", wait_until="domcontentloaded")
    page.locator("#logout-sidebar-btn").click()
    page.wait_for_url(
        f"{live_server}/login.html",
        wait_until="domcontentloaded",
        timeout=5000,
    )

    access_token = page.evaluate("window.sessionStorage.getItem('shiyige_access_token')")
    cookies = context.cookies()
    assert access_token is None
    assert all(cookie["name"] != "refresh_token" for cookie in cookies)

    context.close()
