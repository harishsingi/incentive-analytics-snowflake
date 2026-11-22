# Incentive Analytics with Snowflake

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

## Architecture — Before / After

Hover any component to see what it is and why it is needed.

![Before / After architecture](docs/before-after-elaborated.svg)
<details>
<summary><b>Transformation + tiering — click to expand the 4 steps</b></summary>

Collapsed, this is just: Dealer sales sources -> Snowflake staging -> Heavy transformations -> Historic trend flags

1. Dealer sales and bonus data is the source for every transformation.
2. Staging in Snowflake is built for large-volume transformations.
3. Heavy Snowflake SQL transformations clean and conform the data at scale.
4. Historic trend flags compare each quarter with the same quarter last year.

Tiering follows: bonus tiers are set from historic patterns and multiple parameters, and the variable payment estimate is ready per dealer per quarter.
</details>

### Earlier issues, risk, and impact after

| Aspect | Detail |
|---|---|
| Earlier issues | Dealer bonuses worked out in spreadsheets, slow and hard to audit; invoice, cost and dealer data scattered, so reporting needed manual joins; no historic comparison, so a bonus could not be judged against the same quarter last year; tiers worked out by hand; reports built by hand and delivered late; a bonus figure could not be traced back to its inputs. |
| Risk | Similar dealers could get different treatment with no record of why; a disputed bonus could not be resolved; decisions used stale numbers. |
| Impact after | Heavy Snowflake transformations on large-volume data power a dashboard-ready gold table, one row per dealer per quarter; tiers come from historic patterns and multiple parameters; trend flags show improving, flat or declining against the same quarter last year; the variable payment estimate is ready for review. |

