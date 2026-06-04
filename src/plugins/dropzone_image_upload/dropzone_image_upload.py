from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageOps, ImageColor
import logging

from utils.image_utils import pad_image_blur

logger = logging.getLogger(__name__)


class DropzoneImageUpload(BasePlugin):
    def open_image(self, image_path: str) -> Image:
        """Open an image file safely."""
        try:
            image = Image.open(image_path)
        except Exception as e:
            logger.error(f"Failed to read image file: {str(e)}")
            raise RuntimeError("Failed to read image file.")
        return image

    def generate_image(self, settings, device_config) -> Image:
        """Generate the final image to show on the display."""
        image_files = settings.get("imageFiles[]")

        if not image_files:
            raise RuntimeError("No image uploaded.")

        # Always use the first (and only) uploaded image
        image_path = image_files[0]
        image = self.open_image(image_path)

        orientation = device_config.get_config("orientation")

        if settings.get('padImage') == "true":
            dimensions = device_config.get_resolution()
            if orientation == "vertical":
                dimensions = dimensions[::-1]

            if settings.get('backgroundOption') == "blur":
                return pad_image_blur(image, dimensions)
            else:
                background_color = ImageColor.getcolor(
                    settings.get('backgroundColor') or (255, 255, 255), "RGB"
                )
                return ImageOps.pad(
                    image,
                    dimensions,
                    color=background_color,
                    method=Image.Resampling.LANCZOS
                )

        return image
