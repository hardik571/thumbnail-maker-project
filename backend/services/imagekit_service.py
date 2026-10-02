import base64
from imagekitio import ImageKit
from config import IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT

imagekit = ImageKit(
    private_key=IMAGEKIT_PRIVATE_KEY
)

def upload_file(file_bytes:bytes,file_name:str,folder:str,content_type:str = "image/png") -> str:
    """upload a file to Imagekit and return the URL."""
    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    result = imagekit.files.upload(
        file=file_b64,
        file_name=file_name,
        folder=folder,
        is_private_file=False,
        use_unique_file_name=True,
    )
    return result.url
#Is file ka simple kaam hai: Photo lo $\rightarrow$ ImageKit Cloud par upload karo $\rightarrow$ Uska internet URL link wapas le aao.
def get_variants(base_url:str) -> dict:
    """Return 3 sizes variant urls imagekit transformations."""
    return {"youtube":f"{base_url}?tr=w-1280,h-720,c-maintain_ratio,fo-auto",
            "shorts":f"{base_url}?tr=w-1080,h-1920,c-maintain_ratio,fo-auto",
            "thumbnail":f"{base_url}?tr=w-1080,h-1080,c-maintain_ratio,fo-auto",
            }

   