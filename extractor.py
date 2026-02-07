from bs4 import BeautifulSoup
from typing import Union, List, Optional
from datetime import datetime
from src.schemas import ArticleSchema, GeneralPageSchema, LinkItem, Entities

async def extract_metadata(markdown_content: str, html_content: str, url: str) -> Union[ArticleSchema, GeneralPageSchema]:
    """
    Extracts structured data using heuristic rules on the HTML content.
    No LLMs involved. Fast and free.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Common Metadata Extraction
    title = _get_title(soup)
    description = _get_description(soup)
    authors = _get_authors(soup)
    published_date = _get_published_date(soup)
    canonical_url = _get_canonical_url(soup) or url

    # Decision Logic: precise "article" detection is hard without LLM, 
    # but we can assume if there's a substantial markdown body, it's an "article".
    # Or we can just default to ArticleSchema if we have a title and content.
    
    # Let's try to return ArticleSchema effectively always, unless it looks like a list/homepage.
    # Simple heuristic: word count of markdown > 200 words -> Article. Else -> General Page.
    word_count = len(markdown_content.split())
    
    if word_count > 200:
        return ArticleSchema(
            url=url,
            title=title or "Untitled Page",
            subtitle=description, # Use description as subtitle fallback
            authors=authors,
            published_date=published_date,
            main_text=markdown_content,
            summary=description,
            entities=Entities(), # Empty for now as we don't have NER
            canonical_url=canonical_url,
            topics=[],
            word_count=word_count,
            type="article"
        )
    else:
        # It's likely a nav page or empty page
        headlines = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])][:10]
        links = []
        seen_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if text and href and href not in seen_links:
                links.append(LinkItem(text=text, url=href))
                seen_links.add(href)
            if len(links) >= 20:
                break
                
        return GeneralPageSchema(
            url=url,
            title=title or "Untitled Page",
            description=description,
            headlines=headlines,
            links=links,
            topics=[],
            type="general_page"
        )

def _get_title(soup: BeautifulSoup) -> Optional[str]:
    # 1. OG Title
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    # 2. Twitter Title
    meta = soup.find("meta", attrs={"name": "twitter:title"})
    if meta and meta.get("content"):
        return meta["content"].strip()
        
    # 3. <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()
        
    # 4. H1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
        
    return None

def _get_description(soup: BeautifulSoup) -> Optional[str]:
    # 1. OG Description
    meta = soup.find("meta", property="og:description")
    if meta and meta.get("content"):
        return meta["content"].strip()
        
    # 2. Meta Description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
        
    return None

def _get_authors(soup: BeautifulSoup) -> List[str]:
    authors = []
    
    # 1. Meta Authors
    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name")
        if prop in ["author", "article:author", "book:author"]:
            content = meta.get("content")
            if content:
                authors.append(content.strip())
                
    # 2. Rel=author links
    for a in soup.find_all("a", rel="author"):
        actions = a.get_text(strip=True)
        if actions:
            authors.append(actions)
            
    return list(set(authors))

def _get_published_date(soup: BeautifulSoup) -> Optional[datetime]:
    # Very basic string check
    date_str = None
    
    # 1. Article Published Time
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        date_str = meta["content"]
        
    if not date_str:
        meta = soup.find("meta", attrs={"name": "date"})
        if meta and meta.get("content"):
            date_str = meta["content"]
            
    if date_str:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            pass
            
    return None

def _get_canonical_url(soup: BeautifulSoup) -> Optional[str]:
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return link["href"]
    return None
