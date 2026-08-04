from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class WebsiteContentBase(BaseModel):
    section_key: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content_json: Optional[str] = None

class WebsiteContentCreate(WebsiteContentBase):
    pass

class WebsiteContentUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content_json: Optional[str] = None

class WebsiteContentResponse(WebsiteContentBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TestimonialBase(BaseModel):
    author_name: str
    author_role: Optional[str] = None
    avatar_url: Optional[str] = None
    quote: str
    rating: Optional[int] = 5
    is_active: Optional[int] = 1

class TestimonialCreate(TestimonialBase):
    pass

class TestimonialUpdate(BaseModel):
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    avatar_url: Optional[str] = None
    quote: Optional[str] = None
    rating: Optional[int] = None
    is_active: Optional[int] = None

class TestimonialResponse(TestimonialBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class BlogPostBase(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    category: Optional[str] = "General"
    read_time: Optional[str] = "5 min read"
    author_name: Optional[str] = "DailyBachat Team"
    author_role: Optional[str] = "Financial Writer"
    content: str
    is_published: Optional[int] = 1
    published_date: Optional[str] = None

class BlogPostCreate(BlogPostBase):
    pass

class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    read_time: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    content: Optional[str] = None
    is_published: Optional[int] = None
    published_date: Optional[str] = None

class BlogPostResponse(BlogPostBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ContactSubmissionCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str

class ContactSubmissionUpdateStatus(BaseModel):
    status: str

class ContactSubmissionResponse(ContactSubmissionCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class VisitorTrackCreate(BaseModel):
    visitorId: str
    ip: Optional[str] = None
    country: Optional[str] = "India"
    state: Optional[str] = "Maharashtra"
    city: Optional[str] = "Mumbai"
    ageGroup: Optional[str] = "25-34"
    gender: Optional[str] = "Not Specified"
    device: Optional[str] = "Desktop"
    browser: Optional[str] = "Chrome"
    os: Optional[str] = "Unknown"
    path: Optional[str] = "/"

