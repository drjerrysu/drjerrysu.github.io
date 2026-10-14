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

# 改用證交所最穩定的 Open Data CSV 下載點（專供自動化與程式串接使用）
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=csv&selectType=all"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

stock_list = []

try:
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        lines = content.splitlines()
        
        for line in lines:
            # 略過標題與非數據行
            if '"' in line or ',' in line:
                parts = [p.strip().replace('"', '') for p in line.split(',')]
                if len(parts) >= 16:
                    code = parts[0].replace('=', '')
                    name = parts[1]
                    
                    if code.isdigit() and len(code) == 4:
                        try:
                            foreign = int(parts[4].replace(',', '').replace('+', ''))
                            trust = int(parts[10].replace(',', '').replace('+', ''))
                            self_amt = int(parts[15].replace(',', '').replace('+', ''))
                            
                            stock_list.append({
                                "code": code,
                                "name": name,
                                "foreign": foreign,
                                "trust": trust,
                                "self": self_amt
                            })
                        except (ValueError, IndexError):
                            continue
        print(f"成功解析真實上市股票，共 {len(stock_list)} 筆")
    else:
        print(f"請求失敗，狀態碼: {response.status_code}")
except Exception as e:
    print(f"發生例外錯誤: {e}")

# 如果真的抓不到，改從另一個備用官方 JSON 端點抓取
if len(stock_list) == 0:
    print("嘗試備用 JSON 端點...")
    try:
        json_url = "https://www.twse.com.tw/zh/trading/foreign/t86?response=json&selectType=all"
        res = requests.get(json_url, headers=headers, timeout=20)
        if res.status_code == 200:
            jdata = res.json()
            if 'data' in jdata:
                for row in jdata['data']:
                    code = str(row[0]).strip().replace('=', '').replace('"', '')
                    name = str(row[1]).strip().replace('"', '')
                    if code.isdigit() and len(code) == 4:
                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": int(str(row[4]).replace(',', '').replace('+', '')),
                            "trust": int(str(row[10]).replace(',', '').replace('+', '')),
                            "self": int(str(row[15]).replace(',', '').replace('+', '')) if len(row) > 15 else 0
                        })
                print(f"備用端點成功取得 {len(stock_list)} 筆資料")
    except Exception as je:
        print(f"備用端點也失敗: {je}")

if len(stock_list) == 0:
    raise ValueError("錯誤：無法取得任何證交所真實資料！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功寫入 {len(stock_list)} 筆真實數據到 stock_data.json")
