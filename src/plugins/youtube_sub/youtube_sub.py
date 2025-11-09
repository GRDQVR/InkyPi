import requests
import logging
from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class YoutubeSub(BasePlugin):
    def get_subscriber_count(self, channel_id, device_config):
        """Fetch subscriber count from YouTube API using the API key from device_config."""
        if not channel_id:
            return "N/A"
        
        api_key = device_config.load_env_key("YOUTUBE_SECRET")
        if not api_key:
            return "N/A"
        
        url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("items")
            if not items:
                return "N/A"

            stats = items[0].get("statistics", {})
            if stats.get("hiddenSubscriberCount"):
                return "Hidden"

            count = stats.get("subscriberCount")
            if count is None:
                return "N/A"

            return f"{int(count):,}"
        except Exception as e:
            logger.error(f"Error fetching YouTube subscribers: {e}")
            return "N/A"

    def generate_image(self, settings, device_config):
        """
        Generate the plugin image.
        `settings` comes from the plugin form (user input), `device_config` is a Config object.
        """
        # Dimensions fallback
        dimensions = getattr(device_config, "dimensions", (200, 200))

        # Get user input safely (fields may be blank)
        channel_id = settings.get("channel_id", "")
        title = settings.get("title", "My Channel")
        icon_url = settings.get("icon_url", "")

        template_params = {
            "title": title,
            "subscribers": self.get_subscriber_count(channel_id, device_config),
            "icon_url": icon_url
        }

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params["plugin_settings"] = settings

        return self.render_image(dimensions, "youtube.html", "youtube.css", template_params)

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params
