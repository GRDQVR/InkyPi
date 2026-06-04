from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageOps, ImageColor, ImageDraw, ImageFont
from utils.app_utils import get_font
from utils.image_utils import pad_image_blur
import requests, io, json, os, time, logging, base64

logger = logging.getLogger(__name__)

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "spotify_token.json")
REDIRECT_URI = "http://127.0.0.1:8080/callback"
TOKEN_URL = "https://accounts.spotify.com/api/token"
CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYED_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"


class Spotify(BasePlugin):

    def get_token(self, settings):
        token_data = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)

        if token_data and time.time() < token_data.get("expires_at", 0):
            return token_data["access_token"]

        client_id = settings.get("clientId") or (token_data.get("client_id") if token_data else None)
        client_secret = settings.get("clientSecret") or (token_data.get("client_secret") if token_data else None)
        auth_code = settings.get("authCode")

        if token_data and token_data.get("refresh_token"):
            if not (client_id and client_secret):
                raise RuntimeError("Client ID/Secret missing; cannot refresh Spotify token")
            headers = {
                "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            }
            data = {"grant_type": "refresh_token", "refresh_token": token_data["refresh_token"]}
            resp = requests.post(TOKEN_URL, data=data, headers=headers)
            if resp.status_code == 200:
                new_data = resp.json()
                token_data["access_token"] = new_data["access_token"]
                token_data["expires_at"] = time.time() + new_data.get("expires_in", 3600)
                token_data["client_id"] = client_id
                token_data["client_secret"] = client_secret
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_data, f)
                return token_data["access_token"]
            else:
                logger.warning(f"Refresh token failed: {resp.text}, trying first-time auth.")

        if not (client_id and client_secret and auth_code):
            raise RuntimeError("Spotify credentials missing and no valid token found.")

        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        }
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI
        }
        resp = requests.post(TOKEN_URL, data=data, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Spotify token request failed: {resp.text}")

        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        token_data["client_id"] = client_id
        token_data["client_secret"] = client_secret

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

        return token_data["access_token"]

    def get_currently_playing(self, access_token):
        """Returns (image_url, track_name, artist_name, is_playing) or None if nothing playing."""
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(CURRENTLY_PLAYING_URL, headers=headers)

        if resp.status_code == 204:
            return None

        if resp.status_code != 200:
            logger.error(f"Spotify currently-playing API failed: {resp.text}")
            raise RuntimeError("Spotify currently-playing API failed.")

        data = resp.json()
        try:
            item = data.get("item") or {}
            image_url = item["album"]["images"][0]["url"]
            track_name = item.get("name", "")
            artist_name = ", ".join(a["name"] for a in item.get("artists", []))
            is_playing = data.get("is_playing", False)
            return image_url, track_name, artist_name, is_playing
        except Exception as e:
            raise RuntimeError(f"Failed to parse currently playing: {e}")

    def get_recently_played(self, access_token):
        """Returns (image_url, track_name, artist_name) for the last played track."""
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(RECENTLY_PLAYED_URL, headers=headers)

        if resp.status_code != 200:
            logger.error(f"Spotify recently-played API failed: {resp.text}")
            return None

        data = resp.json()
        try:
            item = data["items"][0]["track"]
            image_url = item["album"]["images"][0]["url"]
            track_name = item.get("name", "")
            artist_name = ", ".join(a["name"] for a in item.get("artists", []))
            return image_url, track_name, artist_name
        except Exception:
            return None

    def build_image(self, album_art, track_name, artist_name, dimensions, settings, recently_played=False):
        pad = settings.get("padImage") == "true"
        show_text = settings.get("showText") == "true"

        if pad:
            if settings.get("backgroundOption") == "blur":
                image = pad_image_blur(album_art, dimensions)
            else:
                bg_color = ImageColor.getcolor(settings.get("backgroundColor") or "#ffffff", "RGB")
                image = ImageOps.pad(album_art, dimensions, color=bg_color, method=Image.Resampling.LANCZOS)
        else:
            image = album_art.resize(dimensions, Image.Resampling.LANCZOS)

        if show_text and (track_name or artist_name):
            image = self._draw_text_overlay(image, track_name, artist_name, recently_played)

        return image

    def _draw_text_overlay(self, image, track_name, artist_name, recently_played=False):
        w, h = image.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        bar_height = max(80, h // 6)
        draw.rectangle([(0, h - bar_height), (w, h)], fill=(0, 0, 0, 170))

        try:
            font_track = get_font("Roboto-Bold", max(20, h // 22))
            font_artist = get_font("Roboto-Regular", max(16, h // 28))
            font_label = get_font("Roboto-Regular", max(13, h // 36))
        except Exception:
            font_track = ImageFont.load_default()
            font_artist = font_track
            font_label = font_track

        padding = 16
        track_y = h - bar_height + padding

        if recently_played:
            draw.text((padding, track_y), "Sidst afspillet:", font=font_label, fill=(180, 180, 180, 255))
            track_y += max(16, h // 32)

        draw.text((padding, track_y), track_name, font=font_track, fill=(255, 255, 255, 255))
        artist_y = track_y + max(24, h // 22)
        draw.text((padding, artist_y), artist_name, font=font_artist, fill=(200, 200, 200, 255))

        return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    def _make_not_playing_image(self, dimensions):
        img = Image.new("RGB", dimensions, color=(18, 18, 18))
        draw = ImageDraw.Draw(img)

        try:
            font_big = get_font("Roboto-Bold", max(28, dimensions[1] // 14))
            font_small = get_font("Roboto-Regular", max(18, dimensions[1] // 22))
        except Exception:
            font_big = ImageFont.load_default()
            font_small = font_big

        cx, cy = dimensions[0] // 2, dimensions[1] // 2 - dimensions[1] // 10
        r = min(dimensions) // 8
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 215, 96))

        note = "♫"
        bbox = draw.textbbox((0, 0), note, font=font_big)
        nw, nh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - nw // 2, cy - nh // 2), note, font=font_big, fill=(0, 0, 0))

        msg = "Intet afspilles lige nu"
        bbox = draw.textbbox((0, 0), msg, font=font_big)
        draw.text(((dimensions[0] - (bbox[2] - bbox[0])) // 2, cy + r + 20), msg, font=font_big, fill=(255, 255, 255))

        sub = "Spotify er ikke aktiv"
        bbox = draw.textbbox((0, 0), sub, font=font_small)
        draw.text(((dimensions[0] - (bbox[2] - bbox[0])) // 2, cy + r + 60), sub, font=font_small, fill=(150, 150, 150))

        return img

    def generate_image(self, settings, device_config) -> Image:
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        access_token = self.get_token(settings)
        result = self.get_currently_playing(access_token)

        if result:
            image_url, track_name, artist_name, is_playing = result
            img_data = requests.get(image_url).content
            album_art = Image.open(io.BytesIO(img_data))
            return self.build_image(album_art, track_name, artist_name, dimensions, settings)

        # Intet spiller — vis senest afspillede hvis slået til
        if settings.get("showRecentIfIdle") == "true":
            recent = self.get_recently_played(access_token)
            if recent:
                image_url, track_name, artist_name = recent
                img_data = requests.get(image_url).content
                album_art = Image.open(io.BytesIO(img_data))
                return self.build_image(album_art, track_name, artist_name, dimensions, settings, recently_played=True)

        return self._make_not_playing_image(dimensions)
