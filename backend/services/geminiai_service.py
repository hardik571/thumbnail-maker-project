import httpx
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

async def generate_thumbnail(prompt: str, style_prompt: str, headshot_url: str) -> bytes:
    """
    Uses Gemini's native image generation and editing capability (gemini-2.5-flash-image)
    with the reference headshot passed directly into the multimodal contents array.
    Returns raw PNG/JPEG bytes at 16:9 aspect ratio (YouTube thumbnail standard).
    """
    full_prompt = (
        f"{style_prompt}\n\n"
        f"User request: {prompt}\n\n"
        "IMPORTANT: The generated thumbnail MUST prominently feature the person "
        "shown in the provided reference headshot photo. Keep their likeness accurate."
    )

    async with httpx.AsyncClient() as http_client:
        img_resp = await http_client.get(headshot_url)
        img_resp.raise_for_status()
        headshot_bytes = img_resp.content

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[
            full_prompt,
            types.Part.from_bytes(data=headshot_bytes, mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )

    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data

    raise RuntimeError("No image generation result found in the response")
'''Yeh file user ki face photo ko internet se download karti hai $\rightarrow$ 
 Use prompt ke sath milakar Gemini AI ke paas bhejti 
 hai $\rightarrow$ Gemini us face ko naye background 
 ke sath mix karke ek naya mast thumbnail banata hai 
 $\rightarrow$ Aur yeh function us nayi bani hui photo 
 ke raw bytes lekar wapas aa jata hai.'''