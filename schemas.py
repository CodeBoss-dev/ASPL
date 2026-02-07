from typing import List, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class DateEntity(BaseModel):
    raw: str
    normalized: Optional[str] = None

class Entities(BaseModel):
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    dates: List[DateEntity] = Field(default_factory=list)

class ArticleSchema(BaseModel):
    url: str
    title: str
    subtitle: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    main_text: str
    summary: Optional[str] = None
    entities: Entities = Field(default_factory=Entities)
    canonical_url: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    word_count: int
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str = "article"

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Example Article",
                "main_text": "This is the content...",
                "word_count": 5,
                "fetched_at": "2023-10-27T10:00:00Z",
                "type": "article"
            }
        }

class LinkItem(BaseModel):
    text: str
    url: Optional[str] = None

class GeneralPageSchema(BaseModel):
    url: str
    title: str
    description: Optional[str] = None
    headlines: List[str] = Field(default_factory=list)
    links: List[LinkItem] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str = "general_page"
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/home",
                "title": "Example Homepage",
                "description": "Main landing page...",
                "headlines": ["Breaking News 1", "Feature Story 2"],
                "fetched_at": "2023-10-27T10:00:00Z",
                "type": "general_page"
            }
        }

class MonitoredSource(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    url: str
    type: str = "article_page"
    last_checked_at: Optional[datetime] = None
    last_content_hash: Optional[str] = None

class MonitoredSourceRequest(BaseModel):
    url: str
    type: str = "article_page"

class ChangeEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    url: str
    source_id: Optional[UUID] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    old_hash: Optional[str] = None
    new_hash: str
    change_type: str = "content_updated"
    current_article: Optional[Union[ArticleSchema, GeneralPageSchema]] = None

class Subscriber(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    callback_url: str
    url_prefix_filter: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    failure_count: int = 0
    is_active: bool = True

class SubscriberRequest(BaseModel):
    callback_url: str
    url_prefix_filter: Optional[str] = None
