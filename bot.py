import os, requests, time
from bs4 import BeautifulSoup
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = os.environ.get('SCREENER_URL')
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})

def main():
    print("Scraping Screener...")
    stocks = []
    seen = set()
    page = 1
    
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
                ticker = a_tag['href'].split('/')[2]
                if ticker in seen: continue
                seen.add(ticker)
                stocks.append({"Ticker": ticker, "Name": a_tag.text.strip()})
                added += 1
                
        if added == 0: break
        page += 1
        time.sleep(0.5)

    if not stocks:
        return

    print("Analyzing Sectors and Volume Surges...")
    details = []
    sector_counts = {}
    session = requests.Session()
    session.headers.update(headers)
    
    for i, stock in enumerate(stocks):
        try:
            info = yf.Ticker(f"{stock['Ticker']}.NS", session=session).info
            sector = info.get('sector', 'Unknown')
            if sector == 'Unknown':
                info = yf.Ticker(f"{stock['Ticker']}.BO", session=session).info
                sector = info.get('sector', 'Unknown')
            
            # Calculate Volume Surge (Today's Vol / Avg Vol)
            vol = info.get('volume', 0)
            avg_vol = info.get('averageVolume', 1)
            surge = round(vol / avg_vol, 1) if avg_vol and avg_vol > 0 else 0
            
        except:
            sector, surge = 'Unknown', 0
            
        if sector != 'Unknown':
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            stock['Sector'] = sector
            stock['Surge'] = surge
            details.append(stock)
            
        time.sleep(0.2)

    # 1. Create the Visual Chart Image
    print("Drawing Chart...")
    sorted_sec = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    sectors = [x[0] for x in sorted_sec]
    counts = [x[1] for x in sorted_sec]
    
    plt.figure(figsize=(10, 6))
    plt.barh(sectors[::-1], counts[::-1], color='#4C72B0')
    plt.xlabel('Number of Breakout Stocks')
    plt.title(f'Sector Heat-Map - {datetime.now().strftime("%d %b %Y")}')
    plt.tight_layout()
    plt.savefig('heatmap.png')

    # 2. Format the Actionable Caption
    print("Formatting Actionable Data...")
    caption = f"📊 *Macro Sector Heat-Map*\nTotal Breakouts: {len(stocks)}\n\n"
    
    # Sort stocks by volume surge to find the true leaders
    details.sort(key=lambda x: x['Surge'], reverse=True)
    
    for sec, count in sorted_sec[:5]:
        caption += f"🔥 *{sec}* ({count} stocks)\n"
        # Find top 2 stocks in this sector by volume surge
        leaders = [s for s in details if s['Sector'] == sec][:2]
        for leader in leaders:
            caption += f"   - {leader['Name']} (Vol Surge: {leader['Surge']}x)\n"
        caption += "\n"
        
    print("Sending Image to Telegram...")
    send_telegram_photo('heatmap.png', caption)
    print("Done!")

if __name__ == "__main__":
    main()
