from src.build_gold import tier
def test_tiers(): assert tier(600)=="Platinum" and tier(300)=="Gold" and tier(10)=="Standard"
