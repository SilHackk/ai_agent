TOKEN_CACHE = {}

def save_access_token(token: str):
    TOKEN_CACHE["access_token"] = token

def get_graph_token() -> str:
    token = TOKEN_CACHE.get("access_token")

    if not token:
        raise RuntimeError(
            "Pirmiausia atsidaryk http://127.0.0.1:8000/auth/login ir prisijunk prie Outlook."
        )

    return token