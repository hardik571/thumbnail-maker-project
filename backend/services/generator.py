import asyncio
import logging 
from sqlmodel import Session, select
from database import engine
from models import Job, Thumbnail
from services.geminiai_service import generate_thumbnail
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)

STYLES = {
    "bold_dramatic": (
        "Create a bold, dramatic YouTube thumbnail with high contrast, "
        "cinematic lighting, dark moody background, and powerful composition. "
        "The person's face should be prominent with a dramatic expression."
    ),
    "clean_minimal": (
        "Create a clean, minimal YouTube thumbnail with bright lighting, "
        "white/light background, modern professional aesthetic, plenty of "
        "whitespace, and sharp clean composition. The person should look "
        "approachable and professional."
    ),
    "vibrant_energetic": (
        "Create a vibrant, energetic YouTube thumbnail with colorful gradients, "
        "dynamic angles, eye-catching pop-art style colors, and energetic "
        "composition. The person should have an excited or engaging expression."
    ),
}
STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]


async def generate_single_thumbnail(thumbnail_id: str, prompt: str, headshot_url: str):
    # 1. DB mein status badal kar "generating" karo
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        if not thumb:
            logger.error(f"Thumbnail {thumbnail_id} not found in database")
            return
        thumb.status = "generating"
        style_name = thumb.style_name
        session.add(thumb)
        session.commit()
    
    style_prompt = STYLES[style_name]

    try:
        # 2. Gemini AI se raw image bytes lekar aao
        image_bytes = await generate_thumbnail(prompt, style_prompt, headshot_url)
        
        # 3. Thumbnail model se job_id nikalne ke liye ek baar DB read karo
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            job_id = thumb.job_id

        # 4. ImageKit Cloud par image bytes ko upload karo aur URL wapas lo
        # (Yahan pehle folder_path aur image_byte ki typing mistake thi, use fix kar diya hai)
        url = await asyncio.to_thread(
            upload_file,
            file_bytes=image_bytes,
            file_name=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}/"
        )
        # 5. DB mein milne wala unique URL save karo aur status "uploaded" mark karo
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            thumb.imagekit_url = url
            thumb.status = "uploaded"
            session.add(thumb)
            session.commit()
            
        logger.info(f"Thumbnail {thumbnail_id} generated and uploaded successfully")
        
    except Exception as e:
        logger.error(f"Error generating thumbnail {thumbnail_id}: {e}")
        # 6. Agar kuch crash hua, toh status ko "error" mark karo taaki server chalta rahe
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            if thumb:
                thumb.status = "error"
                thumb.error_message = str(e)[:500]
                session.add(thumb)
                session.commit()


async def process_job(job_id: str):
    # 1. Main Job ka status "processing" mark karo
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()

        # 2. Is job ke andar jitne bhi thumbnails banane hain unhe select karo
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        
        thumbnails_ids = [t.id for t in thumbnails]
        
        # 3. Saare workers (tasks) ko ek list mein dalo
        tasks = [
            generate_single_thumbnail(tid, prompt, headshot_url)
            for tid in thumbnails_ids
        ]
        
        # 4. asyncio.gather se saare thumbnails parallelly (ek sath) background mein banenge
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 5. Saare workers ka kaam khatam hone ke baad final status check karo
        with Session(engine) as session:
            thumbnails = session.exec(
                select(Thumbnail).where(Thumbnail.job_id == job_id)
            ).all()
            
            # Agar saare ke saare thumbnails fail ho gaye ("error" status wale hain)
            all_failed = all(t.status == "error" for t in thumbnails)
            
            job = session.get(Job, job_id)
            # Agar sab fail hue toh Job "failed", agar ek bhi bach gaya toh "completed"!
            job.status = "failed" if all_failed else "completed"
            
            session.add(job)
            session.commit()
            logger.info(f"Job {job_id} processing finished with status: {job.status}")