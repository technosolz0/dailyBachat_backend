from sqlalchemy import Column, String, DateTime, Integer, Text, func
from app.core.database import Base

class WebsiteContent(Base):
    __tablename__ = "website_contents"

    id = Column(Integer, primary_key=True, index=True)
    section_key = Column(String, unique=True, index=True, nullable=False) # e.g. "hero", "about", "features", "faqs", "contact_info", "social_links"
    title = Column(String, nullable=True)
    subtitle = Column(Text, nullable=True)
    content_json = Column(Text, nullable=True) # JSON string storing detailed dynamic configuration/list items
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Testimonial(Base):
    __tablename__ = "testimonials"

    id = Column(Integer, primary_key=True, index=True)
    author_name = Column(String, nullable=False)
    author_role = Column(String, nullable=True) # e.g. "Small Business Owner, Mumbai"
    avatar_url = Column(String, nullable=True)
    quote = Column(Text, nullable=False)
    rating = Column(Integer, default=5)
    is_active = Column(Integer, default=1) # 1 for visible, 0 for hidden
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BlogPostModel(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    excerpt = Column(Text, nullable=True)
    category = Column(String, default="General")
    read_time = Column(String, default="5 min read")
    author_name = Column(String, default="DailyBachat Team")
    author_role = Column(String, default="Financial Writer")
    content = Column(Text, nullable=False) # HTML or Markdown content
    is_published = Column(Integer, default=1)
    published_date = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="pending", index=True) # "pending", "read", "replied", "resolved"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
