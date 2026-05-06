import os
import feedparser
import requests
from slack_sdk import WebClient
import ssl
import certifi
import time
from datetime import datetime, timezone, timedelta
import urllib.parse

# SSL 설정
ssl_context = ssl.create_default_context(cafile=certifi.where())

# 설정값들 - 환경변수에서 가져오기
SLACK_TOKEN = os.getenv('SLACK_TOKEN')
CHANNEL = os.getenv('SLACK_CHANNEL', '#all-ta-re_news')

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 디버깅: 환경변수 확인
print("=== 환경변수 디버깅 ===")
print(f"SLACK_TOKEN: {SLACK_TOKEN[:15] + '...' if SLACK_TOKEN else 'None'}")
print(f"SLACK_CHANNEL: {CHANNEL}")
print("========================")

class NewsBot:
    def __init__(self):
        self.slack_client = WebClient(token=SLACK_TOKEN, ssl=ssl_context)
        self.companies = ['네이버', '카카오', '쿠팡', '배민', '당근', '토스']
    
    def get_google_news_rss(self, query, count=3):
        """Google News RSS로 뉴스 가져오기"""
        try:
            print(f"  📱 {query} 뉴스 검색 중...")
            
            # URL 인코딩
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
            
            # RSS 파싱
            feed = feedparser.parse(rss_url)
            
            news_list = []
            for entry in feed.entries[:count]:
                news_list.append({
                    'title': entry.title,
                    'link': entry.link
                })
            
            return news_list
        except Exception as e:
            print(f"  ❌ {query} 뉴스 검색 실패: {e}")
            return []
    
    def get_company_news(self, company, count=3):
        """특정 회사 뉴스 가져오기"""
        return self.get_google_news_rss(company, count)
    
    def get_job_news(self, count=5):
        """채용 뉴스 가져오기"""
        return self.get_google_news_rss('채용 구인', count)
    
    def create_message(self, all_news):
        """슬랙 메시지 생성"""
        # 한국 시간으로 날짜 가져오기
        kst_now = datetime.now(KST)
        message = f"📰 *IT 뉴스 브리핑* - {kst_now.strftime('%m/%d')}\n\n"
        
        # 회사별 뉴스
        for company in self.companies:
            if company in all_news and all_news[company]:
                message += f"*🏢 {company}*\n"
                for news in all_news[company]:
                    title = news['title'][:60] + "..." if len(news['title']) > 60 else news['title']
                    message += f"• <{news['link']}|{title}>\n"
                message += "\n"
        
        # 채용 뉴스
        if 'jobs' in all_news and all_news['jobs']:
            message += "*💼 채용 정보*\n"
            for news in all_news['jobs']:
                title = news['title'][:60] + "..." if len(news['title']) > 60 else news['title']
                message += f"• <{news['link']}|{title}>\n"
        
        return message
    
    def send_to_slack(self, message):
        """슬랙으로 전송"""
        try:
            response = self.slack_client.chat_postMessage(
                channel=CHANNEL,
                text=message,
                mrkdwn=True,
                unfurl_links=False,  
                unfurl_media=False  
            )
            return response["ok"]
        except Exception as e:
            print(f"❌ 슬랙 전송 실패: {e}")
            return False
    
    def run(self):
        """전체 뉴스봇 실행"""
        print("🚀 뉴스봇 시작!")
        print("🔍 뉴스 수집 중...")
        
        all_news = {}
        
        # 회사별 뉴스 수집 (각 3개씩)
        for company in self.companies:
            all_news[company] = self.get_company_news(company, 3)
            time.sleep(1)  # API 제한 방지
        
        # 채용 뉴스 수집 (5개)
        all_news['jobs'] = self.get_job_news(5)
        
        # 메시지 생성 및 전송
        message = self.create_message(all_news)
        
        if self.send_to_slack(message):
            print("✅ 뉴스 전송 완료!")
        else:
            print("❌ 뉴스 전송 실패")

if __name__ == "__main__":
    bot = NewsBot()
    bot.run()
