import logging
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session, engine
from models import Job, Thumbnail
from services.generator import process_job, STYLE_ORDER
from services.imagekit_service import upload_file, get_variants

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")  # before any other router it gets fixed


# ---------- Request/Response Schemas ----------
class CreateJobRequest(BaseModel):
    prompt: str
    num_thumbnails: int
    headshot_url: str


class CreateJobResponse(BaseModel):
    job_id: str


class ThumbnailResponse(BaseModel):
    id: str
    style_name: str
    status: str
    imagekit_url: str | None = None
    error_message: str | None = None
    variants: dict | None = None


class JobResponse(BaseModel):
    id: str
    prompt: str
    num_thumbnails: int
    headshot_url: str
    status: str
    thumbnails: list[ThumbnailResponse]


# ---------- Routes ----------
@router.post("/upload-headshot")
async def upload_headshot(file: UploadFile = File(...)):
    contents = await file.read()
    url = await asyncio.to_thread(
        upload_file,
        file_bytes=contents,
        file_name=file.filename or "headshot.jpg",
        folder="/headshots",
        content_type=file.content_type or "image/png",
    )
    return {"url": url}


@router.post("/jobs", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest, db: Session = Depends(get_session)):
    if request.num_thumbnails < 1 or request.num_thumbnails > 3:
        raise HTTPException(status_code=400, detail="num_thumbnails must be between 1 and 3")

    job = Job(
        prompt=request.prompt,
        num_thumbnails=request.num_thumbnails,
        headshot_url=request.headshot_url,
        status="pending",
    )
    db.add(job)
    db.flush()  # job.id ko assign karwane ke liye, bina poora commit kiye

    styles = STYLE_ORDER[: request.num_thumbnails]
    for style in styles:
        thumb = Thumbnail(job_id=job.id, style_name=style, status="pending")
        db.add(thumb)

    db.commit()
    db.refresh(job)

    asyncio.create_task(process_job(job.id))
    return CreateJobResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    thumbnails = session.exec(select(Thumbnail).where(Thumbnail.job_id == job_id)).all()

    thumb_response = []
    for t in thumbnails:
        variants = get_variants(t.imagekit_url) if t.imagekit_url else None
        thumb_response.append(
            ThumbnailResponse(
                id=t.id,
                style_name=t.style_name,
                status=t.status,
                imagekit_url=t.imagekit_url,
                error_message=t.error_message,
                variants=variants,
            )
        )

    return JobResponse(
        id=job.id,
        prompt=job.prompt,
        num_thumbnails=job.num_thumbnails,
        headshot_url=job.headshot_url,
        status=job.status,
        thumbnails=thumb_response,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def event_generator():
        sent_thumbnails = set()
        max_iterations = 200  # ~5 minutes safety cap (200 * 1.5s)
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if not job:
                    data = json.dumps({"error": "job not found"})
                    yield f"event: error\ndata: {data}\n\n"
                    return

                thumbnails = session.exec(
                    select(Thumbnail).where(Thumbnail.job_id == job_id)
                ).all()

                for t in thumbnails:
                    if t.id in sent_thumbnails:
                        continue

                    if t.status == "uploaded":
                        variants = get_variants(t.imagekit_url)
                        data = json.dumps({
                            "thumbnail_id": t.id,
                            "style_name": t.style_name,
                            "imagekit_url": t.imagekit_url,
                            "variants": variants,
                        })
                        yield f"event: thumbnail_ready\ndata: {data}\n\n"
                        sent_thumbnails.add(t.id)

                    elif t.status == "error":
                        data = json.dumps({
                            "thumbnail_id": t.id,
                            "style_name": t.style_name,
                            "error": t.error_message,
                        })
                        yield f"event: thumbnail_failed\ndata: {data}\n\n"
                        sent_thumbnails.add(t.id)

                all_done = all(t.status in ("uploaded", "error") for t in thumbnails)
                if all_done and len(sent_thumbnails) == len(thumbnails):
                    data = json.dumps({"job_id": job_id, "status": job.status})
                    yield f"event: job_completed\ndata: {data}\n\n"
                    return

            await asyncio.sleep(1.5)

        # loop safety-limit tak pahunch gaya, timeout event bhejo
        data = json.dumps({"job_id": job_id, "error": "stream timeout"})
        yield f"event: error\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )