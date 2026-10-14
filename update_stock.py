import json
import urllib.request
import datetime

today = datetime.date.today().strftime("%Y-%m-%d")

# 直接使用證交所官方的 JSON 格式 API 端點
url = "https://www.twse.com.tw/zh/trading/foreign/t86?response=json"

req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.twse.com.tw/zh/trading/foreign/t86.html'
    }
)

stock_list = []

try:
    with urllib.request.urlopen(req) as response:
        raw_data = response.read().decode('utf-8')
        parsed = json.loads(raw_data)
        
        # 證交所 JSON 的資料通常放在 'data' 欄位中
        if 'data' in parsed and parsed['data']:
            print(f"成功從官方 JSON API 取得原始資料，共 {len(parsed['data'])} 筆")
            for row in parsed['data']:
                try:
                    # 證交所 T86 JSON 格式：
                    # row[0]: 證券代號, row[1]: 證券名稱
                    # row[4]: 外陸資買賣超股數
                    # row[10]: 投信買賣超股數
                    # row[15]: 自營商買賣超股數 (自行買賣) 或相對應欄位
                    code = str(row[0]).strip().replace('=', '').replace('"', '')
                    name = str(row[1]).strip().replace('"', '')
                    
                    # 確保是 4 位數股票代號
                    if code.isdigit() and len(code) == 4:
                        foreign = int(str(row[4]).replace(',', '').replace('+', '').strip())
                        trust = int(str(row[10]).replace(',', '').replace('+', '').strip())
                        
                        # 處理自營商（有些版本欄位在 15 或 18，取安全的整數轉換）
                        self_amt = 0
                        for idx in [15, 16, 17, 18]:
                            if len(row) > idx:
                                val_str = str(row[idx]).replace(',', '').replace('+', '').strip()
                                if val_str.lstrip('-').isdigit():
                                    self_amt += int(val_str)
                                    break
                        
                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                except Exception as row_e:
                    continue
        else:
            print("API 回傳的資料結構中沒有 'data' 欄位。")

except Exception as e:
    print(f"API 連線發生錯誤: {e}")

# 嚴格把關：如果抓不到任何資料絕對不輸出空內容
if len(stock_list) == 0:
    raise ValueError("錯誤：無法從證交所 JSON API 取得任何股票資料！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"成功更新！總計寫入 {len(stock_list)} 筆真實上市股票資料。")
