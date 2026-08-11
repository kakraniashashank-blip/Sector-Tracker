import os, requests, time
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('SCREENER_URL')
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    print("Starting scraper...")
    stocks = []
    seen = set()
    page = 1
    
    # 1. Scrape all pages dynamically (No Limits)
    while True:
        print(f"Fetching page {page}...")
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
                ticker = a_tag['href'].split('/')[2]
                if ticker in seen: continue
                seen.add(ticker)
                stocks.append({"Ticker": ticker, "Name": a_tag.text.strip()})
                added += 1
                
        if added == 0: break
        page += 1
        time.sleep(0.5)

    print(f"Found {len(stocks)} total stocks.")
    
    if not stocks:
        send_telegram("No stocks found. Check if your Screener URL is Public.")
        return

    industry_counts = {}
    details = []
    
    # 2. Use Yahoo Finance for ALL stocks (No limits)
    # Using a custom session prevents Yahoo from blocking the bot
    session = requests.Session()
    session.headers.update(headers)
    
    for i, stock in enumerate(stocks):
        try:
            # Try NSE first (.NS)
            ticker_obj = yf.Ticker(f"{stock['Ticker']}.NS", session=session)
            industry = ticker_obj.info.get('industry', 'Unknown')
            
            # Fallback for BSE-only stocks (.BO)
            if industry == 'Unknown':
                ticker_obj = yf.Ticker(f"{stock['Ticker']}.BO", session=session)
                industry = ticker_obj.info.get('industry', 'Unknown')
                
        except:
            industry = 'Unknown'
            
        if industry != 'Unknown':
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
            stock['Industry'] = industry
            details.append(stock)
            
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(stocks)} stocks...")
            
        time.sleep(0.2) # Fast but safe delay

    print("Formatting message...")
    sorted_ind = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
    msg = f"*Sector Breakout Heat-Map*\n_{datetime.now().strftime('%d %b %Y')}_\nTotal Breakouts: {len(stocks)}\n\n"
    
    # 3. Clean text formatting (No Emojis)
    for ind, count in sorted_ind[:5]:
        msg += f"*{ind}* ({count} stocks)\n"
        examples = [s['Name'] for s in details if s['Industry'] == ind][:3]
        msg += f"   - {', '.join(examples)}\n\n"
        
    print("Sending text to Telegram...")
    send_telegram(msg)
    print("Done!")

if __name__ == "__main__":
    main()
