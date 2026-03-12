#  BESS Development Risk Radar

**Tool to screen battery storage projects by development-side risk before revenue modelling — across NYISO and ERCOT.**

---

## The Problem

Revenue modelling for BESS is already a crowded, sophisticated space: tools like Modo’s benchmarks and forecasts cover dispatch, revenues, and scenarios in far more depth than I could replicate in a short take‑home. What feels systematically under‑served is development‑side risk — the reasons projects never reach COD in the first place (permits, queues, policy, load uncertainty), even when the revenue stack looks great on paper.

This tool asks:

“Given two identical 100 MW batteries in different regions, why is one much more likely to get built than the other — and how can we see that risk clearly before we start revenue modelling?”

By turning permitting, queue saturation, load growth, and policy churn into simple, comparable scores, I wanted to:
- Make those “invisible” risks visible in one place.
- Show how they differ across NYISO vs ERCOT and between regions inside each ISO.
- Give each stakeholder a way to interpret the same risk map through their own lens (developer, lender, trader, planner).

I treated this as a broad, shallow screening tool, not a deep, single‑market model and kept it simple on purpose
- Used 1–3 scores per dimension instead of complex, parameter‑heavy models.
- Guesstimated where data are coarse, but always anchored in named public sources.
- Treated price volatility (V) as an optional context layer rather than a full revenue model.

Covered what matters to all stakeholders
- Two relevant markets (NYISO, ERCOT).
- Four core dimensions (P/Q/L/S) that affect developers, asset owners, traders, and utilities.

What I chose not to build
- No dispatch, long‑term revenue, or DSCR model — trying to recreate Modo’s core engine in a few hours would be shallow and unconvincing.
Instead I spent time on: parsing and aggregating queues, mapping moratoria to zones, normalising load‑growth metrics, and building a UI where you can toggle and recombine dimensions quickly. The result is a screening tool that can reasonably be built, understood, and critiqued in the given time period.

To keep scores defensible:
- I start from public, named data for each dimension (EticaAG for P; NYISO queue and ERCOT GIS for Q; Power Trends/LTLF/MORA + “energy‑intensive projects” for L; Order 2023 + RTC+B documentation and Modo articles for S).
- I reduce to simple metrics:
    - P = number and type of restrictions.
    - Q = (queued + installed BESS MW) / peak load.
    - L = load‑growth band + data‑center presence.
    - S = count and materiality of active reforms.
- I bucket into 1–3 scores with explicit rules, and I show the underlying numbers (queued MW, ratios, growth %, restriction counts, policy flags) so someone else can disagree with my thresholds and rescore.
- I call out limitations (judgement in P/S, snapshot nature of Q/L) so it’s clear where subjectivity enters.
That makes the tool auditable: every high score can be traced back to specific data and thresholds, not just “the model says so.”

The dimensions deliberately mirror themes in current NYISO/ERCOT storage work:
- Queue saturation & attrition – NYISO’s oversubscribed storage queue and cluster‑study reform, and ERCOT’s very high queue/peak ratios, are embedded in Q and S.
- Permitting & social risk – P reflects the wave of BESS moratoria/bans in New York (and some in Texas), capturing that projects can die from local opposition regardless of prices.
- Load growth & data centers – L uses Power Trends, LTLF, MORA, and “energy‑intensive projects” to reflect data‑center and electrification‑driven demand growth.
- Policy‑shaped business cases – S combines process risk (Order 2023, cluster deposits, infeasibility screens) and market‑design risk (ISC, RTC+B, AS redesign), matching how real BESS projects are underwritten.

Throughout the development process, I used Claude as an AI assistant for initial ideation, cross-referencing Modo's public research themes, and surfacing relevant market data sources. I then transitioned to Claude Code for implementation, following a test-driven development workflow where I validated outputs and manually reviewed all coding logic before accepting generated code. At each stage I maintained clear guardrails by verifying data sources independently, and ensuring the methodology was transparent and reproducible rather than treating AI output as ground truth ~

Lastly, thank you for the opportunity to scope and build this tool, and for considering me for a further position with Modo Energy. I’ve included my CV in this repository so you can see more detail on my background and experience!

---
This tool provides a transparent and interactive **development risk radar** for BESS developers, investors, and analysts. It counter-weights pure revenue optimism with a structured view of the obstacles between "project proposed" and "project operational."

---

## The 5 Risk Dimensions

| Code | Dimension | What it captures | Data Source |
|------|-----------|-----------------|-------------|
| **P** | Permitting / Social Risk | Density of moratoria, bans, and local opposition by zone | EticaAG BESS Restrictions Database; Example NY ordinance |
| **Q** | Queue Stress | Queued BESS MW relative to zone peak load; attrition probability | ERCOT GIS Report Feb 2026 (parsed); NYISO Queue Apr 2023 |
| **L** | Load Growth | Forecast demand growth + data center cluster presence | ERCOT LTLF 2025; NYISO Power Trends 2025; NYISO energy-intensive projects note |
| **S** | Policy Uncertainty | Cluster study reform (NYISO Order 2023), RTC+B + ASDC/ORDC redesign (ERCOT) | NYISO Order 2023 compliance filing; ERCOT RTC+B valuation analysis; Modo Energy Q3 2025 |
| **V** | Price Volatility *(optional)* | DAM/RT price std dev + scarcity frequency — revenue signal, not pure dev risk | Live via `gridstatus` (NYISO LBMP + ERCOT SPP, 90-day lookback) |

### Scoring Rules

**P — Permitting Risk**
- Score 3: 8+ active restrictions OR multiple bans 
- Score 2: 4–7 restrictions OR 1 active ban 
- Score 1: Fewer than 3 restrictions, no active ban 

(Underlying data: [S1][S2][S3][S22])

**Q — Queue Stress** (computed from real XLSX data)
- Score 3: queued_BESS_MW / peak_load_MW > 0.30
- Score 2: ratio 0.15–0.30
- Score 1: ratio < 0.15

> **Key finding**: Queue saturation is structural across all regions, but ISO-specific thresholds reveal real differentiation. NYISO ratios range 0.21–0.38x peak load; ERCOT ratios 1.08–5.90x — a 28x spread that a single global threshold collapses to Q=3 for everyone. Using ISO-aware cutoffs (NYISO >0.35x = Q=3; ERCOT >3.0x = Q=3), four regions score Q=2: NYISO_J (0.21x), NYISO_K (0.31x), ERCOT_HOU (1.08x), ERCOT_NORTH (2.32x). Differentiation within Q, and overall, still comes primarily from P, L, and S. [S4][S5][S6][S9][S11][S12][S13][S16][S19][S20]

**L — Load Growth**
- Score 3: >25% forecast demand growth AND data center cluster present
- Score 2: 15–25% growth OR partial cluster
- Score 1: <15% growth, no cluster

*Note: Load-growth projections are inherently subjective; here they are based on NYISO Power Trends 2025 and ERCOT LTDF / planning reports, interpreted using Modo Energy’s NYISO 2050 and ERCOT outlook research.* [S7][S8][S9][S10][S14][S19][S20][S21]

**S — Policy Uncertainty**
- Score 3: Multiple major reforms in progress (NYISO: ISC redesign + Order 2023 cluster study reform; ERCOT HOU/NORTH: RTC+B + AS market redesign)
- Score 2: One active reform (ERCOT WEST/SOUTH: RTC+B only)
- Score 1: Stable framework

### NYISO Policy Reforms

**ISC — Index Storage Credit** *(revenue context, not an S driver)*
NYSERDA 15-year contracts (from July 2025) providing a monthly revenue floor: NYSERDA covers the shortfall between a developer's bid Strike Price and a Reference Price based on zonal day-ahead transmission basis spreads. Reduces revenue risk for projects that successfully clear the queue and build — but does not ease the interconnection or permitting obstacles captured in P/Q/S. Zone K (Long Island) and eastern nodes offer the largest spread premiums above the Reference Price. [S15][S16]

**Order 2023 / Cluster Study Reform** *(S driver — all NYISO zones score S=3)*
FERC Order 2023 (July 2023) requires NYISO to replace serial interconnection studies with a First-Ready, First-Served Cluster Study Process. Total study timeline: 569 days (Transitional Cluster). Financial commitments: $10,000 application fee; $100K–$250K study deposits (size-tiered); Phase 1 deposit at $4,000/MW; Phase 2 deposit at the greater of Phase 1 or 20% of Phase 1 cost estimate. Withdrawal penalties escalate from 25% of study deposit (pre-Phase 1) to 100% + 20% of Phase 2 deposit (post-Phase 2 acceptance). Physical infeasibility screens added at the Customer Engagement Window stage. [S11][S12][S13]

**Storage-as-Transmission Framework** *(revenue context, not an S driver)*
NYISO tariff discussions allow transmission owners to procure storage as a transmission asset — deferring or replacing conventional wire upgrades. Projects winning transmission contracts gain a revenue stream independent of energy/AS markets, but the framework's tariff design and cost allocation rules remain under active FERC/NYISO proceedings. Adds revenue optionality for strategically sited projects; does not reduce interconnection uncertainty. [S9][S14]

### ERCOT Policy Reforms

**RTC+B — Real-Time Co-Optimization + Batteries** *(S driver — all ERCOT zones)*
ERCOT market redesign replacing the Operating Reserve Demand Curve (ORDC) with Ancillary Service Demand Curves (ASDCs). Under the ORDC, scarcity rents were added as a blunt premium to energy prices when operating reserves fell below a threshold. Under ASDCs, each ancillary service product (Regulation Up/Down, Responsive Reserve, Non-Spinning Reserve) is priced separately in real time based on actual availability — batteries bid energy and ancillary services simultaneously as unified assets with state-of-charge constraints modelled explicitly. [S17][S18][S19][S20]

**ASDCs Replacing ORDCs — Scarcity Rent Mechanism Shift**
Scarcity rents that formerly flowed through energy prices (ORDC adder) now flow through specific AS product prices. For BESS operators, this shifts the revenue stack: energy arbitrage revenue fell ~14% as average ERCOT RT prices declined; ancillary service revenue grew from ~15% of BESS income (2023) to ~26% (2024). Operators who can actively stack AS products (ECRS, REGUP, REGDN) in real time benefit; operators relying on passive energy spread lose share. Projected system cost reduction from RTC+B: $2.5–$6.4 billion annually. [S19][S20][S21]

**ECRS Duration Shift** *(AS redesign — affects eligibility)*
ERCOT Contingency Reserve Service (ECRS) duration requirement reduced from 2 hours to 1 hour. This expands the pool of battery assets eligible to provide ECRS — previously only 2-hour+ units qualified. Lowers the capital cost threshold for ECRS participation, increasing competition for the product but widening revenue access for shorter-duration BESS.

**AS Redesign Scope** *(S driver — HOU and NORTH score S=3)*
Houston and North (DFW) carry the `AS_redesign` flag because these two zones have the highest existing BESS penetration and AS market participation in ERCOT — the redesign directly reprices their primary revenue streams. West and South are less exposed to AS redesign uncertainty (RTC+B only) and score S=2.

**V — Price Volatility** *(continuous, normalised to 1–3 for display)*
> V is kept separate from P/Q/L/S because high price volatility signals both **revenue opportunity** and **revenue uncertainty** — it's a market context signal, not a pure development risk. Opt in to fetch live data. [S23][S24][S25]

### Composite Score
```
RiskScore = Σ (toggle_i × weight_i × score_i)
```

With all four core dimensions on and equal weights, maximum score = 12.

### Final Scores (all dimensions on, equal weights)

| Region | P | Q | L | S | **Score** |
|--------|---|---|---|---|-----------|
| NYISO G/H/I — Lower Hudson Valley | 3 | 3 | 3 | 3 | **12** |
| NYISO J — New York City | 2 | 2 | 3 | 3 | **10** |
| NYISO K — Long Island | 3 | 2 | 2 | 3 | **10** |
| NYISO A–F — Rest of State | 2 | 3 | 1 | 3 | **9** |
| ERCOT Houston | 1 | 2 | 3 | 3 | **9** |
| ERCOT North (DFW) | 1 | 2 | 3 | 3 | **9** |
| ERCOT West (Permian) | 1 | 3 | 2 | 2 | **8** |
| ERCOT South (San Antonio) | 1 | 3 | 2 | 2 | **8** |

---

## Region Coverage

### NYISO (4 regions)
| region_id | Name | Counties |
|-----------|------|---------|
| NYISO_K | Zone K — Long Island | Nassau, Suffolk |
| NYISO_GHI | Zones G/H/I — Lower Hudson Valley | Westchester, Orange, Rockland, Dutchess |
| NYISO_J | Zone J — New York City | 5 boroughs |
| NYISO_ABCDEF | Zones A–F — Rest of State | Upstate NY, Capital District |

### ERCOT (4 regions)
| region_id | Name | Notes |
|-----------|------|-------|
| ERCOT_HOU | Houston | Brazoria Co. cluster, coastal; 16% of ERCOT BESS |
| ERCOT_NORTH | North (DFW Corridor) | Largest data center growth in ERCOT |
| ERCOT_WEST | West (Permian Basin) | Wind + solar country; highest Q ratio (5.9x) |
| ERCOT_SOUTH | South (San Antonio / Corpus) | Lightest restriction profile |

---

## Usage

### Installation
```bash
git clone https://github.com/<your-username>/bess-dev-risk-radar.git
cd bess-dev-risk-radar
pip install -r requirements.txt
```

To enable the V (Price Volatility) dimension, also install:
```bash
pip install gridstatus>=0.25
```

### Run the app
```bash
streamlit run src/app.py
```

### Run unit tests
```bash
python -m pytest tests/test_scoring.py -v
```

---

## How to Read This Tool

### As a Developer — where to originate
Enable P only. Regions scoring P=3 have active bans or dense moratoria — siting requires rezoning or variance before permitting can begin. NYISO downstate zones (G/H/I, J, K) have the most restrictive profiles. ERCOT South (P=1) is the cleanest origination path today.

Weight P=2× if permitting is your binding constraint. Add Q to filter out zones where queue attrition risk is so high that even a permitted project may wait 3–5 years for an interconnection position.

### As an Asset Owner — where to discount pipeline MW
Enable all four core dimensions (P/Q/L/S). Pipeline MW in high-scoring regions should be discounted for probability of completion: historical NYISO queue attrition exceeds 90%; ERCOT applications dropped 50% in H2 2025 — a saturation signal. A 100 MW project in NYISO_GHI (score 12) is a fundamentally different risk position than the same project in ERCOT_SOUTH (score 8).

Weight Q=2× to reflect interconnection risk as a primary valuation input. Every point of Q score represents a structural barrier between financial close and commercial operation date.

### As a Trader / Optimizer — where queue risk keeps spreads fatter or thinner
Enable V (Price Volatility) alongside the core dimensions. The **Risk vs. Revenue** quadrant shows where high development risk has suppressed new build enough to keep price volatility elevated — and where heavy build may compress future spread. X uses P/Q/L/S from permitting, queue, load-growth, and policy data (EticaAG, NYISO queue, Power Trends, ERCOT GIS, Modo research); Y uses a 1–3 volatility band from recent NYISO LBMP / ERCOT SPP data.

Regions with Q=3 but low installed base still have high arbitrage headroom. Regions where queue ratios exceed 1×–2× peak load face structural oversupply risk once projects clear — watch ERCOT West (5.9× ratio) and NYISO downstate for basis compression as the queue clears.

### As a Utility / ISO Planner — where build fails to keep up with load growth
Enable Q and L only (disable P and S). Regions scoring L=3 + Q=3 face simultaneous demand surge and queue saturation — the grid is being asked to do more with a highly contested interconnection pipeline. ERCOT North (DFW data center corridor) and ERCOT Houston (industrial electrification + Brazoria cluster) are the highest-stress zones for adequacy planning.

ERCOT LTLF 2025 projects peak load growing from 109 GW to 139–218 GW by 2030. If queue attrition holds at historical rates, a meaningful fraction of queued BESS MW will not reach commercial operation on the timelines assumed in adequacy studies.


---

## Example Use Cases

**Developer permitting screen**
Enable P only, disable Q/L/S/V. Immediately see which regions have the most active moratoria and bans. NYISO downstate zones and Long Island rank highest — weight P=2× if permitting is your binding constraint.

**Lender / project finance due diligence**
Enable all four core dimensions. Increase Q and P weights (queue attrition + permitting risk are lender priorities); reduce L and S slightly. NYISO_GHI and NYISO_J remain highest risk; ERCOT_SOUTH offers the cleanest development path.

**Market analyst — revenue vs. risk overlay**
Enable V to fetch live price volatility. Compare risk score vs. V_volatility to identify regions with attractive revenue profiles despite development headwinds (e.g., ERCOT_WEST: high revenue volatility, moderate development risk).

**ISO comparison**
Filter to NYISO only to compare zones within New York; filter to ERCOT only to compare Texas regions. All-NYISO view highlights the downstate-vs-upstate permitting divide.

---

## Limitations

- **Directional screening tool**, not a bankable model. Scores are researcher-assigned within P/L/S dimensions using the sources above.
- **NYISO Q** uses the January 2026 queue snapshot (Interconnection Queue + Cluster Projects sheets combined). 583 projects totalling ~82 GW have been withdrawn since the queue opened; the 83 remaining active ES projects total ~11 GW. NYISO_J (NYC) scores Q=2 due to its larger peak load absorbing the queue; all other NYISO zones score Q=3.
- **ERCOT Q** uses the February 2026 GIS Report, which includes all active GIM study-phase projects. Does not filter by study phase or probability of completion.
- **Q scores**: ISO-specific thresholds applied (NYISO >0.35x = Q=3; ERCOT >3.0x = Q=3). Four regions score Q=2: NYISO_J (0.21x), NYISO_K (0.31x), ERCOT_HOU (1.08x), ERCOT_NORTH (2.32x). ERCOT_WEST (5.90x) and ERCOT_SOUTH (3.32x) score Q=3.
- **V dimension** requires internet access and `gridstatus` installation. Degrades gracefully to exclusion if unavailable.
- P and S scores are manually encoded from document review; reasonable analysts could score ±1 on individual regions.

---

## Repository Structure

```
bess-dev-risk-radar/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/
│   │   ├── NYISO-Interconnection-Queue-4-30-2023.xlsx
│   │   ├── GIS_Report_February2026.xlsx
│   │   └── Co-located_Battery_Report_February2026.xlsx
│   ├── region_risk.csv          # 8-region master table
│   ├── ny_permitting.csv        # 34 NY permitting entries (EticaAG)
│   └── tx_permitting.csv        # 5 TX permitting entries (EticaAG)
├── src/
│   ├── app.py                   # Streamlit app
│   ├── data_loader.py           # XLSX parsing + CSV loaders
│   └── scoring.py               # compute_risk_score(), fetch_price_volatility()
└── tests/
    └── test_scoring.py          # 16 unit tests (pytest)
```

---

## Data Sources & References

**Permitting & social risk**

[S1] EticaAG – BESS Restrictions Database (moratoria, bans, ordinances for NY & TX)  
https://eticaag.com/bess-moratorium-database/

[S2] Town of Salem, NY – Temporary Moratorium on the Approval of Commercial Battery Energy Storage Systems (Oct 2025)  
<direct PDF URL>

[S3] EticaAG – Troy, NY Approves Six‑Month BESS Moratorium  
https://eticaag.com/troy-ny-approves-six-month-bess-moratorium/

**Interconnection & queue stress**

[S4] NYISO – Interconnection Queue (Jan 2026 snapshot, “ES” fuel type = energy storage; Interconnection Queue + Cluster Projects sheets)  
https://www.nyiso.com/interconnections

[S5] ERCOT – Generator Interconnection Status (GIS) Report (Feb 2026)  
https://www.ercot.com/mp/data-products/data-product-details?id=pg7-200-er

[S6] ERCOT – Co‑Located Battery Identification Report (Feb 2026)  
<ERCOT data‑product URL>

**Load growth & grid stress**

[S7] ERCOT – Long‑Term Load Forecast (LTLF) 2025 (peak load 109 GW → 139–218 GW by 2030)  
<ERCOT LTLF PDF/XLS URL>

[S8] ERCOT – Monthly Outlook for Resource Adequacy (MORA), May 2026  
<ERCOT MORA URL>

[S9] NYISO – Power Trends 2025 (regional load forecasts)  
https://www.nyiso.com/documents/20142/2223020/2025-Power-Trends.pdf

[S10] NYISO – Energy‑Intensive Projects in NYISO’s Interconnection Queue (29 projects, 6,055 MW as of July 2025)  
https://www.nyiso.com/-/energy-intensive-projects-in-nyiso-s-interconnection-queue

**Policy & market design**

[S11] NYISO – Order No. 2023 Compliance / Cluster Study Reform (First‑Ready, First‑Served, 569‑day timeline, deposit schedule, physical infeasibility criteria)  
https://www.nyiso.com/documents/20142/55778551/Order%20No.%202023%20Compliance%20Plan.pdf

[S12] NYISO – Stakeholder Summary on Order 2023 Implementation  
https://www.nyiso.com/documents/20142/1408883/Stakeholder_Summary.pdf

[S13] Modo Energy – What NYISO’s Interconnection Queue Reform Means for BESS  
https://modoenergy.com/research/en/nyiso-interconnection-queue-reform-cluster-study-battery-storage

[S14] Modo Energy – NYISO 2050 Electricity Demand Forecast & BESS Outlook  
https://modoenergy.com/research/en/nyiso-2050-demand-forecast-bess

[S15] Modo Energy – NYISO: A Complete Guide to BESS Industry Growth and Revenue (ISC, ancillary services, siting)  
https://modoenergy.com/research/en/nyiso-battery-business-case-grid-scale-storage-buildout-energy-arbitrage-ancillary-services

[S16] Modo Energy – NYISO: Where to Build a Battery to Leverage the Index Storage Credit (ISC Reference Price, zonal basis spreads)  
https://modoenergy.com/research/en/nyiso-where-to-build-index-storage-credit-nyserda-zonal-reference-price-arbitrage

[S17] ERCOT – Real‑Time Co‑Optimization + Batteries (RTC+B) Overview  
https://www.ercot.com/files/docs/2025/07/09/Real-Time-Co-Optimization-Overview.pdf

[S18] AInvest – ERCOT’s RTC+B and the Reshaping of Energy Storage Valuation (ORDC → ASDC transition, ECRS duration shift)  
<article URL>

[S19] Modo Energy – ERCOT: BESS Revenues Are Down, But What Could Restore Them?  
https://modoenergy.com/research/en/ercot-bess-revenues-outlook-load-growth-thermal-retirements-bridging-solutions

[S20] Modo Energy – ERCOT Annual Buildout Report (battery capacity ~14 GW by 2026)  
https://modoenergy.com/research/en/ercot-battery-buildout-2025-annual-report

[S21] Modo Energy – BESS Insights and What You Need to Know from Q3 2025 (multi‑ISO roundup)  
https://modoenergy.com/research/en/ercot-pjm-caiso-nyiso-us-bess-research-roundup-q3-2025

**Modo Energy permitting & development**

[S22] Modo Energy – NYISO: The Current Landscape of BESS Permitting  
https://modoenergy.com/research/en/nyiso-new-york-battery-permitting-landscape-moratoria-ban-risk

**Price‑volatility (optional V dimension)**

[S23] NYISO – Energy Market & Operational Data (DAM/RTM LBMP)  
https://www.nyiso.com/energy-market-operational-data

[S24] ERCOT – Market Information (DAM Settlement Point Prices)  
https://www.ercot.com/mktinfo

[S25] gridstatus – Python library (NYISO DAM LBMP + ERCOT DAM SPP; 14‑day lookback used for V)  
https://opensource.gridstatus.io/

