import json
import datetime
import subprocess
import sys
import os

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

today = datetime.date.today().strftime("%Y-%m-%d")

# 先嘗試讀取現有的 stock_data.json，若伺服器暫時沒資料時可作為備用
old_data = []
if os.path.exists("stock_data.json"):
    try:
        with open("stock_data.json", "r", encoding="utf-8") as f:
            content = json.load(f)
            old_data = content.get("data", [])
    except:
        pass

url = "https://openapi.twse.com.tw/v1/fund/T86"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

stock_list = []

try:
    print(f"正在連線證交所 OpenAPI: {url}")
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTTP 狀態碼: {response.status_code}")
    
    # 檢查內容是否為空，避免發生 JSONDecodeError
    response_text = response.text.strip()
    if response.status_code == 200 and response_text:
        data = response.json()
        print(f"成功取得原始資料，共 {len(data)} 筆")
        
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
        print("提示：證交所伺服器目前回傳內容為空（可能尚未到每日結算時間）。")
except Exception as e:
    print(f"發生例外錯誤: {e}")

# 防呆機制：若本次抓不到新資料，自動沿用舊資料，確保系統平穩
if len(stock_list) == 0 and len(old_data) > 0:
    print("提示：本次未取得新資料，沿用上一筆有效數據，確保前端正常顯示。")
    stock_list = old_data

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功更新 stock_data.json，總計筆數: {len(stock_list)}")
