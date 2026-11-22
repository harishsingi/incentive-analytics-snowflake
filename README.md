# Dealer Bonus and Financial Reporting Analytics

Portfolio implementation based on production work experience. All data is synthetic, all code is original and clean-room, and no proprietary code, data, schema names, or internal system details from any employer are included.

**Original context:** Support for a financial services organisation: pipelines and automation for invoices, cost and dealer reporting, plus heavy Snowflake transformations on large volume data powering dealer bonus dashboards capturing historic patterns and multiple other parameters, and a migration supporting dealer and customer support including dealer bonus and variable payments data.

**This portfolio version:** Synthetic dealer sales and bonus data, Snowflake-style SQL transformations (also runnable logic in Python for local tests), and a dashboard-ready gold table. No real dealer, customer, payment or bonus figures are included.

## Run
```bash
python -m src.generate_data
python -m src.build_gold
python -m pytest tests/ -q
```
## Gold output
Per dealer, per quarter: units, bonus tier, variable payment estimate, historic trend flag (improving / flat / declining versus the same quarter last year).
