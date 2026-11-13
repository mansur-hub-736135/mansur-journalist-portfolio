
import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

AUTHOR = "Mansur Habibullah"

SOURCES = [
    (
        "Aaj Tak",
        "site:aajtak.in \"Mansur Habibullah\""
    ),
    (
        "India Today NE",
        "site:indiatodayne.in \"Mansur Habibullah\""
    ),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MansurPortfolioBot/1.0)"
}

def clean(value):
    text = BeautifulSoup(
        value or "",
        "html.parser"
    ).get_text(" ", strip=True)

    return re.sub(r"\s+", " ", text).strip()


def extract_author_names(soup):
    names = []

    selectors = [
        '[rel="author"]',
        '[class*="author" i]',
        '[itemprop="author"]',
        'meta[name*="author" i]',
        'meta[property="article:author"]'
    ]

    for tag in soup.select(",".join(selectors)):
        names.append(tag.get_text(" ", strip=True))
        names.append(tag.get("content", ""))

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )

            stack = data if isinstance(data, list) else [data]

            while stack:
                obj = stack.pop()

                if isinstance(obj, dict):
                    author = obj.get("author")

                    if isinstance(author, dict):
                        names.append(author.get("name", ""))

                    elif isinstance(author, list):
                        stack.extend(author)

                    elif author:
                        names.append(str(author))

                    stack.extend(
                        value for value in obj.values()
                        if isinstance(value, (dict, list))
                    )

                elif isinstance(obj, list):
                    stack.extend(obj)

        except (ValueError, TypeError):
            continue

    return " ".join(names).casefold()


def verify_publisher(host, publisher):
    host = host.lower().split(":")[0]

    if publisher == "Aaj Tak":
        return (
            host == "aajtak.in"
            or host.endswith(".aajtak.in")
        )

    if publisher == "India Today NE":
        return (
            host == "indiatodayne.in"
            or host.endswith(".indiatodayne.in")
        )

    return False


def get_article_details(url, publisher):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
            allow_redirects=True
        )

        if response.status_code != 200:
            return None

        host = urlparse(response.url).netloc

        if not verify_publisher(host, publisher):
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        authors = extract_author_names(soup)

        if AUTHOR.casefold() not in authors:
            return None

        title_tag = soup.find(
            "meta",
            property="og:title"
        )

        if title_tag:
            title = title_tag.get("content", "")
        elif soup.title:
            title = soup.title.get_text(" ", strip=True)
        else:
            title = ""

        desc = (
            soup.find(
                "meta",
                attrs={"name": "description"}
            )
            or soup.find(
                "meta",
                property="og:description"
            )
        )

        summary = desc.get("content", "") if desc else ""

        return {
            "title": clean(title),
            "url": response.url,
            "summary": clean(summary)[:220]
        }

    except requests.RequestException as error:
        print("Article request failed:", error)
        return None


def main():
    reports = []
    seen = set()

    for publisher, query in SOURCES:

        print("Searching:", publisher)

        feed_url = (
            "https://news.google.com/rss/search?q="
            + quote(query)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        try:
            response = requests.get(
                feed_url,
                headers=HEADERS,
                timeout=25
            )

            response.raise_for_status()

            root = ET.fromstring(response.content)

        except (
            requests.RequestException,
            ET.ParseError
        ) as error:

            print("Feed error:", publisher, error)
            continue

        items = root.findall(".//item")

        for item in items[:30]:

            link = item.findtext("link", "")

            if not link:
                continue

            article = get_article_details(
                link,
                publisher
            )

            if not article:
                continue

            final_url = article["url"]

            if final_url in seen:
                continue

            seen.add(final_url)

            pubdate = item.findtext("pubDate", "")

            try:
                date = parsedate_to_datetime(
                    pubdate
                ).astimezone(timezone.utc).isoformat()

            except (TypeError, ValueError):
                date = ""

            reports.append({
                "publisher": publisher,
                "title": article["title"],
                "url": final_url,
                "date": date,
                "summary": article["summary"]
            })

            print("Verified:", article["title"])

            time.sleep(0.5)

    reports.sort(
        key=lambda item: item.get("date", ""),
        reverse=True
    )

    output = {
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "reports": reports[:40]
    }

    with open(
        "reports.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "Total verified reports:",
        len(output["reports"])
    )


if __name__ == "__main__":
    main()
