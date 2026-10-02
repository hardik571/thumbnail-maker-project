from datetime import datetime,timezone
from typing import Optional,List
from uuid import uuid4 #it generate random unique id because 1,2,3 only is not safe

from sqlmodel import Field,SQLModel,Relationship

def _uuid() -> str:
    return str(uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc) #it generate current time in utc format (utc is a global timer)

class Thumbnail(SQLModel,table=True):
    id: str = Field(default_factory=_uuid,primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    style_name: str = Field(default="")
    imagekit_url:Optional[str] = Field(default=None)
    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
    job: Optional["Job"] = Relationship(back_populates="thumbnails")

class Job(SQLModel,table=True):
    id : str = Field(default_factory = _uuid,primary_key=True)
    prompt: str = Field(default="")
    num_thumbnails: int = Field(default=1,ge=1,le=3)
    headshot_url: str = Field(default="")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=_now) #field work as a rule .can't directly write.

    thumbnails: List[Thumbnail] = Relationship(back_populates="job") #back_populates ka kaam hai un dono buttons ko aapas mein jode rakhna, taaki ek jagah kuch badle toh dusri jagah apne aap update ho jaye.