import base64
import os

from openai import OpenAI


SUPPORTED_IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}


def _get_client(api_key=None):
    resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=resolved_api_key)


def generate_image_data_url(prompt, api_key=None, model="gpt-image-1", size="1024x1024"):
    client = _get_client(api_key=api_key)
    resolved_size = size if size in SUPPORTED_IMAGE_SIZES else "auto"
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=resolved_size,
    )

    image_data = (response.data or [None])[0]
    if image_data is None:
        return None

    # Prefer base64 content and normalize it to a data URL for template rendering.
    b64_json = getattr(image_data, "b64_json", None)
    if b64_json:
        try:
            base64.b64decode(b64_json, validate=True)
            return f"data:image/png;base64,{b64_json}"
        except Exception:
            return None

    image_url = getattr(image_data, "url", None)
    if image_url:
        return image_url

    return None