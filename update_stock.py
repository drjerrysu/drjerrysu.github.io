import json
import urllib.request
import datetime

today = datetime.date.today().strftime("%Y-%m-%d")
url = "https://www.twse.com.tw/zh/trading/foreign/t86?response=json"

req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)

stock_list = []

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        if 'data' in data:
            for row in data['data']:
                code = row[0].strip()
                name = row[1].strip()
                try:
                    foreign = int(row[4].replace(',', ''))
                    trust = int(row[10].replace(',', ''))
                    self_amt = int(row[15].replace(',', ''))
                    
                    stock_list.append({
                        "code": code,
                        "name": name,
                        "foreign": foreign,
                        "trust": trust,
                        "self": self_amt
                    })
                except ValueError:
                    continue
except Exception as e:
    print(f"抓取證交所資料發生錯誤: {e}")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"成功更新真實台股資料！共抓取 {len(stock_list)} 筆股票。")
