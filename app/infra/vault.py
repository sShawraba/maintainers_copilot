import os
import hvac

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")

def get_jwt_secret() -> str:
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        raise ConnectionError("Failed to authenticate with Vault")
    
    # Use just the secret name; mount point is 'secret' by default
    try:
        secret_response = client.secrets.kv.v2.read_secret_version(path="jwt")
        jwt_secret = secret_response['data']['data'].get('JWT_SECRET_KEY')
        if not jwt_secret:
            raise ValueError("JWT_SECRET_KEY not found in Vault secret 'jwt'")
        return jwt_secret
    except hvac.exceptions.InvalidPath:
        raise RuntimeError("Secret 'jwt' not found in Vault. Please create it with: vault kv put secret/jwt JWT_SECRET_KEY=your-key")
    except Exception as e:
        raise RuntimeError(f"Error reading JWT secret from Vault: {e}")