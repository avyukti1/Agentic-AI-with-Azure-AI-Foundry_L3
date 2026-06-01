"""Simple tools used by both demos.

In a real enterprise application, these tools could call systems such as
ServiceNow, Jira, SharePoint, Confluence, Azure AI Search, or a ticketing API.
For this classroom demo, they are simple Python functions so the ReAct pattern
is easy to understand.
"""


def search_knowledge_base(issue: str) -> str:
    """Return a matching troubleshooting article for a user issue.

    The user issue is matched with simple keywords:
    - vpn -> VPN troubleshooting article
    - email/outlook -> Email troubleshooting article
    - laptop/slow -> Laptop troubleshooting article
    """

    # This dictionary works like a mini knowledge base.
    # Each key is an issue category, and each value is the article content.
    knowledge_base = {
        "vpn": """VPN Troubleshooting Steps:
1. Check your internet connection.
2. Confirm your VPN username and password.
3. Verify MFA approval.
4. Restart the VPN client.
5. Try connecting from another network.""",
        "email": """Email Troubleshooting Steps:
1. Check your internet connection.
2. Restart Outlook.
3. Check mailbox storage.
4. Log in using a browser.
5. Contact IT if the issue continues.""",
        "laptop": """Laptop Slow Troubleshooting Steps:
1. Restart the laptop.
2. Check CPU and RAM usage.
3. Disable unnecessary startup apps.
4. Run an antivirus scan.
5. Check disk space.""",
    }

    # Convert the issue to lowercase so matching works for VPN, vpn, Vpn, etc.
    issue_lower = issue.lower()

    # Tool logic: choose the best KB article based on keywords in the issue.
    if "vpn" in issue_lower:
        return knowledge_base["vpn"]
    if "email" in issue_lower or "outlook" in issue_lower:
        return knowledge_base["email"]
    if "laptop" in issue_lower or "slow" in issue_lower:
        return knowledge_base["laptop"]

    return "No matching KB article found."


def create_ticket(issue: str) -> str:
    """Create a demo ticket for an unresolved issue.

    This function returns a fixed ticket number for demo purposes.
    In production, this function would call an ITSM ticketing API.
    """
    return f"Ticket INC1001 created successfully for issue: {issue}"
