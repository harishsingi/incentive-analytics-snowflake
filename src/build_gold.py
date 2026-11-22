import csv, collections, pathlib
def tier(u): return "Platinum" if u>=500 else "Gold" if u>=250 else "Standard"
def main():
    rows=list(csv.DictReader(open("data/sales.csv")))
    agg=collections.defaultdict(int)
    for r in rows: agg[(r["dealer_id"],r["quarter"])]+=int(r["units"])
    pathlib.Path("data").mkdir(exist_ok=True)
    with open("data/gold.csv","w",newline="") as f:
        wr=csv.writer(f); wr.writerow(["dealer_id","quarter","units","bonus_tier"])
        for (d,q),u in sorted(agg.items()): wr.writerow([d,q,u,tier(u)])
    print(f"gold rows: {len(agg)}")
if __name__=="__main__": main()
