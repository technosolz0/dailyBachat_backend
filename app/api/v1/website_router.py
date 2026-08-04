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

from app.models.website import VisitorAnalytics
from app.schemas.website import VisitorTrackCreate

@router.post("/track/visitor")
def track_visitor_endpoint(payload: VisitorTrackCreate, db: Session = Depends(get_db)):
    """
    Backend API: Ingest and persist unique website visitor details into database.
    """
    existing = db.query(VisitorAnalytics).filter(VisitorAnalytics.visitor_id == payload.visitorId).first()
    
    if existing:
        existing.ip_address = payload.ip or existing.ip_address
        existing.country = payload.country or existing.country
        existing.state = payload.state or existing.state
        existing.city = payload.city or existing.city
        existing.age_group = payload.ageGroup or existing.age_group
        existing.gender = payload.gender or existing.gender
        existing.device = payload.device or existing.device
        existing.browser = payload.browser or existing.browser
        existing.os = payload.os or existing.os
        existing.visit_count += 1
        
        pages = json.loads(existing.pages_visited or "[]")
        if payload.path and payload.path not in pages:
            pages.append(payload.path)
        existing.pages_visited = json.dumps(pages)
        
        db.commit()
        db.refresh(existing)
        return {"success": True, "message": "Visitor updated"}
    else:
        new_visitor = VisitorAnalytics(
            visitor_id=payload.visitorId,
            ip_address=payload.ip,
            country=payload.country or "India",
            state=payload.state or "Maharashtra",
            city=payload.city or "Mumbai",
            age_group=payload.ageGroup or "25-34",
            gender=payload.gender or "Not Specified",
            device=payload.device or "Desktop",
            browser=payload.browser or "Chrome",
            os=payload.os or "Unknown",
            visit_count=1,
            pages_visited=json.dumps([payload.path or "/"])
        )
        db.add(new_visitor)
        db.commit()
        db.refresh(new_visitor)
        return {"success": True, "message": "Visitor created"}

@router.get("/admin/analytics")
def get_admin_visitor_analytics(
    age: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    device: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Backend API: Retrieve visitor analytics with filtering for Admin Dashboard.
    """
    query = db.query(VisitorAnalytics)

    if age and age != "All":
        query = query.filter(VisitorAnalytics.age_group == age)
    if country and country != "All":
        query = query.filter(VisitorAnalytics.country.ilike(country))
    if state and state != "All":
        query = query.filter(VisitorAnalytics.state.ilike(state))
    if city and city != "All":
        query = query.filter(VisitorAnalytics.city.ilike(city))
    if device and device != "All":
        query = query.filter(VisitorAnalytics.device.ilike(device))
    if search:
        s = f"%{search.lower()}%"
        query = query.filter(
            (VisitorAnalytics.visitor_id.ilike(s)) |
            (VisitorAnalytics.city.ilike(s)) |
            (VisitorAnalytics.state.ilike(s)) |
            (VisitorAnalytics.country.ilike(s)) |
            (VisitorAnalytics.ip_address.ilike(s))
        )

    visitors = query.order_by(VisitorAnalytics.last_seen.desc()).all()
    all_records = db.query(VisitorAnalytics).all()

    # Formulate filter dropdown lists
    countries = list(set([v.country for v in all_records if v.country]))
    states = list(set([v.state for v in all_records if v.state]))
    cities = list(set([v.city for v in all_records if v.city]))
    age_groups = ["18-24", "25-34", "35-44", "45+"]
    devices = ["Mobile", "Desktop", "Tablet"]

    # Compute Aggregations
    total_visitors = len(visitors)
    total_visits = sum([v.visit_count for v in visitors])

    age_breakdown = {}
    country_breakdown = {}
    state_breakdown = {}
    city_breakdown = {}
    device_breakdown = {}

    visitor_list = []

    for v in visitors:
        age_breakdown[v.age_group] = age_breakdown.get(v.age_group, 0) + 1
        country_breakdown[v.country] = country_breakdown.get(v.country, 0) + 1
        state_breakdown[v.state] = state_breakdown.get(v.state, 0) + 1
        city_breakdown[v.city] = city_breakdown.get(v.city, 0) + 1
        device_breakdown[v.device] = device_breakdown.get(v.device, 0) + 1

        visitor_list.append({
            "visitorId": v.visitor_id,
            "ip": v.ip_address or "127.0.0.1",
            "country": v.country,
            "state": v.state,
            "city": v.city,
            "ageGroup": v.age_group,
            "gender": v.gender,
            "device": v.device,
            "browser": v.browser,
            "os": v.os,
            "visitCount": v.visit_count,
            "pagesVisited": json.loads(v.pages_visited or "[]"),
            "firstSeen": v.first_seen.isoformat() if v.first_seen else "",
            "lastSeen": v.last_seen.isoformat() if v.last_seen else ""
        })

    return {
        "summary": {
            "totalVisitors": total_visitors,
            "totalVisits": total_visits,
            "ageBreakdown": age_breakdown,
            "countryBreakdown": country_breakdown,
            "stateBreakdown": state_breakdown,
            "cityBreakdown": city_breakdown,
            "deviceBreakdown": device_breakdown
        },
        "filterOptions": {
            "countries": countries,
            "states": states,
            "cities": cities,
            "ageGroups": age_groups,
            "devices": devices
        },
        "visitors": visitor_list
    }

