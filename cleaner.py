import html2text
from bs4 import BeautifulSoup

def clean_html(html_content: str) -> str:
    """
    Converts raw HTML to clean Markdown, stripping unnecessary elements.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove unwanted tags
    # We can be aggressive here to reduce noise
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg", "header", "aside", "form"]):
        tag.decompose()
        
    # Initialize html2text
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_emphasis = False
    h.body_width = 0 # No wrapping
    
    # Convert
    markdown = h.handle(str(soup))
    
    return markdown.strip()
