import os, requests, time
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('SCREENER_URL')
headers = {"User-Agent": "Mozilla/5.0"}

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    stocks = []
    page = 1
    # 1. Scrape Screener safely
    while True:
        res = requests.get(f"{URL}?page={page}", headers=headers)
        if res.status_code != 200: break
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table')
        if not table: break
        rows = table.find('tbody').find_all('tr')
        if not rows: break
        
        added = 0
        for row in rows:
            a_tag = row.find('a')
            if a_tag and '/company/' in a_tag.get('href', ''):
                stocks.append({"Ticker": a_tag['href'].split('/')[2], "Name": a_tag.text.strip()})
                added += 1
        if added == 0: break
        page += 1
        time.sleep(1)

    if not stocks:
        send_telegram("⚠️ No stocks found. Check your Screener URL.")
        return

    # 2. Get Sectors from Yahoo Finance
    industry_counts = {}
    details = []
    for stock in stocks:
        try:
            industry = yf.Ticker(f"{stock['Ticker']}.NS").info.get('industry', 'Unknown')
        except:
            industry = 'Unknown'
            
        if industry != 'Unknown':
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
            stock['Industry'] = industry
            details.append(stock)
        time.sleep(0.3)

    # 3. Format and Send
    sorted_ind = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
    msg = f"📊 *Sector Breakout Heat-Map*\n_{datetime.now().strftime('%d %b %Y')}_\nTotal Stocks: {len(stocks)}\n\n"
    
    for ind, count in sorted_ind[:5]:
        msg += f"🔥 *{ind}* ({count} stocks)\n"
        examples = [s['Name'] for s in details if s['Industry'] == ind][:2]
        msg += f"   ↳ {', '.join(examples)}\n\n"
        
    send_telegram(msg)

if __name__ == "__main__":
    main()
