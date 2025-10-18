from bs4 import BeautifulSoup

def extract_visible_text_from_html(html):
    """
    Extract and return visible text from HTML using BeautifulSoup.
    """
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text(separator=" ")
    return " ".join(text.split())  # Collapse multiple spaces