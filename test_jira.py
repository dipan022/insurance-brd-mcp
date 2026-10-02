import os
import httpx
from dotenv import load_dotenv


load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


auth = (JIRA_EMAIL, JIRA_API_TOKEN)

headers = {
    "Accept": "application/json"
}


# ------------------------------------------------------------
# TEST 1: Check Jira account
# ------------------------------------------------------------

print("\nChecking Jira account...")

response = httpx.get(
    f"{JIRA_URL}/rest/api/3/myself",
    auth=auth,
    headers=headers,
    timeout=30
)

print("Account status:", response.status_code)

if response.status_code == 200:

    data = response.json()

    print("Jira account:", data.get("displayName"))
    print("Email:", data.get("emailAddress"))

else:

    print(response.text)


# ------------------------------------------------------------
# TEST 2: Check KAN project
# ------------------------------------------------------------

print("\nChecking KAN project...")

response = httpx.get(
    f"{JIRA_URL}/rest/api/3/project/KAN",
    auth=auth,
    headers=headers,
    timeout=30
)

print("Project status:", response.status_code)

if response.status_code == 200:

    data = response.json()

    print("Project name:", data.get("name"))
    print("Project key:", data.get("key"))

else:

    print(response.text)


# ------------------------------------------------------------
# TEST 3: Check KAN-1
# ------------------------------------------------------------

print("\nChecking KAN-1...")

response = httpx.get(
    f"{JIRA_URL}/rest/api/3/issue/KAN-1",
    auth=auth,
    headers=headers,
    timeout=30
)

print("Issue status:", response.status_code)

if response.status_code == 200:

    data = response.json()

    print("\nJIRA ISSUE FOUND")

    print("Issue:", data.get("key"))
    print("Summary:", data["fields"].get("summary"))

else:

    print(response.text)