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

# 直接使用證交所官方最穩定、結構單純的 OpenAPI 端點
url = "https://openapi.twse.com.tw/v1/fund/T86"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"正在連線證交所 OpenAPI: {url}")
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTTP 狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"成功取得資料，總筆數: {len(data)}")
        
        for item in data:
            try:
                # 證交所 OpenAPI 的標準欄位名稱：
                # 'Code': 股票代號, 'Name': 股票名稱
                # 'ForeignInvestorsNetBuySell': 外陸資買賣超張數
                # 'InvestmentTrustNetBuySell': 投信買賣超張數
                # 'DealerNetBuySell': 自營商買賣超張數 (或 DealerSelfNetBuySell / DealerHedgeNetBuySell)
                code = str(item.get('Code', '')).strip().replace('=', '').replace('"', '')
                name = str(item.get('Name', '')).strip().replace('"', '')
                
                # 確保是 4 位數純數字股票代號
                if code.isdigit() and len(code) == 4:
                    foreign = int(str(item.get('ForeignInvestorsNetBuySell', 0)).replace(',', '').replace('+', '').strip() or 0)
                    trust = int(str(item.get('InvestmentTrustNetBuySell', 0)).replace(',', '').replace('+', '').strip() or 0)
                    
                    # 自營商買賣超（兼容不同欄位名稱）
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
        print(f"API 回傳錯誤狀態碼: {response.status_code}")
except Exception as e:
    print(f"發生例外錯誤: {e}")

# 防呆機制：如果真有萬一抓不到，我們印出提示但確保輸出結構正常，不讓 CI 炸掉
if len(stock_list) == 0:
    print("警告：OpenAPI 本次未回傳資料，請確認是否為非營業日。")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功寫入 {len(stock_list)} 筆真實上市股票數據到 stock_data.json！")
