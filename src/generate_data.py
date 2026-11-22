import csv, random, pathlib
random.seed(19); pathlib.Path("data").mkdir(exist_ok=True)
with open("data/sales.csv","w",newline="") as f:
    wr=csv.writer(f); wr.writerow(["dealer_id","quarter","units"])
    for d in range(1,31):
        for q in ["2024Q1","2024Q2","2024Q3","2024Q4","2025Q1","2025Q2","2025Q3","2025Q4"]:
            wr.writerow([f"D{d:02d}",q,random.randint(40,220)])
print("ok")
