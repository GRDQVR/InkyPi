from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageOps, ImageColor
from utils.image_utils import pad_image_blur
import requests, io, json, os, time, logging, base64

logger = logging.getLogger(__name__)

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "spotify_token.json")
REDIRECT_URI = "http://127.0.0.1:8080/callback"
TOKEN_URL = "https://accounts.spotify.com/api/token"
CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

class Spotify(BasePlugin):

    def get_token(self, settings):
        client_id = settings.get("clientId")
        client_secret = settings.get("clientSecret")
        auth_code = settings.get("authCode")

        token_data = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)

        # Reuse valid token
        if token_data and time.time() < token_data.get("expires_at", 0):
            return token_data["access_token"]

        # Refresh token if possible
        if token_data and "refresh_token" in token_data and client_id and client_secret:
            refresh_token = token_data["refresh_token"]
            headers = {"Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()}
            data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
            resp = requests.post(TOKEN_URL, data=data, headers=headers)
            if resp.status_code == 200:
                new_data = resp.json()
                token_data["access_token"] = new_data["access_token"]
                token_data["expires_at"] = time.time() + new_data.get("expires_in", 3600)
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_data, f)
                return token_data["access_token"]
            else:
                logger.warning(f"Refresh token failed: {resp.text}, trying new code.")

        # If no token or refresh failed, try first-time auth
        if not (client_id and client_secret and auth_code):
            raise RuntimeError("Spotify credentials missing and no valid token found.")

        headers = {"Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()}
        data = {"grant_type": "authorization_code", "code": auth_code, "redirect_uri": REDIRECT_URI}
        resp = requests.post(TOKEN_URL, data=data, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Spotify token request failed: {resp.text}")

        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        if "refresh_token" in token_data:
            token_data["refresh_token"] = token_data["refresh_token"]

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

        return token_data["access_token"]

    def get_current_album_art(self, access_token):
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(CURRENTLY_PLAYING_URL, headers=headers)
        if resp.status_code != 200:
            logger.error(f"Spotify currently-playing API failed: {resp.text}")
            raise RuntimeError("Spotify currently-playing API failed.")
        data = resp.json()
        try:
            return data["item"]["album"]["images"][0]["url"]
        except Exception as e:
            raise RuntimeError(f"Failed to parse album art: {e}")

    def generate_image(self, settings, device_config) -> Image:
        access_token = self.get_token(settings)
        image_url = self.get_current_album_art(access_token)
        img_data = requests.get(image_url).content
        image = Image.open(io.BytesIO(img_data))

        dimensions = device_config.get_resolution()
        orientation = device_config.get_config("orientation")
        if orientation == "vertical":
            dimensions = dimensions[::-1]

        if settings.get("padImage") == "true":
            if settings.get("backgroundOption") == "blur":
                return pad_image_blur(image, dimensions)
            else:
                background_color = ImageColor.getcolor(settings.get("backgroundColor") or (255,255,255),"RGB")
                return ImageOps.pad(image, dimensions, color=background_color, method=Image.Resampling.LANCZOS)
        return image

