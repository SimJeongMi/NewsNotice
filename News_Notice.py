import os
import random
import datetime
import requests
import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# 환경 변수에서 웹후크 주소 로드
hook_exchange = os.environ.get('DISCORD_WEBHOOK')

# 1. 기술 블로그 포스팅 추출 (Medium RSS)
def get_tech_blog():
    url = "https://medium.com/feed/tag/software-engineering"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req).read()
        root = ET.fromstring(response)
        items = root.findall('.//item')
        if items:
            target = random.choice(items[:20])
            title = target.find('title').text
            link = target.find('link').text.split('?')[0]
            return f"📰 **오늘의 기술 읽을거리**\n**제목:** {title}\n**링크:** {link}\n"
    except:
        return "📰 기술 블로그 정보를 가져오지 못했습니다.\n"

# 2. 네이버 경제 뉴스 상위 10개 추출
def get_naver_economy_news():
    url = "https://news.naver.com/section/101"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = soup.select('.sa_text_title')
        
        if not news_items:
            return "💰 현재 경제 뉴스를 가져오지 못했습니다.\n"

        news_text = "💰 **현재 경제 뉴스 (상위 10개)**\n"
        for i, item in enumerate(news_items[:10], 1):
            title = item.get_text(strip=True)
            link = item.get('href')
            # 상대 경로일 경우 절대 경로로 보정
            if link and not link.startswith('http'):
                link = f"https://news.naver.com{link}"
            news_text += f"{i}. [{title}]({link})\n"
        return news_text + "\n"
    except Exception as e:
        return f"💰 뉴스 연결 실패: {str(e)}\n"

# 3. 메인 실행부
if __name__ == "__main__":
    # 한국 시간 기준 날짜 및 시간 생성 (UTC + 9시간)
    now_kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_date = now_kst.strftime("%Y년 %m월 %d일 %H시")

    blog_part = get_tech_blog()
    news_part = get_naver_economy_news()

    # 최종 메시지 구성 (알고리즘 파트 제거)
    full_content = f"🔔 **경제 뉴스 알림 도착 ({today_date})**\n\n"
    full_content += f"{blog_part}\n"
    full_content += f"{news_part}\n"

    # 전송 로직
    if hook_exchange and "http" in hook_exchange:
        payload = {
            "username": "데브 & 경제 알리미",
            "content": full_content
        }
        # 2000자 초과 방지
        if len(full_content) > 2000:
            payload["content"] = full_content[:1990] + "..."
            
        requests.post(hook_exchange, json=payload)
        print(f"{today_date} 알림 전송 완료!")
    else:
        print("웹후크 URL 환경 변수가 설정되지 않았습니다.")
