import os
from dotenv import load_dotenv
from msal import ConfidentialClientApplication

load_dotenv(".env.local")
load_dotenv()

SCOPES = ["User.Read", "Mail.Read"]

def _build_msal_app():
    return ConfidentialClientApplication(
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_credential=os.getenv("AZURE_CLIENT_SECRET"),
        authority=f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}",
    )

def build_auth_url():
    app = _build_msal_app()

    flow = app.initiate_auth_code_flow(
        scopes=SCOPES,
        redirect_uri=os.getenv("AZURE_REDIRECT_URI"),
    )

    return flow