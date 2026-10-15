import json
import datetime
import subprocess
import sys

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

today = datetime.date.today().strftime("%Y-%m-%d")
stock_list = []

url = "https://openapi.twse.com.tw/v1/fund/T86"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"正在連線證交所 OpenAPI: {url}")
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTTP 狀態碼: {response.status_code}")
    
    # 印出前 100 字元檢查實際回傳內容
    print(f"API 回傳內容預覽: {response.text[:100]}")
    
    if response.status_code == 200 and response.text.strip():
        data = response.json()
        print(f"成功取得資料，總筆數: {len(data)}")
        
        for item in data:
            try:
                code = str(item.get('Code', '')).strip().replace('=', '').replace('"', '')
                name = str(item.get('Name', '')).strip().replace('"', '')
                
                if code.isdigit() and len(code) == 4:
                    foreign = int(str(item.get('ForeignInvestorsNetBuySell', 0)).replace(',', '').replace('+', '').strip() or 0)
                    trust = int(str(item.get('InvestmentTrustNetBuySell', 0)).replace(',', '').replace('+', '').strip() or 0)
                    
                    dealer_self = str(item.get('DealerSelfNetBuySell', '0')).replace(',', '').replace('+', '').strip()
                    dealer_hedge = str(item.get('DealerHedgeNetBuySell', '0')).replace(',', '').replace('+', '').strip()
                    total_dealer = (int(dealer_self) if dealer_self.lstrip('-').isdigit() else 0) + \
                                   (int(dealer_hedge) if dealer_hedge.lstrip('-').isdigit() else 0)
                    
                    if total_dealer == 0:
                        dealer_total_str = str(item.get('DealerNetBuySell', '0')).replace(',', '').replace('+', '').strip()
                        total_dealer = int(dealer_total_str) if dealer_total_str.lstrip('-').isdigit() else 0

                    stock_list.append({
                        "code": code,
                        "name": name,
                        "foreign": foreign,
                        "trust": trust,
                        "self": total_dealer
                    })
            except Exception:
                continue
    else:
        print("API 回傳內容為空或伺服器異常。")
except Exception as e:
    print(f"發生例外錯誤: {e}")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已寫入 {len(stock_list)} 筆資料到 stock_data.json")
