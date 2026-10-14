import json
import datetime
import subprocess
import sys

# 自動確保安裝 requests 庫以確保請求成功率
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

today = datetime.date.today().strftime("%Y-%m-%d")

# 證交所三大法人買賣超官方 JSON API（加入 selectType=all 抓取全市場）
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=all"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.twse.com.tw/zh/trading/foreign/t86.html',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
}

stock_list = []

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and data['data']:
            print(f"成功取得 API 資料，共 {len(data['data'])} 筆")
            for row in data['data']:
                try:
                    # 代號在 index 0，名稱在 index 1
                    code = str(row[0]).strip().replace('=', '').replace('"', '')
                    name = str(row[1]).strip().replace('"', '')
                    
                    if code.isdigit() and len(code) == 4:
                        # 根據證交所 T86 標準 JSON 欄位：
                        # [4] 外陸資買賣超張數
                        # [10] 投信買賣超張數
                        # [15] 自營商買賣超張數
                        foreign = int(str(row[4]).replace(',', '').replace('+', '').strip())
                        trust = int(str(row[10]).replace(',', '').replace('+', '').strip())
                        
                        self_amt = 0
                        if len(row) > 15:
                            val_str = str(row[15]).replace(',', '').replace('+', '').strip()
                            if val_str.lstrip('-').isdigit():
                                self_amt = int(val_str)

                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                except Exception as parse_err:
                    continue
        else:
            print(f"API 回傳內容無資料結構: {data}")
    else:
        print(f"請求失敗，狀態碼: {response.status_code}")
except Exception as e:
    print(f"發生例外錯誤: {e}")

if len(stock_list) == 0:
    raise ValueError("錯誤：抓取到的股票清單為空！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功寫入 {len(stock_list)} 筆真實股票數據到 stock_data.json")
