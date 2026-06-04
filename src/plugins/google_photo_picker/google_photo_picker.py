import requests
import random
import logging
import json
import os
from io import BytesIO
from PIL import Image
from plugins.base_plugin.base_plugin import BasePlugin
from utils.app_utils import resolve_path

logger = logging.getLogger(__name__)

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), "google_tokens.json")

# Mime types for images supported by Drive
IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
]


def save_tokens(tokens):
    """Persist tokens to disk so they survive across Update Now calls."""
    try:
        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save tokens: {e}")

def load_tokens():
    """Load persisted tokens from disk."""
    try:
        if os.path.exists(TOKEN_CACHE_FILE):
            with open(TOKEN_CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def exchange_auth_code(client_id, client_secret, code, settings):
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "https://developers.google.com/oauthplayground",
        "grant_type": "authorization_code",
    }
    resp = requests.post(TOKEN_URL, data=data)
    if not resp.ok:
        print(f"Token exchange error {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    tokens = resp.json()
    tokens["client_id"] = client_id
    tokens["client_secret"] = client_secret
    settings.update(tokens)
    save_tokens(tokens)
    return tokens["access_token"]


def refresh_google_token(client_id, client_secret, refresh_token):
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    tokens = resp.json()
    if "refresh_token" not in tokens:
        tokens["refresh_token"] = refresh_token
    return tokens


class GooglePhotoPicker(BasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_access_token(self, settings):
        # Merge cached tokens so credentials survive Update Now
        cached = load_tokens()
        for key in ("client_id", "client_secret", "refresh_token"):
            if not settings.get(key) and cached.get(key):
                settings[key] = cached[key]

        client_id = settings.get("client_id")
        client_secret = settings.get("client_secret")
        auth_code = settings.get("auth_code")
        refresh_token = settings.get("refresh_token")

        if not client_id or not client_secret:
            raise RuntimeError("Client ID and Client Secret must be set.")

        if refresh_token:
            try:
                tokens = refresh_google_token(client_id, client_secret, refresh_token)
                tokens["client_id"] = client_id
                tokens["client_secret"] = client_secret
                settings.update(tokens)
                save_tokens(tokens)
                return tokens["access_token"]
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")

        if auth_code:
            return exchange_auth_code(client_id, client_secret, auth_code, settings)

        raise RuntimeError("No authorization code or refresh token available.")

    def fetch_all_image_ids(self, access_token, folder_id=None):
        """Fetch up to 1000 image file IDs from Google Drive (or a specific folder)."""
        headers = {"Authorization": f"Bearer {access_token}"}
        mime_query = " or ".join([f"mimeType='{m}'" for m in IMAGE_MIME_TYPES])
        query = f"({mime_query}) and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        image_ids = []
        page_token = None

        while len(image_ids) < 1000:
            params = {
                "q": query,
                "fields": "nextPageToken, files(id)",
                "pageSize": 100,
                "orderBy": "createdTime desc",
            }
            if page_token:
                params["pageToken"] = page_token

            resp = requests.get(DRIVE_FILES_URL, headers=headers, params=params)
            if not resp.ok:
                logger.error(f"Drive API error {resp.status_code}: {resp.text}")
            resp.raise_for_status()

            data = resp.json()
            image_ids.extend([f["id"] for f in data.get("files", [])])
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return image_ids

    def download_image(self, access_token, file_id):
        """Download image content from Google Drive."""
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{DRIVE_FILES_URL}/{file_id}?alt=media"
        resp = requests.get(url, headers=headers)
        if not resp.ok:
            logger.error(f"Drive download error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.content

    def generate_image(self, settings, device_config):
        folder_id = settings.get("folder_id") or None
        random_order = settings.get("randomOrder") == "true"

        token = self.get_access_token(settings)
        image_ids = self.fetch_all_image_ids(token, folder_id=folder_id)

        if not image_ids:
            raise RuntimeError("No images found in Google Drive.")

        if random_order:
            file_id = random.choice(image_ids)
        else:
            file_id = image_ids[0]

        content = self.download_image(token, file_id)
        return Image.open(BytesIO(content))
