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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
)

stock_list = []

try:
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('big5', errors='ignore')
        lines = content.splitlines()
        
        csv_reader = csv.reader(lines)
        for row in csv_reader:
            # 證交所 T86 真正的股票資料行：欄位數通常大於 16，且第一欄是 4 位數字的股票代號
            if len(row) >= 16:
                code = row[0].strip().replace('"', '').replace('=', '')
                name = row[1].strip().replace('"', '')
                
                # 嚴格過濾：必須是 4 位純數字的股票代號（排除中文標題行與市場總計行）
                if code.isdigit() and len(code) == 4:
                    try:
                        # 依照證交所官方 T86 CSV 實際欄位對應：
                        # [2] 證券名稱 (通常row[1]是代號或名稱，依實際結構調整)
                        # 我們直接抓取數值欄位：外資[4], 投信[10], 自營商(自行買賣+避險)合併計算或取[15]
                        # 為了保險，我們針對數值型欄位進行安全的整數轉換
                        
                        # 尋找含有數字的欄位進行解析
                        numeric_vals = []
                        for val in row[2:]:
                            clean_val = val.replace(',', '').replace('"', '').strip()
                            # 嘗試轉成整數
                            try:
                                numeric_vals.append(int(clean_val))
                            except ValueError:
                                continue
                        
                        # T86 標準格式中，外資、投信、自營商買賣超張數有固定相對位置
                        # 讓我們直接抓取確切欄位：
                        foreign = int(row[4].replace(',', '').strip())
                        trust = int(row[10].replace(',', '').strip())
                        
                        # 自營商通常分自行買賣與避險，我們將後面的數值加總或取主要欄位
                        self_1 = int(row[15].replace(',', '').strip()) if len(row) > 15 and row[15].replace(',', '').strip().lstrip('-').isdigit() else 0
                        self_2 = int(row[18].replace(',', '').strip()) if len(row) > 18 and row[18].replace(',', '').strip().lstrip('-').isdigit() else 0
                        self_amt = self_1 + self_2

                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                    except Exception as parse_e:
                        continue

    print(f"成功完整解析證交所真實上市股票，共 {len(stock_list)} 筆")

except Exception as e:
    print(f"抓取失敗: {e}")

if len(stock_list) == 0:
    raise ValueError("錯誤：未能取得任何證交所股票資料！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print("已成功將全面、完整的真實台股資料寫入 stock_data.json")
