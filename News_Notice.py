import os
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

hook_exchange = os.environ.get('DISCORD_WEBHOOK')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}
TOP_N = 10


# 기사 URL에서 oid, aid 추출 (예: https://n.news.naver.com/mnews/article/015/0005012345)
def parse_ids(link):
    m = re.search(r'/article/(\d+)/(\d+)', link)
    return (m.group(1), m.group(2)) if m else (None, None)


# 기사별 댓글 수 조회
def get_comment_count(link):
    oid, aid = parse_ids(link)
    if not oid:
        return 0
    api = "https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
    params = {
        "ticket": "news",
        "templateId": "default_economy",
        "pool": "cbox5",
        "lang": "ko",
        "country": "KR",
        "objectId": f"news{oid},{aid}",
        "pageSize": 1,
        "page": 1,
        "_callback": "cb",
    }
    headers = {**HEADERS, "Referer": link}  # Referer 없으면 거부됨
    try:
        res = requests.get(api, params=params, headers=headers, timeout=5)
        text = res.text
        data = json.loads(text[text.find('(') + 1: text.rfind(')')])
        return data.get("result", {}).get("count", {}).get("comment", 0)
    except Exception:
        return 0


# 네이버 경제 섹션 기사 수집 (페이지 노출 순서 유지, 댓글 수 포함)
def fetch_articles():
    url = "https://news.naver.com/section/101"
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')

    articles, seen = [], set()
    for item in soup.select('.sa_text_title'):
        link = item.get('href')
        if not link:
            continue
        if not link.startswith('http'):
            link = f"https://news.naver.com{link}"
        if link in seen:
            continue
        seen.add(link)
        articles.append({"title": item.get_text(strip=True), "link": link})

    with ThreadPoolExecutor(max_workers=8) as ex:
        counts = list(ex.map(lambda a: get_comment_count(a["link"]), articles))
    for a, c in zip(articles, counts):
        a["comments"] = c
    return articles


# 목록 → 디스코드 메시지 텍스트
def format_section(header, articles):
    text = f"{header}\n"
    for i, a in enumerate(articles[:TOP_N], 1):
        text += f"{i}. [{a['title']}](<{a['link']}>) 💬 {a['comments']:,}\n"
    return text


def send(content):
    if len(content) > 2000:
        content = content[:1990] + "..."
    requests.post(hook_exchange, json={"username": "경제 뉴스 알리미", "content": content})


if __name__ == "__main__":
    now_kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_date = now_kst.strftime("%Y년 %m월 %d일 %H시")

    try:
        articles = fetch_articles()
        if not articles:
            messages = ["💰 현재 경제 뉴스를 가져오지 못했습니다."]
        else:
            latest = format_section(f"💰 **현재 경제 뉴스 (상위 {TOP_N}개)**", articles)
            by_comments = sorted(articles, key=lambda a: a["comments"], reverse=True)
            popular = format_section(f"🔥 **댓글 많은 경제 뉴스 (상위 {TOP_N}개)**", by_comments)
            messages = [latest, popular]
    except Exception as e:
        messages = [f"💰 뉴스 연결 실패: {e}"]

    messages[0] = f"🔔 **경제 뉴스 알림 도착 ({today_date})**\n\n" + messages[0]

    if hook_exchange and "http" in hook_exchange:
        for msg in messages:  # 2000자 제한 때문에 섹션별로 따로 전송
            send(msg)
        print(f"{today_date} 뉴스 전송 완료!")
    else:
        print("웹후크 URL 환경 변수가 설정되지 않았습니다.")
