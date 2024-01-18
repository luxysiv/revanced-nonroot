from src import session
from selectolax.lexbor import LexborHTMLParser

def get_download_page(version: str) -> str:
    url = (
        f"https://www.apkmirror.com/apk/google-inc/youtube/youtube"
        + f"-{version.replace('.', '-')}-release/"
    )
    parser = LexborHTMLParser(session.get(url, timeout=10).text)

    apm = parser.css(".apkm-badge")

    sub_url = ""
    for is_apm in apm:
        parent_text = is_apm.parent.parent.text()

        if "APK" in is_apm.text() and (
            "arm64-v8a" in parent_text
            or "universal" in parent_text
            or "noarch" in parent_text
        ):
            parser = is_apm.parent
            sub_url = parser.css_first(".accent_color").attributes["href"]
            break
    if sub_url == "":
        raise Exception("No download page found")

    yt_apk_page = "https://www.apkmirror.com" + sub_url
    return yt_apk_page

def extract_download_link(page: str) -> None:
    parser = LexborHTMLParser(session.get(page).text)

    resp = session.get(
        "https://www.apkmirror.com"
        + parser.css_first("a.accent_bg").attributes["href"]
    )
    parser = LexborHTMLParser(resp.text)

    href = parser.css_first(
        "p.notes:nth-child(3) > span:nth-child(1) > a:nth-child(1)"
    ).attributes["href"]

    apk_link = "https://www.apkmirror.com" + href
    return apk_link
    
