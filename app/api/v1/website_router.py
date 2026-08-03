from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json

from app.core.database import get_db
from app.models.website import WebsiteContent, ContactSubmission, Testimonial, BlogPostModel
from app.schemas.website import (
    WebsiteContentResponse,
    ContactSubmissionCreate,
    ContactSubmissionResponse,
    TestimonialResponse,
    BlogPostResponse
)

router = APIRouter()

# Default fallback dynamic contents for public site
DEFAULT_WEBSITE_SECTIONS = {
    "hero": {
        "title": "Smart Financial Management for Every Indian Household & Business",
        "subtitle": "DailyBachat helps you track daily expenses, manage GST invoices, handle split bills, monitor loans, and gain complete control over your money seamlessly.",
        "content_json": json.dumps({
            "primaryBtnText": "Download App",
            "secondaryBtnText": "Explore Features",
            "badgeText": "Trusted by 50,000+ Active Users",
            "stats": [
                {"value": "50K+", "label": "Active Users"},
                {"value": "₹10Cr+", "label": "Tracked Monthly"},
                {"value": "4.9★", "label": "App Store Rating"}
            ]
        })
    },
    "features": {
        "title": "Everything you need to master your savings & business finances",
        "subtitle": "Designed with simplicity, security, and smart AI insights for individuals and small business owners alike.",
        "content_json": json.dumps([
            {
                "id": "expense-tracking",
                "title": "Smart Expense Tracker",
                "description": "Categorize every rupee spent, set budget alerts, and analyze monthly trends effortlessly."
            },
            {
                "id": "gst-billing",
                "title": "GST Invoicing & Quotations",
                "description": "Create professional bills, tax invoices, and quotations on the go with custom branding."
            },
            {
                "id": "group-split",
                "title": "Group Bill Splitting",
                "description": "Split trips, household bills, and party expenses with friends without awkward conversations."
            },
            {
                "id": "loan-manager",
                "title": "Udhar & Debt Manager",
                "description": "Keep track of payments given or owed with automated SMS/WhatsApp reminders."
            }
        ])
    },
    "contact_info": {
        "title": "Get in Touch with DailyBachat Team",
        "subtitle": "Have questions or need support? Reach out to us anytime.",
        "content_json": json.dumps({
            "email": "technosolz01@gmail.com",
            "phone": "+91 75587 26131",
            "address": "Mumbai, Maharashtra, India",
            "workingHours": "Mon - Sun: 9:00 AM - 9:00 PM IST",
            "facebook": "https://www.facebook.com/technosolz01",
            "instagram": "https://www.instagram.com/technosolz01/",
            "linkedin": "https://www.linkedin.com/company/technosolz01/"
        })
    }
}

@router.get("/content", response_model=Dict[str, Any])
def get_website_content(db: Session = Depends(get_db)):
    """
    Public API: Fetch dynamic website sections (hero, features, contact_info, social_links, etc.).
    """
    records = db.query(WebsiteContent).all()
    result = {}

    for section_key, val in DEFAULT_WEBSITE_SECTIONS.items():
        result[section_key] = {
            "section_key": section_key,
            "title": val["title"],
            "subtitle": val["subtitle"],
            "content_json": val["content_json"]
        }

    for rec in records:
        result[rec.section_key] = {
            "section_key": rec.section_key,
            "title": rec.title,
            "subtitle": rec.subtitle,
            "content_json": rec.content_json,
            "updated_at": rec.updated_at
        }

    return result

@router.get("/testimonials", response_model=List[TestimonialResponse])
def get_public_testimonials(db: Session = Depends(get_db)):
    """
    Public API: Fetch active user testimonials.
    """
    return db.query(Testimonial).filter(Testimonial.is_active == 1).order_by(Testimonial.id.desc()).all()

@router.get("/blogs", response_model=List[BlogPostResponse])
def get_public_blog_posts(db: Session = Depends(get_db)):
    """
    Public API: Fetch published blog posts.
    """
    return db.query(BlogPostModel).filter(BlogPostModel.is_published == 1).order_by(BlogPostModel.id.desc()).all()

@router.get("/blogs/{slug}", response_model=BlogPostResponse)
def get_public_blog_post_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Public API: Fetch a single blog post by slug.
    """
    post = db.query(BlogPostModel).filter(BlogPostModel.slug == slug, BlogPostModel.is_published == 1).first()
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post

@router.post("/contact", response_model=ContactSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_contact_form(payload: ContactSubmissionCreate, db: Session = Depends(get_db)):
    """
    Public API: Submit a Contact Us inquiry from website visitors.
    """
    submission = ContactSubmission(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
        status="pending"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission
