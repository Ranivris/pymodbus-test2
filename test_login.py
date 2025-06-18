import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/login"
DASHBOARD_URL = f"{BASE_URL}/"

def print_test_result(test_name, success, message=""):
    status = "SUCCESS" if success else "FAILURE"
    print(f"Test '{test_name}': {status} {message}")
    if not success:
        sys.exit(1) # Exit if any test fails

def run_tests():
    session = requests.Session() # Use a session to persist cookies (and thus flask session)

    # Test 1: Access dashboard directly (should redirect to login)
    print("\n--- Test 1: Access dashboard directly ---")
    try:
        response = session.get(DASHBOARD_URL, allow_redirects=False)
        actual_location = response.headers.get("Location")
        is_redirect_to_login = response.status_code == 302 and (actual_location == LOGIN_URL or actual_location == "/login")
        print_test_result("Access dashboard directly redirects to /login", is_redirect_to_login, f"Status: {response.status_code}, Location: {actual_location}")
    except requests.exceptions.ConnectionError as e:
        print_test_result("Access dashboard directly redirects to /login", False, f"Connection error: {e}. Is the server running?")
        return # Stop further tests if server is not running

    # Test 2: Incorrect credentials
    print("\n--- Test 2: Incorrect credentials ---")
    try:
        response = session.post(LOGIN_URL, data={"username": "wronguser", "password": "wrongpassword"}, allow_redirects=False)
        renders_login_again = response.status_code == 200
        contains_error_message = "잘못된 사용자 이름 또는 비밀번호입니다." in response.text
        print_test_result("Incorrect credentials shows error", renders_login_again and contains_error_message, f"Status: {response.status_code}, Error in text: {contains_error_message}")
        if not (renders_login_again and contains_error_message):
            print(f"Response text (first 500 chars): {response.text[:500]}")
    except requests.exceptions.ConnectionError as e:
        print_test_result("Incorrect credentials shows error", False, f"Connection error: {e}")
        return

    # Test 3: Correct credentials
    print("\n--- Test 3: Correct credentials ---")
    try:
        response_login = session.post(LOGIN_URL, data={"username": "admin", "password": "admin"}, allow_redirects=False)
        actual_location_login = response_login.headers.get("Location")
        is_redirect_to_dashboard = response_login.status_code == 302 and (actual_location_login == DASHBOARD_URL or actual_location_login == "/")
        print_test_result("Correct credentials redirect to /", is_redirect_to_dashboard, f"Status: {response_login.status_code}, Location: {actual_location_login}")

        if is_redirect_to_dashboard:
            # Follow redirect
            response_dashboard = session.get(DASHBOARD_URL) # session already has the cookie
            dashboard_accessible = response_dashboard.status_code == 200
            contains_dashboard_content = "HVAC 모니터링" in response_dashboard.text
            print_test_result("Dashboard accessible after login", dashboard_accessible and contains_dashboard_content, f"Status: {response_dashboard.status_code}, Dashboard content OK: {contains_dashboard_content}")
            if not (dashboard_accessible and contains_dashboard_content):
                 print(f"Response text (first 500 chars): {response_dashboard.text[:500]}")

        else:
            print_test_result("Dashboard accessible after login", False, "Skipped because login redirect failed.")
            print(f"Login response text (first 500 chars): {response_login.text[:500]}")


    except requests.exceptions.ConnectionError as e:
        print_test_result("Correct credentials redirect to /", False, f"Connection error: {e}")
        return

    print("\nAll tests completed.")

if __name__ == "__main__":
    run_tests()

