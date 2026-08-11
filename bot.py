import os, requests, time, re
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('SCREENER_URL')
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    print("Starting Screener scrape...")
    stocks = []
    seen = set()
    page = 1
    
    # 1. Scrape all pages of your screen (up to 20 pages)
    while page <= 20:
        print(f"Fetching page {page} from Screen...")
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
                # Prevent infinite loops if pagination breaks
                if ticker in seen: continue
                seen.add(ticker)
                stocks.append({"Ticker": ticker, "Name": a_tag.text.strip()})
                added += 1
                
        if added == 0: break
        page += 1
        time.sleep(1)

    print(f"Found {len(stocks)} total stocks.")
    
    if not stocks:
        send_telegram("No stocks found. Check if your Screener URL is Public.")
        return

    print("Fetching industry data directly from Screener...")
    industry_counts = {}
    details = []
    
    # 2. Visit every individual company page to get the exact sector
    for i, stock in enumerate(stocks):
        industry = "Unknown"
        try:
            company_url = f"https://www.screener.in/company/{stock['Ticker']}/"
            c_res = requests.get(company_url, headers=headers)
            
            if c_res.status_code == 200:
                c_soup = BeautifulSoup(c_res.text, 'html.parser')
                
                # Look for the Industry link in Screener's HTML
                ind_tag = c_soup.find('a', href=re.compile(r'/explore/industry/'))
                if ind_tag:
                    industry = ind_tag.text.strip()
                else:
                    # Fallback to Sector if Industry is missing
                    sec_tag = c_soup.find('a', href=re.compile(r'/explore/sector/'))
                    if sec_tag:
                        industry = sec_tag.text.strip()
        except:
            pass
            
        if industry != "Unknown":
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
            stock['Industry'] = industry
            details.append(stock)
            
        # Print progress to logs
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(stocks)} stocks...")
            
        # Mandatory 1-second delay so Screener does not block the bot
        time.sleep(1)

    print("Formatting message...")
    sorted_ind = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
    
    # 3. Clean text formatting (No Emojis)
    msg = f"*Sector Breakout Heat-Map*\n_{datetime.now().strftime('%d %b %Y')}_\nTotal Breakouts: {len(stocks)}\n\n"
    
    for ind, count in sorted_ind[:5]:
        msg += f"*{ind}* ({count} stocks)\n"
        examples = [s['Name'] for s in details if s['Industry'] == ind][:3]
        msg += f"   - {', '.join(examples)}\n\n"
        
    print("Sending text to Telegram...")
    send_telegram(msg)
    print("Done!")

if __name__ == "__main__":
    main()
