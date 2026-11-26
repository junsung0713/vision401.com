#!/usr/bin/env python3
"""Regenerate the static portfolio pages from the public caseData array in index.html."""

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://vision401.com"
ERP = "/services/erp-development/"
RENEWAL = "/services/website-renewal/"
GUIDE = "/guide/dev-outsourcing/"

# Editorial links are specific to the team's documented role in each project.
SERVICE_LINKS = {
    "muldream": [(RENEWAL, "브랜드 홈페이지 제작·리뉴얼 서비스")],
    "vetu1": [(ERP, "업무 화면과 운영 절차를 설계하는 맞춤형 ERP 개발")],
    "investy": [(ERP, "관리자 페이지와 백오피스 개발"), (RENEWAL, "기업 홈페이지 리뉴얼 서비스")],
}


def link(url, label):
    return f'<a href="{escape(url)}">{escape(label)}</a>'


def section(title, contents):
    return f'<section>\n<h2>{escape(title)}</h2>\n{contents}\n</section>'


def items(values):
    return "<ul>\n" + "\n".join(f"<li>{escape(value)}</li>" for value in values) + "\n</ul>"


def asset(source):
    return "/" + source.lstrip("/")


def metadata(case, url, title, image):
    breadcrumbs = [
        ("비전401", SITE + "/"),
        ("포트폴리오", SITE + "/#work"),
        (case["name"], url),
    ]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": url + "#webpage",
                "url": url,
                "name": title,
                "description": case["overview"],
                "inLanguage": "ko-KR",
                "isPartOf": {"@id": SITE + "/#website"},
                "breadcrumb": {"@id": url + "#breadcrumb"},
                "publisher": {"@id": SITE + "/#organization"},
                "primaryImageOfPage": image,
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": i, "name": name, "item": path}
                    for i, (name, path) in enumerate(breadcrumbs, 1)
                ],
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")


def project_details(case):
    facts = [
        ("프로젝트", case["client"]),
        ("기간", case["period"]),
        ("담당 역할", case["role"]),
        ("작업 범위", " · ".join(case["scope"])),
        ("기술", ", ".join(case["stack"])),
    ]
    rows = "\n".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
        for label, value in facts if value
    )
    return section("프로젝트 정보", f'<dl class="facts">\n{rows}\n</dl>')


def image_figure(pic, name, loading):
    source = asset(pic["src"])
    caption = escape(pic["caption"])
    return (
        f'<figure class="{escape(pic["kind"])}"><a href="{escape(source)}">'
        f'<img loading="{loading}" decoding="async" src="{escape(source)}" '
        f'width="{int(pic["w"])}" height="{int(pic["h"])}" '
        f'alt="{escape(name)} · {caption}"></a><figcaption>{caption}</figcaption></figure>'
    )


def cover_media(case):
    hero = case["hero"]
    if hero["type"] == "logo":
        return (
            f'<div class="case-logo" style="background:{escape(hero["bg"])};padding:3rem;text-align:center">'
            f'<img src="{escape(hero["src"])}" alt="{escape(case["name_en"])}" width="200"></div>',
            set(),
        )
    sources = hero["srcs"] if hero["type"] == "phones" else [hero["src"]]
    indexed = {pic["src"]: pic for pic in case["images"]}
    covers = [image_figure(indexed[src], case["name"], "eager") for src in sources]
    kind = "case-phones" if hero["type"] == "phones" else "case-cover"
    return f'<div class="gallery {kind}">' + "\n".join(covers) + "</div>", set(sources)


def gallery(case, used):
    figures = []
    for pic in case["images"]:
        if pic["src"] not in used:
            figures.append(image_figure(pic, case["name"], "lazy"))
    if not figures:
        return ""
    return section("프로젝트 화면", '<div class="gallery">\n' + "\n".join(figures) + "\n</div>")


def design_details(case):
    parts = []
    if case["typography"]:
        fonts = []
        for font in case["typography"]:
            fonts.append(
                f'<h4>{escape(font["family"])}</h4><p>{escape(font["where"])} · '
                f'{escape(font["weights"])}</p>{items(font["why"])}'
            )
        parts.append("<h3>글꼴</h3>" + "\n".join(fonts))
    if case["colors"]:
        swatches = []
        for swatch in case["colors"]:
            color = escape(swatch["hex"])
            swatches.append(
                f'<li><span aria-hidden="true" class="swatch" style="background-color:{color}"></span> '
                f'{escape(swatch["name"])} ({color}) · {escape(swatch["where"])}</li>'
            )
        parts.append('<h3>색상</h3><ul>' + "\n".join(swatches) + "</ul>")
    if not parts:
        return ""
    return '<details class="design-notes"><summary>화면 디자인 상세</summary>\n' + "\n".join(parts) + "\n</details>"


def render(case, following):
    slug = case["slug"]
    url = f"{SITE}/work/{slug}/"
    title = f'{case["name"]} · {case["summary"]} | 비전401'
    hero = case["hero"]
    image = "/og.png"
    if case["images"]:
        cover = hero["src"] if hero["type"] == "image" else case["images"][0]["src"]
        image = asset(cover)
    cover_html, cover_sources = cover_media(case)
    body = [project_details(case)]
    if case.get("quote"):
        quote = case["quote"]
        body.append(f'<blockquote><p>{escape(quote["text"])}</p><cite>{escape(quote["by"])}</cite></blockquote>')
    if case["problem"]:
        body.append(section("해결할 과제", items(case["problem"])))
    if case.get("platforms"):
        platforms = [
            f'{entry["name"]} · {entry["period"]} · {entry["role"]}'
            for entry in case["platforms"]
        ]
        body.append(section(
            f'담당 플랫폼 {len(platforms)}종',
            items(platforms) + f'<p>{escape(case["platformsNote"])}</p>',
        ))
    if case["approach"]:
        body.append(section(case.get("approachTitle", "구현한 내용"), items(case["approach"])))
    if case["images"]:
        body.append(gallery(case, cover_sources))
    body.append(design_details(case))
    if case["links"]:
        links = "\n".join(f'<li>{link(ref["url"], ref["label"])}</li>' for ref in case["links"])
        body.append(section("공개 서비스와 자료", '<ul class="related">\n' + links + "\n</ul>"))
    related = SERVICE_LINKS.get(slug, []) + [
        (GUIDE, "개발 외주를 맡기는 방법과 업체 비교"),
        (f'/work/{following["slug"]}/', f'다음 사례 · {following["name"]}'),
        ("/#work", "전체 포트폴리오 보기"),
    ]
    related_links = "\n".join(f"<li>{link(path, label)}</li>" for path, label in related)
    body.append(section("관련 서비스와 사례", '<ul class="related">\n' + related_links + "\n</ul>"))
    article = "\n".join(block for block in body if block)
    title_tag = escape(title)
    description = escape(case["overview"])
    name = escape(case["name"])
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_tag}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.ico">
<meta property="og:type" content="article">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="비전401 (Vision401)">
<meta property="og:title" content="{title_tag}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}{image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/assets/detail.css">
<script type="application/ld+json">{metadata(case, url, title, SITE + image)}</script>
</head>
<body>
<header class="site-header"><div class="wrap">
<a class="brand" href="/">VISION 401</a>
<nav aria-label="주 메뉴"><a href="/#work">포트폴리오</a> <a href="{GUIDE}">개발 외주 가이드</a> <a href="/#contact">문의</a></nav>
</div></header>
<main class="wrap">
<nav class="breadcrumb" aria-label="현재 위치"><a href="/">홈</a> <span aria-hidden="true">/</span> <a href="/#work">포트폴리오</a> <span aria-hidden="true">/</span> <span aria-current="page">{name}</span></nav>
<header class="page-intro">
<p class="kicker">{escape(case["summary"])}</p>
<h1>{name}</h1>
<p class="lead">{description}</p>
</header>
{cover_html}
{article}
</main>
<footer class="site-footer"><div class="wrap"><a class="brand" href="/">VISION 401</a> <a href="/#contact">프로젝트 문의</a></div></footer>
</body>
</html>
"""


def main():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<script\b[^>]*\bid="caseData"[^>]*>(.*?)</script>', home, re.DOTALL)
    if block is None:
        raise ValueError("The caseData JSON block is missing from index.html")
    cases = json.loads(block.group(1))
    for i, case in enumerate(cases):
        directory = ROOT / "work" / case["slug"]
        directory.mkdir(parents=True, exist_ok=True)
        page = render(case, cases[(i + 1) % len(cases)])
        (directory / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
