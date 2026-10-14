import json
import urllib.request
import datetime
import csv

today = datetime.date.today().strftime("%Y-%m-%d")

# 證交所三大法人買賣超日報 CSV 端點
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=csv"

req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
)

stock_list = []

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        raw_bytes = response.read()
        try:
            content = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_bytes.decode('big5', errors='ignore')
            
        lines = content.splitlines()
        csv_reader = csv.reader(lines)
        
        for row in csv_reader:
            # 確保該行有足夠的欄位（T86 通常超過 16 個欄位）
            if len(row) >= 16:
                # 清理代號與名稱
                code = row[0].strip().replace('=', '').replace('"', '').replace(' ', '')
                name = row[1].strip().replace('"', '')
                
                # 排除非股票的項目（例如產業分類標題、總計行等）
                # 真正的台股股票代號通常是 4 位數字，且不能包含「總計」、「合計」或中文字元
                if code.isdigit() and len(code) == 4:
                    try:
                        # 證交所 T86 標準欄位對應：
                        # [4] 外陸資買賣超張數(不含自營商)
                        # [10] 投信買賣超張數
                        # [15] 自營商買賣超張數
                        foreign = int(row[4].replace(',', '').replace('+', '').strip())
                        trust = int(row[10].replace(',', '').replace('+', '').strip())
                        self_amt = int(row[15].replace(',', '').replace('+', '').strip())
                        
                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                    except (ValueError, IndexError):
                        continue

    print(f"成功完整解析全市場真實股票，共 {len(stock_list)} 筆")

except Exception as e:
    print(f"解析發生錯誤: {e}")

# 如果真的抓不到資料，寫入空清單但保留日期
output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print("已成功更新完整的 stock_data.json！")
