# Decision Knowledge Package (DKP)
## Francis E. Walter Dam and Reservoir — Lehigh River, Lehigh River Basin, PA

> **DKP definition.** A Decision Knowledge Package is the discrete representational unit produced for a single decision-maker, encoding either deterministic-control logic (rules with variables) or distributional-behavioral patterns, together with a fallback policy for conditions its source material does not cover.

> **Revision note (2026-10-07) - reservoir-only model.** In `R-PLAN` only, the downstream control-gage thresholds, the gage-triggered Plan C and the sentence on downstream stage trends were removed, because the simulation supplies no downstream gage data; a pool between the seasonal target and 1450.0 ft is Plan B. Nothing else in this file is changed. The unedited file is kept as `DKP_FEWalter_Dam_v1.2_original.md`.

> **Version notice.** `DKP-FEWALTER-v1.2`. **Prescriptive source replaced.** Layer 2 is rebuilt from scratch against the governing *Water Control Manual (Revised), Francis E. Walter Dam and Reservoir* — USACE Philadelphia District, October 1961, revised October 1994, **revised September 2014** (redacted public edition, Chapters 1–9 + Pertinent Data). HEC PR-73 is **demoted from prescriptive to evidentiary**; no Layer 2 rule in this version cites PR-73. Walter now joins Prompton and Beltzville as a **single-prescriptive-source gold-standard DKP**.
>
> **Three substantive corrections to v1.0.** (1) v1.0's central characterization — a discretionary, case-by-case "deviation regime" (`FC_Ops_Dev`) for summer recreation pool — is **obsolete**. The 2014 WCM institutionalizes the seasonal raise to elevation 1370 as the *normal operational rule curve* (§7-01), not a deviation. (2) v1.0's downstream control stages (Lehighton 9.7 / Walnutport 6.3 / Bethlehem 9.9 ft) **do not exist in the WCM**; Table 7-2 prescribes a two-tier flood-stage / action-stage structure at five stations. The value 6.3 ft appears in the WCM only as an event-specific figure inside the August 1955 *routing narrative* (§8-02,d,2) — an evidentiary number promoted to a standing rule. (3) v1.0's rate-of-change rule was stated in the **wrong physical domain**: the WCM prescribes gate-position criteria (feet per 10 minutes), not a 500 cfs/hr discharge constraint. This is the **second independent instance** of the same domain-translation defect already logged at Beltzville, which makes it a systematic RT1 finding rather than a one-off.
>
> **v1.2 (2026-08-07) — TAB-A partially supplied; the DKP is now executable.** Table 7-1 Parts A and B, Table 7-3, Table 8-1 and Table 8-2 were added. The Maximum, Minimum and Water Quality Release Schedules close the v1.1 blocking gap: **release magnitude under every Schedule Plan is now computable.** Table 7-3 at 1-ft resolution with a day-second-feet column makes storage accounting and `R-INFLOW` executable. Table 8-1 adds a **53-year annual maximum series (WY1961–2013)** and Table 8-2 a five-event natural-vs-regulated record. Two new prescriptive rules appear (`R-TEMP`, `R-FILLING`) and eight new source defects are logged, including a precisely diagnosable off-by-one-foot error in Table 8-1's flood-storage denominator (Provenance 3(t)). Still absent: Tables 8-3 to 8-11 (station ratings), all Plates, Exhibits A–D.

---

## Layer 1 — Identity and System Metadata

| # | Field | Value |
|---|---|---|
| 1.1 | **DKP ID** | `DKP-FEWALTER-v1.2` (full tier) |
| 1.2 | **Decision type** | `deterministic-control` — plan-selecting (Schedule Plans A–D) with a seasonal rule curve; **jointly constrained** with Beltzville Lake |
| 1.3 | **Decision-maker represented** | Water Control Personnel, Northern Area Office, Operations Division, USACE Philadelphia District (CENAP); dam operators execute and assume regulation authority on loss of communications (WCM §5-08a, §7-04, §9-01,a,5) |
| 1.4 | **Decision output** | Gate setting on three flood-control service gates and two 24-in bypass butterfly valves → release (cfs), subject to zone/plan logic, five downstream stage constraints, a combined-release ceiling shared with Beltzville, and gate-position rate limits |
| 1.5 | **Sources** | (1) **Prescriptive:** F.E. Walter Water Control Manual, rev. September 2014 — Pertinent Data; §§2-03, 3-05, 4-01, 4-09, 5-01, 5-08 to 5-13, 6-02, 7-01 to 7-16, 8-02 to 8-10, 9-01 to 9-06; Tables 4-7, 4-8, 5-1, 7-2, 8-12, 8-13; **TAB-A Tables 7-1 Parts A and B, 7-3, 8-1, 8-2**. (2) **Evidentiary:** HEC PR-73 (Feb 2010, rev. May 2011) §4.3.4.1, Table 4.23, App. B — retained only in §2.5 and P5 as a labeled expert-extraction comparator. (3) **Referenced, not obtained:** WCM TAB-A Tables 8-3 to 8-11 (station ratings), Plates 7-1a/7-1b/7-2/7-3/7-4/7-5/7-6/7-7, Exhibits A–D, F.E. Walter Emergency Action Plan, DRBC Water Code |
| 1.6 | **Epistemic ground** | Document-driven (WCM, single prescriptive source) |
| 1.7 | **Basin / stream / location** | Lehigh River Basin (Delaware River Basin); Lehigh River at the Bear Creek confluence, RM 77 above the Delaware at Glendon/Easton, PA; ~5 mi upstream of White Haven, PA |
| 1.8 | **Drainage area** | **288 sq mi** above the dam (Pertinent Data; §4-01) = 21% of the 1,368 sq mi Lehigh Basin. Gaged inflow: Stoddartsville 91.7 + Blakeslee 118.0 = 209.7 sq mi; Bear Creek ungaged. Outflow gage below dam (White Haven) = 290.0 sq mi. *(v1.0 coverage gap closed; see Provenance 3(e)–(f) for two arithmetic/transposition defects in the source.)* |
| 1.9 | **Dam / spillway / outlet** | Earthfill embankment, 3,000 ft long × 234 ft high, top width 30 ft at El. 1474.0. **Uncontrolled** concrete ogee spillway, crest El. 1450.0, width 450 ft, in the right abutment — no regulating appurtenances. Outlet works: 16-ft concrete conduit (1,040 ft, 1.10% slope, invert 1250.0 → 1238.1) fed by three service + three emergency vertical slide gates, each 5'8" × 10'0"; plus two 24-in butterfly bypass valves off inlet weirs at El. 1297.0 |
| 1.10 | **Companion project(s)** | **Beltzville Lake** (Pohopoco Creek) → `DKP-BELTZVILLE-v1.2`. Regulated **as a system**: Table 7-1 Part B prescribes a *combined* maximum release across both projects — a single cfs value read against the most restrictive of three shared Lehigh gages — with allocation between them governed by balancing percent flood-control storage utilized (WCM Table 7-1 Parts A and B; §7-03; §7-05,a,2). Beltzville's own parameters are given in Table 7-1: normal pool 628.0, spillway crest 651.0, minimum releases 35/35/15 cfs, Parryville action stage 5.30 ft (1,500 cfs). Walter and Beltzville are the only two flood-control reservoirs in the Lehigh Basin |
| 1.11 | **Authorized purposes** | **Flood control** (primary; Flood Control Act of 1946, PL 526). **Recreation incl. whitewater** (PL 100-676 §6, 17 Nov 1988). *Not* project purposes: hydropower, navigation, water supply, fish and wildlife (the last receives equal consideration under PL 85-624 but has no storage allocation) |
| 1.12 | **Institutional partners** | North Atlantic Division (deviation approval); DRBC (drought declarations; expired temporary-storage MOA); NWS Mt. Holly/Philadelphia (forecasts); USGS (gaging; Delaware River Master); PA Fish & Boat Commission (50 cfs minimum, whitewater/fisheries plan); PA DCNR (Hickory Run State Park notification); Carbon and Luzerne County EMAs (>2,000 cfs notification) |
| 1.13 | **Observed-behavior benchmark** | Pool-elevation gage at the project (DA 288.0, datum 1265.00, installed Feb 1961); **Lehigh River below F.E. Walter near White Haven** (DA 290.0, datum 1212.95, Oct 1957). Control-point gages: Lehighton (591.0 / 444.26), Walnutport (889.0 / 350.27), Bethlehem (1279.0 / 210.94), Glendon (1359.0 / 164.30). Inflow gages: Stoddartsville (91.7 / 1463.81), Tobyhanna Ck. at Blakeslee (118.0 / 1511.23). Beltzville coupling gages: Kresgeville (49.9 / 659.72), Pohopoco below Beltzville near Parryville (96.4 / 492.05) |
| 1.14 | **Vertical datum** | **NGVD29** throughout. Conversion: NAVD88 = NGVD29 − 0.62 ft (Pertinent Data) |

---

## Layer 2 — Machine-Readable Rules and Data

*Every rule below cites the September 2014 WCM. No PR-73 content appears in Layer 2.*

### §2.1 Operating Zones and Key Elevations

| Zone / feature | Elev. (ft NGVD29) | Area (ac) | Storage (ac-ft) | Source |
|---|---|---|---|---|
| `EL_TOP_OF_DAM` | 1,474.0 | 2,460.3 | 159,814 | Pertinent Data (rev. 2014) |
| `EL_MAX_SDF` — max spillway design pool | 1,470.9 | 2,307.9 | 152,464 | Pertinent Data; §2-03a; §8-02b |
| `EL_SPILLWAY` — top of flood control pool = ogee crest | 1,450.0 | 1,811.7 | 109,878 | Pertinent Data; §2-03b |
| `EL_DROUGHT_MAX` — top of expired DRBC temporary storage (summer) | 1,392.0 | — | — | §3-05a; §7-12; §9-03 — **contract expired, not renewed** |
| `EL_REC_SUMMER` — top of temporary recreation pool (= expired drought winter cap) | 1,370.0 | 519.7 | 20,696 | Pertinent Data; §7-01; §7-06 |
| `EL_ACCESS_ROAD` — legacy upstream-embankment road; historic whitewater storage cap | 1,309.0 | — | — | §3-05,b,1; §7-06 — **superseded 2004** by the road across the dam crest |
| `EL_BOAT_LIMIT` — in-lake boating/launching impeded above | 1,306.0 | — | — | §3-05,b,1; §7-06 |
| `EL_CONSERVATION` — top of conservation pool = winter normal pool | 1,300.0 | 100.5 | 1,993 | Pertinent Data; §7-01 |
| `EL_BYPASS_INVERT` — bypass inlet weir crest (selective-withdrawal floor) | 1,297.0 | — | — | Pertinent Data; §2-03,c,2; §4-08 |
| `EL_INACTIVE` — outlet intake invert / approach channel | 1,250.0 | — | — | Pertinent Data; §2-03,c,1 |
| `EL_STREAMBED` | 1,245.0 | 0 | 0 | Pertinent Data |

Flow and rate constants:

| Constant | Value | Source |
|---|---|---|
| `Q_MIN_NORMAL` — conservation / water-quality minimum release | **50 cfs** | §7-01; §7-07; §8-04 (established by PA Fish & Boat Commission) |
| `Q_MIN_DROUGHT` — minimum during a basin-wide DRBC drought declaration | **43 cfs** | §8-04 |
| `Q_MIN_FC` — minimum while impounding during a flood emergency | **100 cfs** | §7-05,c,3 |
| `Q_CHANNEL_CAP` — limiting non-damaging channel capacity below the dam | **10,000 cfs** (= stage 8.40 ft at the outflow gage) | §3-05,b,2(c); §4-09; §7-02a; §7-05,c,1 |
| `Q_OUTLET_MAX_AT_CREST` — outlet works capacity at `EL_SPILLWAY` | **≈17,000 cfs** | §7-02a; §7-05,c,4 |
| `Q_NOTIFY` — release triggering Carbon/Luzerne County EMA notification | **2,000 cfs** | §5-08b; §5-13; §7-02a |
| `Q_WW_EVENT` — scheduled whitewater release band | **500–750 cfs** | §3-05,b,2(a); §7-06 |
| `Q_WW_STORAGE` — release held during legacy pre-event storage period | **144 cfs** (cut back to inflow if inflow < 144) | §7-06 |
| `ROC_GATE_LOW` — gate travel limit, openings 0–6 ft (raise **and** lower) | **≤ 1.0 ft per 10 min** | §7-05,c,6 |
| `ROC_GATE_HIGH` — gate travel limit, openings > 6 ft (raise **and** lower) | **≤ 1.5 ft per 10 min** | §7-05,c,6 |
| `GATE_TRAVEL_MECH` — mechanical hoist rate (capability, *not* the regulatory limit) | 0.8 ft/min; ~12.5 min for a full 10-ft transit | §2-03,c,2 |
| `STORAGE_FC` — flood control storage allocation | **107,886 ac-ft** (recomputes to 107,885.66 from Table 7-3) | §7-05; §7-05,c,2; Table 7-3 |
| `STORAGE_FC_T81` — denominator used in Table 8-1's % column | 106,084 ac-ft — **erroneous**, see Provenance 3(t) | Table 8-1 footer |
| `T_TARGET_MAX` — downstream release temperature target | **60–65 °F**, met by blending surface (1300.0–1297.0) and bottom water | Table 7-1 Part B, Water Quality Release Schedule |
| `EL_BLEND_TOP` / `EL_BLEND_BOT` — bypass withdrawal band | 1,300.0 / 1,297.0 ft NGVD | Table 7-1 Part B |
| `STORAGE_FC_BELTZVILLE` — companion allocation (for balancing) | 27,664 ac-ft | §7-05 — *cross-check against `DKP-BELTZVILLE-v1.2`* |
| `EL_NORMAL_BELTZVILLE` / `EL_SPILLWAY_BELTZVILLE` | 628.0 / 651.0 ft NGVD | Table 7-1 Part A |
| `STAGE_PARRYVILLE_ACTION` — Beltzville's own control limit | **5.30 ft = 1,500 cfs** (Table 7-1 note 4) — *Table 7-2 gives 5.5 ft; see Provenance 3(p)* | Table 7-1 Part B |
| `DRAWDOWN_TIME` — 1450.0 → 1300.0 at ≤10,000 cfs, three gates, inflow 300 cfs | ≈ 5.6 days | §7-05,c(item mis-numbered "3") |
| `POOL_FLUX_SPAWN` — max pool fluctuation, May–June spawning window | **5 ft** | §7-08 |

Downstream control stages (WCM **Table 7-2**, with Table 4-7 datum conversions). *Table 7-1 Part A uses these same action stages as the Plan-B/Plan-C boundary except at Lehighton, where it gives 9.0 ft — see Provenance 3(o).*

| Station | NWS flood stage (ft) | Action stage (ft) | Gage datum (ft NGVD) | Regulated by |
|---|---|---|---|---|
| Lehigh R. at **White Haven**, PA *(immediately below dam)* | **8.0** | — | 1212.95 | Walter |
| Lehigh R. at **Lehighton**, PA | **10.0** | **9.5** | 444.26 | Walter only |
| Pohopoco Ck. below **Beltzville** nr. Parryville, PA | **5.5** | — | 492.05 | Beltzville only |
| Lehigh R. at **Walnutport**, PA | **8.0** | **7.0** | 350.27 | Walter **and** Beltzville |
| Lehigh R. at **Bethlehem**, PA | **16.0** | **12.0** | 210.94 | Walter **and** Beltzville |
| Delaware R. at **Easton**, PA | **22.0** (= 177.21 ft NGVD) | n/a | — | Monitored constraint, not a control gage |

### §2.2 State Variables (Observation Schema)

```json
{
  "pool_elevation_ft_NGVD29": "float",
  "inflow_cfs": "float",
  "prev_release_cfs": "float",
  "gate_openings_ft": "array[3] of float (flood control service gates)",
  "bypass_valves_open": "int (0-2)",
  "schedule_plan": "enum {A, B, C, D}",
  "target_pool_ft": "float (1300.0 winter | 1370.0 recreation season)",
  "season": "enum {winter, recreation_fill, recreation_release, drawdown}",
  "stage_WhiteHaven_ft": "float",
  "stage_Lehighton_ft": "float",
  "stage_Walnutport_ft": "float",
  "stage_Bethlehem_ft": "float",
  "stage_Easton_Delaware_ft": "float",
  "stages_trend": "enum {rising, stationary, falling_after_peak}",
  "event_peak_stage_ft": "map station -> float (max stage observed this event)",
  "pct_fc_storage_used": "float (0-1)",
  "beltzville_state": {
    "pool_el_ft": "float",
    "release_cfs": "float",
    "pct_fc_storage_used": "float"
  },
  "impounding_for_flood_emergency": "bool",
  "drbc_drought_declared": "bool",
  "whitewater_event_scheduled": "bool",
  "ice_jam_downstream": "bool",
  "comms_available": "bool",
  "embankment_distress": "bool",
  "gates_operable": "bool"
}
```

### §2.3 Decision Rules

**R-RELEASE (composite per-timestep decision; WCM Table 7-1 Parts A and B; §7-01, §7-03, §7-05)**
```pseudo
plan = R-PLAN(pool_elevation, stages, season)

active_min = R-MINFC       if plan in {C, D} or impounding_for_flood_emergency   # 100 cfs
           | R-MINDROUGHT  if drbc_drought_declared                              #  43 cfs
           | R-MINNORM                                                           #  50 cfs

CASE plan OF
  A:  release = inflow_cfs, holding pool at or near target_pool_ft;
        obligations = Minimum Release Schedule + Water Quality Release Schedule (R-TEMP)

  B:  release_combined = MaxReleaseSchedule_Rising(stages)      # §2.4.5 — MOST RESTRICTIVE gage governs
        release_walter  = R-BALANCE(release_combined, pct_fc_storage_used,
                                    beltzville_state.pct_fc_storage_used)
        summer: defer to Exhibit D Recreation Plan (NOT SUPPLIED)
        apply R-FILLING whenever pool exceeds any previously attained elevation

  C:  release = active_min                                       # store all inflow at BOTH projects
        on stages_trend == falling_after_peak, switch to MaxReleaseSchedule_Falling (§2.4.5)

  D:  release = pass inflow (hourly or finer), gates incrementally to full open;
        once outlet capacity exceeded, HOLD full open until pool < EL_SPILLWAY;
        then outflow = inflow until MaxReleaseSchedule_Rising (Plan B) can be resumed

release = clip(release, lower = active_min,
                        upper = min( Q_CHANNEL_CAP,            # conditional — see R-ATSITE
                                     outlet_capacity(pool_elevation),
                                     R-DOWNSTREAM limit ) )

subject to R-ROC (gate-position limits, NOT a discharge-rate limit)

IF pool_elevation > EL_SPILLWAY:
    total_outflow = release + spillway_discharge(pool_elevation)   # uncontrolled, §2.4.3
```

**R-MINNORM**, **R-MINFC**, **R-MINDROUGHT** (Minimum Release Schedule; WCM Table 7-1 Part B; §7-01, §7-05,c,3, §8-04)
```pseudo
Flows maintained at the reservoir OUTFLOW gaging station (White Haven for Walter):

   Regulation purpose                     Walter (cfs)   Beltzville (cfs)
   1. Flood control regulation (storing)      100              35     -> R-MINFC
   2. Normal regulation                        50              35     -> R-MINNORM
   3. Drought warning and drought               43              15     -> R-MINDROUGHT

Precedence: R-MINFC applies whenever storing under Plans C/D; R-MINDROUGHT relaxes
R-MINNORM under a declared DRBC drought warning or emergency; R-MINNORM otherwise.
The 50 cfs is a Commonwealth of Pennsylvania Fish Commission requirement set to protect
downstream brook trout habitat (Table 7-1 Part B).
```

**R-ATSITE (maximum release; WCM §4-09, §7-02a, §7-05,c,1, Table 7-2 notes 1–2)**
```pseudo
release ≤ 10,000 cfs  "during non-spillway flow conditions ... should not be exceeded IF POSSIBLE"
   equivalently: stage_WhiteHaven ≤ 8.4 ft (Table 7-1 Part B note 5)
release ≤ outlet_capacity(pool_elevation)   [≈17,000 cfs at EL_SPILLWAY]

EXCEPTION (Table 7-2 note 1): during FALLING stages after a peak, releases in excess of
10,000 cfs MAY be considered, provided the release — combined with Beltzville's — does not
cause any key Lehigh station to exceed max(event_peak_stage, flood stage), whichever governs.
CONFIRMED BY RECORD: the WY1996 maximum discharge of 11,452 cfs (Table 8-1, 29 Jan 1996)
exceeds 10,000 cfs -- the exception is exercised in practice, not merely permitted.
=> the 10,000 cfs cap is a CONDITIONAL constraint, not a physical invariant.
```

**R-ROC (rate of change — gate position; WCM §7-05,c,6; §7-16)**
```pseudo
FOR each flood control service gate:
   IF opening ≤ 6 ft:  |Δ opening| ≤ 1.0 ft per 10 minutes   (raising and lowering)
   IF opening > 6 ft:  |Δ opening| ≤ 1.5 ft per 10 minutes   (raising and lowering)

Purpose (§7-16): prevent bank sloughing, undercutting, excessive erosion, and danger to
human and animal life from sudden release change.

WAIVER (§7-05,b,4; §7-16): waived for embankment failure (gates full open after downstream
warning) or a downstream drowning requiring immediate closure.

NOTE: the WCM states NO discharge-domain rate limit. Any cfs/hr figure must be DERIVED
from these gate criteria through the gate rating (Plate 7-3) at the prevailing pool.
```

**R-DOWNSTREAM (control-point constraints; WCM Table 7-2 and its notes; §7-01)**
```pseudo
RISING or STATIONARY stages:
   release such that stage_WhiteHaven ≤ 8.0 ft, accounting for travel time (Table 4-8)
   and uncontrolled intervening drainage between the dam and each control station.
   Storage of inflow is initiated when a Flood Control Storage Initiation (action) stage
   is equaled or exceeded at Lehighton (9.5), Walnutport (7.0), or Bethlehem (12.0).

FALLING stages after peak:
   IF all key stages peaked BELOW flood stage:
       combined Walter+Beltzville release must not exceed flood stage at any key station
   IF any key stage peaked ABOVE flood stage:
       combined release must not exceed the recorded maximum stage for THAT EVENT

JOINT: Walnutport and Bethlehem are shared control points with Beltzville.
       Lehighton is Walter's alone; Pohopoco/Parryville (5.5 ft) is Beltzville's alone.

DELAWARE CONSTRAINT (§7-01; Table 7-2 note 5): no post-event evacuation release may raise
Easton / mainstem Delaware stages above what Delaware flooding alone would have produced.
Easton (Glendon) is NOT used as a control gage — Bethlehem is the lower-basin control station.
Coordinate with the NWS Philadelphia/Mt. Holly office for Delaware stage forecasts.

Travel times (Table 4-8, peak / low flow, hours):
   Walter→Lehighton 6/15; Lehighton→Walnutport 1/4; Walnutport→Bethlehem 4/16;
   Bethlehem→Easton 3/10; Beltzville→Parryville 1/3; Parryville→Walnutport 1/3.
```

**R-ZONE (seasonal rule curve — the normal operating target; WCM §7-01, Plate 7-2)**
```pseudo
target_pool_ft = 1300.0   # winter normal pool
Storage for recreation begins on/about 1 April; target date mid-May to reach 1370.0;
1370.0 is held and drawn on to make releases through mid-October; thereafter any
remaining water is released and the pool returns to 1300.0.

RATIONALE (§3-05,b,2(b)): 1370 is "the limit imposed to keep adequate flood control space
available since this volume can be quickly evacuated in advance of an oncoming storm event."

=> Recreation storage is ALWAYS subordinate and pre-releasable; it is NOT protected storage.
```

**R-PLAN (Schedule Plan selection — the Layer 2 spine; WCM Table 7-1 Part A; §7-05,a,2)**
```pseudo
Pool bands (Walter | Beltzville):
    Plan A: below 1300.0        | below 628.0
    Plan B: 1300-1450 (winter)  | 628.0-651.0      <- summer band is 1370-1450
    Plan D: above 1450.0        | above 651.0

IF pool_elevation > EL_SPILLWAY:                                 plan = D
ELIF target_pool_ft <= pool_elevation <= EL_SPILLWAY:            plan = B
ELSE:                                                             plan = A

target_pool_ft = 1300.0 (winter) | 1370.0 (summer) per R-ZONE -- so the Plan-A/Plan-B
boundary MOVES SEASONALLY. This is the single most consequential coupling between the
recreation rule curve and the flood-control plan logic.
```

**R-BALANCE (joint storage balancing with Beltzville; WCM §7-03, §7-05,a,2(a) ii[c]–[d], Plate 7-4)**
```pseudo
WHILE flood control storage is in use at BOTH projects:
    balance pct_fc_storage_used across Walter and Beltzville by evacuating FASTER,
    and with higher priority, from whichever project is using the LARGER percentage —
    "when conditions dictate making such large releases or when spillway flow is imminent."

The Maximum Release Schedule (Table 7-1 Part B, reproduced at §2.4.5) gives the maximum
COMBINED total release from the two projects as a function of current readings at the key
control stations; time of travel and intermediate-area flow are embedded in that table.
Individual-reservoir releases are then STAGED using the Time of Travel Schedule (§2.4.6)
so as not to exceed flood control stages or create greater damaging stages downstream
than have already occurred for that event.

Per-reservoir channel limits still bind under Condition 1 (all stations peaked at or below
flood stage): Walter <= 10,000 cfs (8.4 ft), Beltzville <= 1,500 cfs (5.30 ft at Parryville).
Under Condition 2 (one or more stations peaked above flood stage) those channel capacities
MAY be exceeded.

=> Walter's flood release is NOT computable from Walter's own state alone.
   Requires beltzville_state. (Same property as DKP-BELTZVILLE.)
```

**R-RECREATION (whitewater and in-lake recreation; WCM §3-05,b,2, §7-06, §8-03)**
```pseudo
CURRENT PLAN (2014, Exhibit D — NOT SUPPLIED): ~26 whitewater releases spread across the
season, plus fishing / fisheries-augmentation releases every day no whitewater is planned,
subject to hydrologic availability.

LEGACY PROGRAM (documented, superseded 2005+): five weekend events / seven days per year;
storage began the Monday two weeks before each event; release 144 cfs during storage
(or inflow, if lower) until pool reached 1309.0; if 1309.0 reached early, pass inflow;
event releases 500–750 cfs; cancellation evaluated by DRBC during drought warnings.

Recreation storage is evacuable at any time for flood control (§8-03,b).
In-lake boating/fishing impeded above EL_BOAT_LIMIT (1306.0).
```

**R-TEMP (Water Quality Release Schedule — selective withdrawal; WCM Table 7-1 Part B)**
```pseudo
The two 24-in bypass valves withdraw WARMER SURFACE water from the band
EL_BLEND_BOT (1297.0) to EL_BLEND_TOP (1300.0).
Blend that surface water with COOLER BOTTOM releases through the flood control outlet
works to meet a downstream temperature target NOT EXCEEDING 60-65 degrees F.

The blend ratio is the operator's discretionary variable; no schedule is given.
Applies under Plans A, B and C (Schedule A and B both cite the Water Quality Release
Schedule as a standing obligation). Withdrawal selectivity is lost once the pool exceeds
the recreation band, since the bypass draws only from a 3-ft window at conservation pool.
```

**R-FILLING (Initial Reservoir Filling Plan; WCM Table 7-1 Part A; Exhibit C)**
```pseudo
WHENEVER pool_elevation exceeds any elevation previously attained at the project,
apply the Initial Reservoir Filling Plan criteria of EXHIBIT C. Invoked explicitly
under Schedules B, C and D.
EXHIBIT C IS NOT SUPPLIED -- this rule is structurally present but its criteria are
out of coverage. An agent must escalate rather than infer filling constraints.
```

**R-FISH (fisheries accommodation; WCM §7-08)**
```pseudo
Limit pool fluctuation to ≤ 5 ft during May and June (in-lake spawning window).
Summer: augment releases to improve downstream aquatic habitat and buffer river temperature
(cool-water benefit). Avoid abrupt gate changes during above-normal flood-control releases.
Water control management needs TAKE PRECEDENCE over fishery accommodation.
```

**R-CADENCE (gate-change frequency; WCM §5-11)**
```pseudo
Non-flood: routine daily instructions from Water Control Personnel.
Flood, pool well into flood control zone: 2-3 gate changes per day expected.
Pool at or above EL_SPILLWAY: gate changes may occur EVERY HOUR.
Ceiling: "only under the most unusual circumstances" more often than once per hour.
=> defines the agent's admissible decision timestep.
```

**R-ALERT (alert and notification thresholds; WCM §5-10, §5-13, §5-08b)**
```pseudo
ALERT Water Control Personnel when:
   forecast rainfall ≥ 2.0 in in ≤ 12 hr near the dam;
   snow water equivalent ≥ 3.0 in above the project with warming forecast;
   a Flood Control Storage Initiation stage is forecast or approached at any Table 7-2 station;
   pool has risen ≥ 7 ft above normal operational pool in ≤ 12 hr;
   severe ice or temporary constrictions downstream; seepage/embankment concern;
   water quality problem; any condition requiring a gate-change or mode change.

NOTIFY Carbon and Luzerne County EMAs when release > Q_NOTIFY (2,000 cfs).
NOTIFY PA DCNR park manager (Hickory Run) on release changes affecting whitewater recreation.
NOTIFY EMAs of all significant gate changes increasing discharge when ice is present.
```

**R-ICE (ice-jam modification; WCM §7-02b, §7-05,a,2(b) ii[b])**
```pseudo
IF ice_jam_downstream threatens property or life:
   modify flood control regulation at BOTH projects to prevent severe downstream problems;
   evaluate case by case; coordinate with local EMAs;
   if gage readings are caused by ice or ice backwater, modify regulation accordingly;
   continually evaluate flood control storage at all projects so project integrity is not
   threatened while storing during an ice-jam emergency.
```

**R-DEVIATION (deviation from normal regulation; WCM §7-14)**
```pseudo
CATEGORY a - Emergencies (drowning, facility failure, upstream spill requiring storage,
   downstream pollution requiring flushing): ACT IMMEDIATELY unless the action would create
   equal or worse conditions; inform North Atlantic Division as soon as practicable.
CATEGORY b - Unplanned minor deviations (construction, stream crossings, bridge work,
   maintenance shutdowns; hours to days): analyze on merits against upstream watershed
   conditions, flood threat, lake conditions, alternatives; comply if no adverse effect on
   overall project operation; inform NAD as soon as practicable.
CATEGORY c - Planned deviations: PRIOR NAD review and approval required.

NOTE: the seasonal 1370 recreation pool is NOT a deviation in the 2014 WCM — it is the
normal rule curve (R-ZONE). This corrects DKP-FEWALTER-v1.0.
```

**R-EMERGENCY (emergency regulation; WCM §5-08a, §7-04, §7-05b, §9-01,a,5)**
```pseudo
comms_available == false: head dam operator (or assistant) directs regulation per the
   Schedule of Regulation (Table 7-1) and Exhibit B on his own initiative, computing inflow
   per §7-05d, while making every effort to restore communication.
gates_operable == false: notify District and Water Control immediately; if during a comms
   breakdown, regulate wholly or partially with whatever system is operational, at the
   Dam Operator's discretion.
embankment_distress == true: notify Water Control and downstream key personnel; if the
   embankment is established as failing, open flood control service gates FULL after
   warnings are issued; R-ROC is WAIVED; draw the lake down as quickly as controlled
   releases through the outlet works permit; follow the Emergency Action Plan.
Nuclear attack with total comms loss (§7-05,b,2): regulation reverts to dam operators per
   Table 7-1; impounded water may be released as potable supply when directed by higher
   authority.
```

**R-INFLOW (inflow determination; WCM §7-05d, Plate 7-7)**
```pseudo
Rising pool:  I = Q + S * 24 / (T2 - T1)
Falling pool: I = Q - S * 24 / (T2 - T1)
   I = average inflow (cfs) over T2-T1;  Q = average outflow (cfs) over T2-T1
   S = change in storage in day-second-feet (dsf) from Table 7-3;  T in hours
Forecast alternative (§6-02,b,1): 2-hr composite unit hydrograph (Plate 6-2) with
   DCP precipitation weights Blakeslee 35% / Stoddartsville 45% / damsite 20% (Table 6-1);
   initial loss 1.0 in, infiltration 0.20 in/hr (adjustable to match observed hydrographs).
```

### §2.4 Rating and Conversion Tables

#### §2.4.1 Elevation–Area–Capacity (WCM **Table 7-3, revised 2014**; TAB-A)

Full 1-ft resolution, El. 1247 → 1474. The **day-second-feet (dsf)** column is the unit `R-INFLOW` requires; linear interpolation between 1-ft rows is adequate. **Storage accounting and `R-INFLOW` are now executable** — this closes the principal v1.1 gap. Table 7-3 begins at 1247, not at the Pertinent Data streambed elevation of 1245.0 (both report zero storage).

<details>
<summary>Table 7-3 — full elevation–area–capacity (228 rows)</summary>

| Elev. (ft NGVD29) | Area (ac) | Storage (ac-ft) | Storage (dsf) | |
|---|---|---|---|---|
| 1247 | 0.00 | 0.00 | 0.00 | |
| 1248 | 0.00 | 0.00 | 0.00 | |
| 1249 | 0.02 | 0.01 | 0.01 | |
| 1250 | 0.04 | 0.04 | 0.02 | ← `EL_INACTIVE` |
| 1251 | 0.07 | 0.10 | 0.05 | |
| 1252 | 0.10 | 0.19 | 0.10 | |
| 1253 | 0.19 | 0.32 | 0.16 | |
| 1254 | 0.57 | 0.66 | 0.33 | |
| 1255 | 1.16 | 1.50 | 0.76 | |
| 1256 | 1.89 | 3.03 | 1.53 | |
| 1257 | 2.67 | 5.30 | 2.67 | |
| 1258 | 3.49 | 8.38 | 4.23 | |
| 1259 | 4.12 | 12.20 | 6.15 | |
| 1260 | 4.71 | 16.61 | 8.37 | |
| 1261 | 5.40 | 21.64 | 10.91 | |
| 1262 | 6.24 | 27.45 | 13.84 | |
| 1263 | 7.26 | 34.18 | 17.23 | |
| 1264 | 8.74 | 42.11 | 21.23 | |
| 1265 | 11.06 | 51.95 | 26.19 | |
| 1266 | 13.68 | 64.30 | 32.42 | |
| 1267 | 16.44 | 79.37 | 40.02 | |
| 1268 | 18.95 | 97.05 | 48.93 | |
| 1269 | 21.71 | 117.38 | 59.18 | |
| 1270 | 24.22 | 140.37 | 70.77 | |
| 1271 | 26.38 | 165.69 | 83.54 | |
| 1272 | 28.49 | 193.16 | 97.38 | |
| 1273 | 30.43 | 222.60 | 112.23 | |
| 1274 | 32.41 | 254.01 | 128.07 | |
| 1275 | 34.40 | 287.42 | 144.91 | |
| 1276 | 36.74 | 322.94 | 162.82 | |
| 1277 | 39.69 | 361.11 | 182.06 | |
| 1278 | 42.98 | 402.37 | 202.86 | |
| 1279 | 46.77 | 447.26 | 225.49 | |
| 1280 | 50.73 | 495.99 | 250.06 | |
| 1281 | 53.93 | 548.41 | 276.49 | |
| 1282 | 56.35 | 603.59 | 304.31 | |
| 1283 | 58.65 | 661.11 | 333.31 | |
| 1284 | 60.76 | 720.83 | 363.42 | |
| 1285 | 62.65 | 782.56 | 394.54 | |
| 1286 | 64.50 | 846.11 | 426.58 | |
| 1287 | 66.54 | 911.60 | 459.60 | |
| 1288 | 69.05 | 979.39 | 493.78 | |
| 1289 | 71.76 | 1049.76 | 529.25 | |
| 1290 | 74.28 | 1122.84 | 566.10 | |
| 1291 | 76.57 | 1198.27 | 604.13 | |
| 1292 | 78.82 | 1275.95 | 643.29 | |
| 1293 | 81.41 | 1356.02 | 683.66 | |
| 1294 | 84.23 | 1438.89 | 725.44 | |
| 1295 | 86.82 | 1524.41 | 768.56 | |
| 1296 | 89.62 | 1612.64 | 813.04 | |
| 1297 | 92.26 | 1703.59 | 858.89 | ← `EL_BYPASS_INVERT` |
| 1298 | 94.96 | 1797.20 | 906.09 | |
| 1299 | 97.67 | 1893.48 | 954.63 | |
| 1300 | 100.50 | 1992.61 | 1004.61 | ← **`EL_CONSERVATION`** |
| 1301 | 103.26 | 2094.46 | 1055.96 | |
| 1302 | 106.27 | 2199.25 | 1108.79 | |
| 1303 | 109.31 | 2306.99 | 1163.11 | |
| 1304 | 112.60 | 2417.99 | 1219.07 | |
| 1305 | 115.51 | 2532.08 | 1276.59 | |
| 1306 | 118.24 | 2648.94 | 1335.51 | ← `EL_BOAT_LIMIT` |
| 1307 | 121.37 | 2768.72 | 1395.90 | |
| 1308 | 124.97 | 2891.83 | 1457.96 | |
| 1309 | 128.38 | 3018.58 | 1521.87 | ← `EL_ACCESS_ROAD` |
| 1310 | 131.26 | 3148.43 | 1587.33 | |
| 1311 | 134.14 | 3281.12 | 1654.23 | |
| 1312 | 137.21 | 3416.77 | 1722.62 | |
| 1313 | 140.45 | 3555.60 | 1792.62 | |
| 1314 | 143.57 | 3697.62 | 1864.22 | |
| 1315 | 146.56 | 3842.68 | 1937.35 | |
| 1316 | 150.26 | 3991.02 | 2012.14 | |
| 1317 | 154.28 | 4143.28 | 2088.90 | |
| 1318 | 157.57 | 4299.25 | 2167.54 | |
| 1319 | 160.79 | 4458.43 | 2247.79 | |
| 1320 | 164.13 | 4620.88 | 2329.69 | |
| 1321 | 167.80 | 4786.79 | 2413.34 | |
| 1322 | 171.75 | 4956.54 | 2498.92 | |
| 1323 | 175.88 | 5130.32 | 2586.54 | |
| 1324 | 180.39 | 5308.40 | 2676.32 | |
| 1325 | 185.61 | 5491.28 | 2768.52 | |
| 1326 | 191.41 | 5679.85 | 2863.59 | |
| 1327 | 196.16 | 5873.63 | 2961.29 | |
| 1328 | 200.59 | 6072.04 | 3061.32 | |
| 1329 | 205.26 | 6274.91 | 3163.60 | |
| 1330 | 210.31 | 6482.73 | 3268.38 | |
| 1331 | 215.71 | 6695.66 | 3375.73 | |
| 1332 | 221.50 | 6914.26 | 3485.94 | |
| 1333 | 227.67 | 7138.83 | 3599.16 | |
| 1334 | 234.42 | 7369.79 | 3715.60 | |
| 1335 | 241.17 | 7607.65 | 3835.52 | |
| 1336 | 247.85 | 7852.13 | 3958.78 | |
| 1337 | 254.96 | 8103.51 | 4085.52 | |
| 1338 | 261.42 | 8361.75 | 4215.71 | |
| 1339 | 268.17 | 8626.48 | 4349.19 | |
| 1340 | 275.86 | 8898.44 | 4486.30 | |
| 1341 | 283.19 | 9178.00 | 4627.24 | |
| 1342 | 290.43 | 9464.82 | 4771.85 | |
| 1343 | 298.05 | 9759.05 | 4920.19 | |
| 1344 | 305.41 | 10060.78 | 5072.31 | |
| 1345 | 313.25 | 10370.02 | 5228.22 | |
| 1346 | 321.86 | 10687.63 | 5388.35 | |
| 1347 | 330.21 | 11013.69 | 5552.74 | |
| 1348 | 338.11 | 11347.91 | 5721.24 | |
| 1349 | 345.87 | 11689.92 | 5893.67 | |
| 1350 | 353.90 | 12039.87 | 6070.10 | |
| 1351 | 361.89 | 12397.75 | 6250.53 | |
| 1352 | 368.69 | 12763.12 | 6434.74 | |
| 1353 | 375.42 | 13135.13 | 6622.30 | |
| 1354 | 382.38 | 13514.05 | 6813.34 | |
| 1355 | 389.23 | 13899.81 | 7007.82 | |
| 1356 | 397.12 | 14292.87 | 7205.99 | |
| 1357 | 405.77 | 14694.24 | 7408.35 | |
| 1358 | 414.26 | 15104.32 | 7615.09 | |
| 1359 | 422.40 | 15522.66 | 7826.01 | |
| 1360 | 430.94 | 15949.30 | 8041.11 | |
| 1361 | 439.66 | 16384.60 | 8260.57 | |
| 1362 | 448.58 | 16828.66 | 8484.45 | |
| 1363 | 457.87 | 17281.93 | 8712.97 | |
| 1364 | 466.42 | 17744.14 | 8946.00 | |
| 1365 | 474.76 | 18214.74 | 9183.26 | |
| 1366 | 483.13 | 18693.69 | 9424.74 | |
| 1367 | 491.50 | 19180.97 | 9670.41 | |
| 1368 | 500.32 | 19676.85 | 9920.41 | |
| 1369 | 509.70 | 20181.80 | 10174.99 | |
| 1370 | 519.71 | 20696.47 | 10434.47 | ← **`EL_REC_SUMMER`** |
| 1371 | 530.42 | 21221.30 | 10699.07 | |
| 1372 | 555.30 | 21761.87 | 10971.61 | |
| 1373 | 595.89 | 22339.82 | 11262.99 | |
| 1374 | 619.02 | 22948.00 | 11569.62 | |
| 1375 | 635.99 | 23575.93 | 11886.20 | |
| 1376 | 649.70 | 24218.86 | 12210.34 | |
| 1377 | 662.74 | 24875.11 | 12541.20 | |
| 1378 | 675.84 | 25544.46 | 12878.67 | |
| 1379 | 688.23 | 26226.48 | 13222.52 | |
| 1380 | 701.11 | 26921.10 | 13572.72 | |
| 1381 | 713.53 | 27628.56 | 13929.40 | |
| 1382 | 725.75 | 28348.13 | 14292.19 | |
| 1383 | 737.08 | 29079.64 | 14660.99 | |
| 1384 | 748.87 | 29822.44 | 15035.48 | |
| 1385 | 761.42 | 30577.62 | 15416.22 | |
| 1386 | 773.26 | 31345.10 | 15803.16 | |
| 1387 | 783.96 | 32123.65 | 16195.67 | |
| 1388 | 795.84 | 32913.48 | 16593.88 | |
| 1389 | 808.26 | 33715.53 | 16998.25 | |
| 1390 | 820.40 | 34529.86 | 17408.81 | |
| 1391 | 832.02 | 35356.01 | 17825.32 | |
| 1392 | 843.97 | 36194.09 | 18247.85 | ← `EL_DROUGHT_MAX` |
| 1393 | 856.25 | 37044.10 | 18676.40 | |
| 1394 | 869.68 | 37907.01 | 19111.45 | |
| 1395 | 882.26 | 38783.08 | 19553.14 | |
| 1396 | 894.34 | 39671.38 | 20000.99 | |
| 1397 | 906.20 | 40571.66 | 20454.88 | |
| 1398 | 917.99 | 41483.74 | 20914.72 | |
| 1399 | 929.27 | 42407.40 | 21380.40 | |
| 1400 | 940.50 | 43342.31 | 21851.75 | |
| 1401 | 951.89 | 44288.47 | 22328.77 | |
| 1402 | 963.46 | 45246.15 | 22811.60 | |
| 1403 | 975.30 | 46215.54 | 23300.34 | |
| 1404 | 986.83 | 47196.63 | 23794.97 | |
| 1405 | 998.41 | 48189.21 | 24295.40 | |
| 1406 | 1010.12 | 49193.50 | 24801.72 | |
| 1407 | 1021.77 | 50209.47 | 25313.94 | |
| 1408 | 1034.16 | 51237.28 | 25832.13 | |
| 1409 | 1048.62 | 52278.62 | 26357.14 | |
| 1410 | 1062.33 | 53334.09 | 26889.27 | |
| 1411 | 1076.21 | 54403.33 | 27428.35 | |
| 1412 | 1090.65 | 55486.81 | 27974.60 | |
| 1413 | 1104.98 | 56584.62 | 28528.08 | |
| 1414 | 1119.45 | 57696.87 | 29088.84 | |
| 1415 | 1134.43 | 58823.72 | 29656.96 | |
| 1416 | 1148.95 | 59965.41 | 30232.56 | |
| 1417 | 1164.37 | 61122.02 | 30815.69 | |
| 1418 | 1179.97 | 62294.14 | 31406.63 | |
| 1419 | 1195.76 | 63482.01 | 32005.51 | |
| 1420 | 1213.15 | 64686.35 | 32612.70 | |
| 1421 | 1231.21 | 65908.44 | 33228.84 | |
| 1422 | 1251.07 | 67149.47 | 33854.52 | |
| 1423 | 1269.65 | 68410.02 | 34490.05 | |
| 1424 | 1287.24 | 69688.46 | 35134.60 | |
| 1425 | 1304.10 | 70984.15 | 35787.84 | |
| 1426 | 1321.04 | 72296.70 | 36449.59 | |
| 1427 | 1338.38 | 73626.37 | 37119.96 | |
| 1428 | 1356.51 | 74973.79 | 37799.29 | |
| 1429 | 1375.41 | 76339.66 | 38487.92 | |
| 1430 | 1395.42 | 77725.04 | 39186.38 | |
| 1431 | 1415.00 | 79130.40 | 39894.91 | |
| 1432 | 1433.86 | 80554.80 | 40613.05 | |
| 1433 | 1454.45 | 81998.51 | 41340.92 | |
| 1434 | 1477.39 | 83464.87 | 42080.21 | |
| 1435 | 1500.95 | 84953.31 | 42830.63 | |
| 1436 | 1529.73 | 86468.39 | 43594.48 | |
| 1437 | 1553.49 | 88010.95 | 44372.19 | |
| 1438 | 1572.72 | 89574.11 | 45160.28 | |
| 1439 | 1591.82 | 91156.45 | 45958.05 | |
| 1440 | 1611.06 | 92757.80 | 46765.39 | |
| 1441 | 1630.74 | 94378.69 | 47582.59 | |
| 1442 | 1650.75 | 96019.42 | 48409.79 | |
| 1443 | 1671.24 | 97680.38 | 49247.19 | |
| 1444 | 1692.51 | 99362.19 | 50095.11 | |
| 1445 | 1713.33 | 101065.15 | 50953.68 | |
| 1446 | 1733.07 | 102788.42 | 51822.49 | |
| 1447 | 1752.98 | 104531.48 | 52701.29 | |
| 1448 | 1772.72 | 106294.34 | 53590.07 | |
| 1449 | 1791.79 | 108076.58 | 54488.61 | |
| 1450 | 1811.69 | 109878.27 | 55396.96 | ← **`EL_SPILLWAY`** |
| 1451 | 1831.37 | 111699.82 | 56315.33 | |
| 1452 | 1851.36 | 113541.21 | 57243.70 | |
| 1453 | 1871.18 | 115402.45 | 58182.07 | |
| 1454 | 1890.81 | 117283.46 | 59130.41 | |
| 1455 | 1910.38 | 119184.11 | 60088.66 | |
| 1456 | 1929.87 | 121104.23 | 61056.72 | |
| 1457 | 1949.84 | 123044.03 | 62034.70 | |
| 1458 | 1972.16 | 125004.69 | 63023.20 | |
| 1459 | 1995.92 | 126988.81 | 64023.53 | |
| 1460 | 2019.53 | 128996.57 | 65035.77 | |
| 1461 | 2042.64 | 131027.72 | 66059.81 | |
| 1462 | 2065.47 | 133081.77 | 67095.39 | |
| 1463 | 2088.36 | 135158.57 | 68142.45 | |
| 1464 | 2111.92 | 137258.72 | 69201.28 | |
| 1465 | 2136.81 | 139382.91 | 70272.22 | |
| 1466 | 2162.56 | 141532.53 | 71355.99 | |
| 1467 | 2187.92 | 143707.78 | 72452.68 | |
| 1468 | 2214.93 | 145908.94 | 73562.43 | |
| 1469 | 2244.71 | 148138.56 | 74686.53 | |
| 1470 | 2276.74 | 150399.17 | 75826.25 | |
| 1471 | 2311.39 | 152693.01 | 76982.73 | |
| 1472 | 2349.04 | 155022.79 | 78157.33 | |
| 1473 | 2391.96 | 157392.55 | 79352.08 | |
| 1474 | 2460.27 | 159814.09 | 80572.94 | ← **`EL_TOP_OF_DAM`** |

</details>

Derived quantities (all recomputed from Table 7-3, not quoted):

| Quantity | Value |
|---|---|
| Conservation storage at 1300.0 | 1,992.61 ac-ft |
| Recreation storage, 1300.0 → 1370.0 | 18,703.86 ac-ft |
| Flood control storage, 1300.0 → 1450.0 | **107,885.66 ac-ft** (WCM §7-05 states 107,886 ✓) |
| Storage at 1449.0 − 1300.0 | 106,083.97 ac-ft — *this is the erroneous denominator used in Table 8-1; see Provenance 3(t)* |
| Surcharge, 1450.0 → 1474.0 | 49,935.82 ac-ft |
| Runoff equivalence (288 mi²) | 1 in = 15,360 ac-ft |

#### §2.4.2 Outlet Works Rating

Plate 7-3 (partial and full gate ratings for one, two and three service gates) **not supplied**. Available anchors only:

| Condition | Capacity |
|---|---|
| Three gates full open at El. 1450.0 | ≈ 17,000 cfs (§7-02a; §7-05,c,4) |
| Max release, Standard Project Flood routing | 16,950 cfs (§8-02c) |
| Bypass system (two 24-in butterfly valves, weir crest 1297.0) | "limited discharge capacity" — value not stated (§4-08) |

`outlet_capacity(pool_elevation)` is **out of coverage** below the crest.

#### §2.4.3 Spillway Rating

Uncontrolled ogee, crest 1,450.0, width 450 ft; "flow over the spillway is not subject to regulation by any appurtenances" (§2-03b). Plate 7-5 (spillway discharge rating curve) **not supplied**. Anchors:

| Condition | Discharge |
|---|---|
| Design discharge, total (conduit + spillway), Pertinent Data | 193,721 cfs |
| Spillway alone, design (§2-03b) | ≈ 170,000 cfs |
| SDF routing at El. 1470.9 — combined max release (§8-02b) | 184,000 cfs |

*Three figures, not mutually reconciled — see Provenance 3(g).*

#### §2.4.4 Downstream Station Ratings

Tables 8-3 through 8-11 (stage–discharge ratings at Stoddartsville, Blakeslee, White Haven, Lehighton, Walnutport, Bethlehem, Glendon, Kresgeville, Parryville) reside in **TAB-A and were not supplied**. `R-DOWNSTREAM` stage constraints cannot be converted to flow limits. Gage datums (§2.1, field 1.13) permit stage↔elevation conversion only.

Available flow–stage pairs from Table 4-6 (floods of record) provide sparse anchors: Lehighton 13.5 ft ↔ 25,500 cfs (Jun 2006); Walnutport 12.5 ↔ 41,100; Bethlehem 17.7 ↔ 49,000.

#### §2.4.5 Maximum Release Schedule (WCM **Table 7-1 Part B**; TAB-A)

**Combined** total release from Beltzville Lake **and** F.E. Walter Reservoir. *Initial rising stages:*

| Bethlehem (ft) | Walnutport (ft) | Lehighton (ft) | Max allowable **combined** release (cfs) |
|---|---|---|---|
| below 7.0 | below 2.5 | below 5.7 | **11,500** |
| 7.0 – 7.7 | 2.5 – 3.7 | 5.7 – 6.6 | 8,000 |
| 7.7 – 8.3 | 3.7 – 4.5 | 6.6 – 7.5 | 6,000 |
| 8.3 – 8.8 | 4.5 – 5.2 | 7.5 – 8.2 | 4,000 |
| 8.8 – 9.4 | 5.2 – 5.8 | 8.2 – 9.0 | 2,000 |
| 9.4 – 12.0 | 5.8 – 7.0 | 9.0 – 9.5 | 1,000 |
| above 12.0 | above 7.0 | above 9.5 | *(store — see Minimum Release Schedule)* |

Read the **most restrictive** row: "stage need be exceeded at only one control gage" (note 1). Lehighton is affected by Walter regulation only (note 3). Per-reservoir channel limits: Parryville 5.30 ft = 1,500 cfs (note 4); White Haven 8.4 ft = 10,000 cfs (note 5). Coordinate with NWS Philadelphia/Mt. Holly on mainstem Delaware conditions before releasing (note 6).

*Falling stages after peaking:*

| Condition | Rule |
|---|---|
| **1 — all stations peaked at or below flood stage** | Combined release, routed to the key stations, must not exceed the **action stage** there. Delaware from Easton to Trenton must be falling or non-critical. Per-reservoir channel capacities (10,000 / 1,500 cfs) **still bind**. Lower the reservoir using the larger percent of flood storage with top priority. |
| **2 — one or more stations peaked above flood stage** | Combined release must not exceed the **maximum flood stage reached during that event**. Per-reservoir channel capacities **may be exceeded**. Same balancing priority. |

Note the asymmetry: Condition 1 targets *action* stage, which is stricter than the flood stage that WCM §7-05,a,2(b) ii[a] describes in prose. Table 7-1 governs.

#### §2.4.6 Time of Travel Schedule (WCM **Table 7-1 Part B**; TAB-A)

| Reach | Peak flow (hr) | Low flow (hr) |
|---|---|---|
| F.E. Walter → Lehighton | 6 | **16** |
| Lehighton → Walnutport | 1 | 4 |
| Walnutport → Bethlehem | 4 | 16 |
| Bethlehem → Easton | 3 | 10 |
| Parryville → Walnutport | 1 | 3 |
| Beltzville → Parryville | 1 | 3 |

Peak-flow times from HEC-1 calibration to the August 1955 flood; low-flow times from House Doc. 522, 87th Cong., App. M (April 1960). *The Walter→Lehighton low-flow time is 16 hr here and 15 hr in Table 4-8 — see Provenance 3(q).*

### §2.5 Empirical Operating Record

#### §2.5.1 Actual regulation record (project operational from Feb 1961)

| Event | Max pool (ft NGVD) | % FC storage | Peak inflow (cfs) | Max release (cfs) | Duration above 1300 | Source |
|---|---|---|---|---|---|---|
| **Jun 2006** (record pool) | **1,441.73** (29 Jun) | — | 22,723 | ≈ 9,610 | — | §4-06b; §8-02,d,6 |
| **Sep 1985** | 1,417.10 (28 Sep) | — | — | — | — | §4-06b |
| **Jan 1976** | 1,377.80 | 22% | 10,198 | 4,591 | ≈ 16 days | §8-02,d,5; Plate 8-7 |
| **Jun 1972** (Agnes) | 1,398.2 | 37% | 9,790 | ≈ 4,126 | ≈ 32 days | §8-02,d,4; Plate 8-6 |

Note: the June 2006 event occurred **during summer recreation storage** (§8-02,d,6) — i.e. the record pool was reached from an elevated starting pool, which is the single most operationally informative fact in this record for evaluating the R-ZONE / flood-space trade-off. Plates 8-6 and 8-7 are reproductions of the actual Monthly Water Control Charts (independent regulation records).

#### §2.5.2 Pre-project floods routed under the current Schedule of Regulation

These are **hypothetical routings**, not regulation records — the project was not operational.

| Event | Max pool (ft) | % FC storage | Peak inflow (cfs) | Note |
|---|---|---|---|---|
| Aug 1955 (Connie/Diane; basin flood of record) | 1,418.69 | 57% | 52,200 | No spillway flow. Min release 100 cfs initiated when Walnutport reached **6.3 ft**; only Walnutport and Bethlehem gages then operational (§8-02,d,2) |
| May 1942 | 1,399.15 | 38% | 26,400 | No spillway flow; Lehighton gage not yet operational (§8-02,d,3) |

**The 6.3 ft figure above is the provenance of v1.0's erroneous `STAGE_FCI_WALNUTPORT`** — an event-specific value from a 1955 back-routing narrative, not a standing rule.

#### §2.5.3 Design flood routings (§8-02b, §8-02c, §8-02,d,1)

| Flood | Peak inflow (cfs) | Max pool (ft) | Max outflow (cfs) | Note |
|---|---|---|---|---|
| Spillway Design Flood (SPS + PMP 5 days later) | 203,000 (preceded by SPF 79,150) | **1,470.9** | 184,000 combined | ~90% of surcharge used for ~81 hr; within 3.1 ft of top of dam. Total storm rainfall 25.6 in, 21.9 in excess (HMR 51/52) |
| Standard Project Flood | 79,150 | 1,450.0 | 16,950 | **No spillway flow**; releases exceeded 10,000 cfs for ~6 hr |
| Reservoir Design Flood | 93% of SPF | — | — | Largest flood just contained with no spillway flow |

SDF/SPF routing logic (an explicit, machine-checkable statement of the operating rule): pass inflow until it reaches 2,000 cfs → cut to 100 cfs minimum → hold until flood control storage exhausted and pool reaches 1450.0 → match inflow hourly up to outlet capacity, all gates full open → hold full open until pool recedes below crest → pass inflow until it recedes to 10,000 cfs → hold 10,000 cfs until pool reaches 1300.0 or inflow rises again.

#### §2.5.4 Annual maximum pool, flood storage utilized, and discharge (WCM **Table 8-1**; WY1961–WY2013)

53 water years. Percent-of-total values are **as printed**; they use an erroneous 106,084 ac-ft denominator (Provenance 3(t)). Superscript ⁽ᵈ⁾ marks rows the WCM flags as "impacted by storage prior to event."

| WY | Max pool date | Max pool (ft NGVD) | FC storage (ac-ft) | % (as printed) | Max discharge (cfs) | Discharge date |
|---|---|---|---|---|---|---|
| 1961 | 27 Feb | 1350.67 ⁽ᵃ⁾ | 10,003 | 9 | 4,110 | 1 Mar |
| 1962 | 2 Apr | 1334.25 | 5,206 | 5 | 3,540 | 3 Apr |
| 1963 | 30 Mar | 1367.94 | 17,894 | 17 | 7,070 | 31 Mar |
| 1964 | 11 Mar | 1360.07 | 13,834 | 13 | 4,680 | 12 Mar |
| 1965 | 29 Nov | 1352.03 | 10,516 | 10 | 1,660 | 11 Feb |
| 1966 | 30 May | 1391.72 | 34,433 | 32 | 3,510 | 21 Dec |
| 1967 | 7 Aug | 1367.56 | 17,682 | 17 | 2,820 | 30 Mar |
| 1968 | 12 Sep | 1319.60 | 2,340 | 2 | 2,840 | 18 Mar |
| 1969 | 5 Aug | 1373.30 | 21,097 | 20 | 3,350 | 26 Mar |
| 1970 | 5 Apr | 1366.85 | 17,288 | 16 | 4,410 | 7 Apr |
| 1971 | 16 Feb | 1329.55 | 4,161 | 4 | 3,120 | 17 Mar |
| 1972 | 26 Jun | **2398.2** ⁽ᵇ⁾ | 40,003 | 38 | 4,010 | 1 Jun |
| 1973 | 3 Jul | 1397.20 | 39,469 | 37 | 4,760 | 4 Jul |
| 1974 | 9 Dec | 1351.40 | 10,139 | 10 | 4,740 | 24 Dec |
| 1975 | 26 Feb | 1362.70 | 15,128 | 14 | 4,290 | 10 Dec |
| 1976 | 29 Jan | 1377.80 | 24,020 | 23 | 4,390 | 31 Jan |
| 1977 | 20 Oct | 1360.60 | 13,830 | 13 | 3,750 | 14 Oct |
| 1978 | 29 Mar | 1371.77 | 20,133 | 19 | 6,180 | 30 Mar |
| 1979 | 26 Jan | 1366.82 | 17,271 | 16 | 5,270 | 27 Jan |
| 1980 | 23 Mar | 1365.58 | 16,582 | 16 | 4,750 | 24 Mar |
| 1981 | 19 May | 1397.27 | 29,175 | 28 | 4,590 | 24 Feb |
| 1982 | 19 Apr | 1381.96 | 26,926 | 25 | 3,280 | 20 Apr |
| 1983 | 17 Apr | 1389.14 | 32,339 | 30 | 8,230 | 13 Apr |
| 1984 | 7 Apr | 1396.70 | 38,668 | 36 | 8,050 | 9 Apr |
| 1985 | 28 Sep | **1417.10** | 59,301 | 56 | 8,390 | 29 Sep |
| 1986 | 1 Oct | 1397.20 | 39,113 | 37 | 6,040 | 18 Mar |
| 1987 | 6 Apr | 1382.60 | 27,390 | 26 | 6,870 | 15 Sep |
| 1988 | 22 May | 1344.89 | 8,068 | 7 | 4,230 | 22 May |
| 1989 | 7 May | 1375.93 | 22,768 | 21 | 7,440 | 8 May |
| 1990 | 18 May | 1340.27 | 6,728 | 6 | 3,800 | 18 May |
| 1991 | 5 Dec | 1339.76 | 6,589 | 6 | 3,970 | 5 Dec |
| 1992 | 25 Nov | 1343.83 | 7,761 | 7 | 3,450 | 2 Jun |
| 1993 | 3 Apr | 1379.58 | 25,222 | 24 | 8,400 | 4 Apr |
| 1994 | 29 Aug | 1388.45 | 31,804 | 30 | 8,580 | 30 Nov |
| 1995 | 2 Oct | 1355.95 | 12,048 | 11 | 4,162 | 16 Jan |
| 1996 | 21 Jan | 1397.73 | 39,651 | 37 | **11,452** ⁽ᶜ⁾ | 29 Jan |
| 1997 | 10 Nov | 1366.25 | 16,955 | 16 | 9,800 | 10 Nov |
| 1998 | 16 Jun | 1332.13 | 4,729 | 4 | 4,863 | 10 Mar |
| 1999 | 24 Sep | 1383.35 ⁽ᵈ⁾ | 27,934 | 26 | 5,990 | 25 Jan |
| 2000 | 1 Oct | 1378.37 ⁽ᵈ⁾ | 24,405 | 23 | 3,560 | 28 Feb |
| 2001 | 18 Dec | 1349.77 | 9,674 | 9 | 4,041 | 18 Dec |
| 2002 | 29 May | 1399.23 ⁽ᵈ⁾ | 40,920 | 39 | 8,242 | 29 May |
| 2003 | 23 Jun | 1383.37 | 27,947 | 26 | 7,095 | 26 Jun |
| 2004 | 19 Sep | 1401.38 | 42,924 | 40 | 7,445 | 13 Dec |
| 2005 | 4 Apr | 1407.88 ⁽ᵈ⁾ | 50,327 | 47 | 8,140 | 6 Apr |
| 2006 | 29 Jun | **1441.73** ⁽ᵈ⁾ | 91,830 | **87** | 9,820 | 8 Jul |
| 2007 | 18 Apr | 1382.29 | 27,165 | 26 | 4,030 | 20 Nov |
| 2008 | 9 Mar | 1391.68 ⁽ᵈ⁾ | 34,399 | 32 | 6,990 | 10 Mar |
| 2009 | 11 May | 1373.05 ⁽ᵈ⁾ | 22,370 | 21 | 4,750 | 15 Dec |
| 2010 | 16 Mar | 1380.41 | 27,211 | 26 | 5,260 | 28 Jan |
| 2011 | 12 Mar | **1414** ⁽ᵉ⁾ | 28,832 | 27 | 8,560 | 13 Mar |
| 2012 | 2 Oct | 1376.70 ⁽ᵈ⁾ | 24,563 | 23 | 5,700 | 2 Oct |
| 2013 | 3 Jul | 1373.12 ⁽ᵈ⁾ | 22,458 | 21 | 4,390 | 31 Oct |

⁽ᵃ⁾ WY1961 falls inside the initial filling period (final storage began 17 Feb 1961; conservation pool filled June 1961) — a filling record, not a regulation record. ⁽ᵇ⁾ Printed as 2398.2; unambiguously 1398.2 (matches §8-02,d,4). ⁽ᶜ⁾ Exceeds the 10,000 cfs channel capacity — empirical confirmation of the `R-ATSITE` exception. ⁽ᵈ⁾ WCM note 3, "impacted by storage prior to event." ⁽ᵉ⁾ **Internally inconsistent:** 28,832 ac-ft recomputes from Table 7-3 to El. ≈1385.3, not 1414; at 1414 the storage would be ~55,704 ac-ft. See Provenance 3(u).

**Series homogeneity warning (WCM note 2):** maximum discharges for WY1961–1993 are **daily mean** values; from WY1994 onward they are **instantaneous peak** values. The series must not be treated as homogeneous — the apparent step up after 1993 is a measurement-convention artifact, not a regulation change.

**Behavioral signal.** Median annual maximum pool sits near 1375–1380, i.e. ~20–25% of flood storage — in a typical year Walter uses a quarter of its allocation. Only **one** year in 53 exceeds 60%: WY2006 at 87%, and that event began from an elevated recreation pool. The next two are WY1985 (56%) and WY2005 (47%). The distribution is therefore strongly right-skewed with a single dominant outlier, which is the correct prior for an agent reasoning about how often deep flood-storage use is warranted. Maximum pool and maximum discharge frequently occur in **different events within the same water year** (e.g. WY1965: pool 29 Nov, discharge 11 Feb) — the two columns are independent annual maxima, not paired event data.

#### §2.5.5 Natural vs. regulated peak-discharge frequency (Tables 8-12, 8-13)

Discharge in 1,000 cfs. Natural (unregulated) / **Regulated** (Walter alone at White Haven and Lehighton; Walter + Beltzville below Walnutport):

| Return period | White Haven (290 mi²) | Lehighton (591 mi²) | Walnutport (889 mi²) | Bethlehem (1,279 mi²) | Glendon (1,359 mi²) |
|---|---|---|---|---|---|
| 2-yr | 5.8 / **5.8** | 17.0 / **12.0** | 18.7 / **15.7** | 23.0 / **20.6** | 23.4 / **21.3** |
| 10-yr | 14.6 / **8.3** | 35.0 / **16.1** | 39.0 / **21.7** | 46.9 / **32.5** | 48.0 / **34.5** |
| 50-yr | 27.7 / **8.5** | 56.9 / **27.5** | 64.0 / **34.4** | 75.8 / **50.6** | 76.0 / **53.3** |
| 100-yr | 38.8 / **8.5** | 68.4 / **33.2** | 78.0 / **41.8** | 90.8 / **61.1** | 91.5 / **64.2** |
| 500-yr | 60.7 / **8.9** | 102 / **48.9** | 117 / **62.8** | 134 / **89.4** | 135 / **94.4** |
| 1000-yr | 78.0 / **12.5** | 118 / **56.6** | 138 / **74.1** | 150 / **102** | 155 / **109** |

Behavioral signal: the regulated White Haven curve **flattens at 8.5 × 10³ cfs from the 10-yr through the 100-yr event** — the numerical signature of the 10,000 cfs channel-capacity rule binding across the entire design range immediately below the dam, and the sharpest single test of whether an agent has internalized `R-ATSITE`. It rises again only at the 500- and 1000-yr events, where surcharge and spillway flow defeat control.

#### §2.5.6 System flood reduction, natural vs. regulated (WCM **Table 8-2**)

Peak discharge (cfs) at the three Lehigh control stations, with and without regulation by F.E. Walter and Beltzville:

| Event | Lehighton nat. | Lehighton reg. | Walnutport nat. | Walnutport reg. | Bethlehem nat. | Bethlehem reg. |
|---|---|---|---|---|---|---|
| June 1972 | n/a | n/a | 71,000 * | 42,000 * | 88,000 * | 64,000 * |
| January 1976 | n/a | n/a | 42,500 | 27,000 | 52,000 | 38,500 |
| April 1983 | 32,390 | 20,740 | 50,460 | 41,210 | 59,500 | 49,240 |
| September 1985 | 31,920 | *[corrupt]* | 36,610 | 27,430 | 43,480 | 32,130 |
| June 2006 | n/a | *[corrupt]* | 65,900 | 41,200 | 68,600 | 48,900 |

\* WCM: "Regulated by F.E. Walter Reservoir only." Lehighton is a Walter-only station throughout (Table 7-1 Part B note 3). Two regulated-Lehighton cells contain date strings rather than discharges — see Provenance 3(r). **The June 1972 and January 1976 natural values conflict sharply with Table 4-6 — see Provenance 3(s); do not use Table 8-2's 1972 figures without resolving that conflict.**

Reduction ratios where both cells are clean: Walnutport 41–59% of natural peak removed; Bethlehem 26–35%; Lehighton 36% (1983). These are the headline system-performance numbers and the natural target for an emulation skill-score.

#### §2.5.7 Aggregate benefit record

$199,666,000 in damages prevented from completion (1961) through FY2012 at October 2012 price levels (§8-02f). Estimated average annual damages remaining, with Walter + Beltzville + the Allentown and Bethlehem local protection projects on line: **$685,700** (1992 price level; Table 4-10, Parts 1–2), of which Easton alone is $299,000. Table 8-2 (natural vs. regulated elevations and discharges for major historic events) resides in TAB-A and was not supplied.

---

## Layer 3 — Curated Policy Text

**P1 — Operating philosophy / project objective (WCM §7-01, §7-03, §7-05):** Flood control is the primary objective; recreation (in-lake and downstream whitewater) and fisheries enhancement are the secondary objectives. Walter is regulated **in conjunction with Beltzville** for optimum flood control benefit on the Lehigh, with all flood control storage at both projects committed to that end — "Method A" under EM 1110-2-3600 §3-02. During flood events "the first priority will always be to obtain maximum downstream flood control benefits." Under normal regulation the flood control system passes inflow while holding the target pool. The two reservoirs control only ~6% of the Easton–Trenton mainstem Delaware drainage, so Delaware-oriented benefit is negligible; Easton benefits only for *Lehigh-oriented* flooding, and evacuation releases must never add to Delaware-oriented stages there.

**P2 — Operator role and authority (WCM §5-08a, §7-04, §9-01a):** Water Control Personnel, Northern Area Office, issue all storage and release instructions. Dam operators execute, log every gate operation, and report daily. On loss of communications the head dam operator assumes regulation authority under Table 7-1 and Exhibit B on his own initiative — a *documented, bounded transfer of decision authority* that the DKP must be able to represent. Water Control is available 07:00–15:30 daily plus off-hours as needed; a 24-hour roster covers emergencies.

**P3 — System / joint operation (WCM §7-03, §7-05,a, Table 7-1 Part B, Plate 7-4):** Walter and Beltzville are regulated **as a system**. Walter is regulated for flow reduction from the damsite to Parryville; Beltzville for the lower Pohopoco and, jointly with Walter, for the Lehigh below Parryville. When both are storing, operations balance the *percent* of flood control storage utilized at each, evacuating faster from whichever is fuller. The Maximum Release Schedule is a **combined** total across both projects with travel time and intermediate-area flow embedded. Walter alone owns Lehighton; Walnutport and Bethlehem are shared; Pohopoco at Parryville is Beltzville's.

**P4 — Institutional chain (WCM §7-14, §9-02 to §9-05):** Deviations run through North Atlantic Division — prior approval for planned deviations, act-then-notify for emergencies and unplanned minor deviations. DRBC declares basin drought warnings and emergencies and monitors salinity intrusion; the Corps–DRBC MOA for 34,665 ac-ft of temporary drought storage between 1300.0 and 1392.0 (1370.0 winter) **has expired and has not been renewed**, so there is currently *no* water supply allocation at Walter and any future request would require a new contract plus reevaluation of available storage. PA Fish & Boat Commission set the 50 cfs minimum and co-develops the annual recreation plan with PA DCNR. The Delaware River Master (USGS, per the 1954 Supreme Court decree) supervises NYC-reservoir compensating releases. Weatherly Borough held a 3-year FERC preliminary permit (Dec 2013) to study hydropower at the site; power is not a project purpose.

**P5 — Empirical anchors (WCM §4-06b, §8-02, Tables 8-12/8-13; and the demoted PR-73):** June 2006 (pool 1,441.73, inflow 22,723 cfs, release ~9,610 cfs) is the flood of record since construction and occurred from an elevated recreation pool; Agnes 1972 and January 1976 are documented from the actual Monthly Water Control Charts. The regulated frequency curve pinned at 8.5 kcfs at White Haven from the 10- through 100-yr event (§2.5.5) is the numerical fingerprint of the channel-capacity rule. The 53-year annual series (§2.5.4) shows a project that in a typical year uses roughly a quarter of its flood storage, with a single dominant outlier at 87% (June 2006, from an elevated recreation pool), and whose maximum discharge of record — 11,452 cfs in January 1996 — exceeds the nominal 10,000 cfs channel capacity, confirming that the `R-ATSITE` exception is exercised. Table 8-2 (§2.5.6) quantifies the joint Walter + Beltzville effect across five events: 41–59% of the natural peak removed at Walnutport, 26–35% at Bethlehem. **HEC PR-73 (2010)** is retained here as an *evidentiary* comparator only: it is an independent expert's extraction of the 1994 WCM (with a 2003 water-quality revision and 1/22/09 CENAP correspondence), validated against April 2004, April 2005 and June 2006. Its divergences from the 2014 WCM — a discharge-domain rate limit, three fabricated control stages, superseded storage values — are catalogued in Provenance 3 and constitute the labeled-defect set for the RT1 extraction comparator.

**P6 — Recreation as subordinate storage (WCM §3-05,b,2, §7-01, §7-06, §8-03):** The whitewater program evolved from ad-hoc 1968 club releases through a 1971 state-negotiated 750 cfs cap, was suspended entirely during the 1980–82 drought, and was formalized by PL 100-676 §6 in 1988. The 2004 road across the dam crest removed the 1309.0 access-road constraint, permitting the pool to be raised progressively — 1335 (2005), 1365 (2006), 1370 (current). The governing justification is explicit and is what keeps recreation compatible with the primary purpose: this volume "can be quickly evacuated in advance of an oncoming storm event." Recreation storage is therefore always pre-releasable and never protected.

**P7 — Source scope boundary (WCM front matter; TAB-A):** This DKP is built from the redacted public edition, Chapters 1–9 plus Pertinent Data, together with the portion of **TAB-A** supplied at v1.2 — Tables 7-1 Parts A and B, 7-3, 8-1 and 8-2. The station rating tables (8-3 to 8-11), all Plates, Exhibits A–D, and the Emergency Action Plan are referenced throughout the manual but remain unsupplied. The manual itself notes it is maintained in loose-leaf form with dated page-level revisions, so partial-revision drift between sections is possible and section-level vintage cannot be assumed uniform.

---

## Layer 4 — Decision Templates

**T1 — Normal / routine operations (Schedule Plan A).**
Given: `schedule_plan == A`; `pool_elevation ≈ target_pool_ft`; all control stages below action stage.
Agent actions: pass inflow per `R-RELEASE` case A while holding `target_pool_ft` per `R-ZONE`; honor `R-MINNORM` (50 cfs) or `R-MINDROUGHT` (43 cfs) if `drbc_drought_declared`; move gates within `R-ROC`; compute inflow per `R-INFLOW`; observe `R-FISH` 5-ft fluctuation limit in May–June.

**T2 — Flood operations (Schedule Plans B and C).**
Given: `pool_elevation > target_pool_ft` and `< EL_SPILLWAY`.
Agent actions: select the plan via `R-PLAN` against the Table 7-1 Part A thresholds (Bethlehem 12.0 / Walnutport 7.0 / Lehighton 9.0), remembering that the Plan-A/B pool boundary is 1300.0 in winter and **1370.0 in summer**. Under C (any one gage at or above threshold), store all inflow at **both** projects and release only `R-MINFC` (100 cfs). Under B, read the **combined** allowable release from the Maximum Release Schedule (§2.4.5) at the most restrictive gage, then split it against `beltzville_state` via `R-BALANCE`, staging the two releases with the Time of Travel Schedule (§2.4.6). In both, cap by `R-ATSITE`, ramp gates within `R-ROC`, step at the `R-CADENCE` interval, maintain `R-TEMP`, and apply `R-FILLING` on any new maximum pool. Notify per `R-ALERT` above 2,000 cfs. Modify per `R-ICE` if `ice_jam_downstream`.

**T3 — Post-flood evacuation.**
Given: `stages_trend == falling_after_peak`; `pool_elevation > target_pool_ft`.
Agent actions: draw down per `R-RELEASE` on the falling-stage branch of §2.4.5. **Condition 1** (all stations peaked at or below flood stage): combined release must not exceed the *action* stage when routed downstream, and the per-reservoir 10,000 / 1,500 cfs channel limits still bind. **Condition 2** (any station peaked above flood stage): the bound is that event's maximum flood stage and the channel limits may be exceeded — this is the only route to the `R-ATSITE` exception. Schedule jointly with Beltzville via `R-BALANCE` using Table 7-1 travel times. Verify no addition to Delaware-oriented stages at Easton.

**T4 — Institutional-directive operations (deviations and drought).**
Given: a deviation request, or `drbc_drought_declared == true`.
Agent actions: classify the request under `R-DEVIATION` categories a/b/c and route accordingly — act-then-notify NAD for a and b, prior NAD approval for c. Under drought, relax the minimum to `Q_MIN_DROUGHT` (43 cfs) per `R-MINDROUGHT`; note there is **no** active water-supply storage contract, so no supply release may be committed without a new agreement. Recreation events during a DRBC drought warning are evaluated for cancellation by the Commission.

**T5 — Spillway-crest operations (Schedule Plan D).**
Given: `pool_elevation ≥ EL_SPILLWAY`.
Agent actions: ignore downstream stages entirely per `R-PLAN`. Determine inflow **hourly or more often** per `R-INFLOW`; open gates incrementally to full open attempting to hold the pool at or below the crest; once outlet capacity is exceeded, **hold gates full open** until the pool recedes below 1450.0. Then regulate **outflow equal to inflow** until the Plan B Maximum Release Schedule can be resumed, and deplete flood storage as quickly as it permits. Apply `R-FILLING` throughout high pool. Spillway discharge above the crest is uncontrolled (§2.4.3). If a second event raises downstream stages during drawdown, evaluate closing gates to recover whatever flood storage is then available.

**T6 — Emergency and degraded-authority operations.**
Given: `comms_available == false`, `gates_operable == false`, or `embankment_distress == true`.
Agent actions: apply `R-EMERGENCY`. On comms loss, the dam operator regulates from Table 7-1 and Exhibit B and computes inflow per `R-INFLOW`. On embankment distress, warn downstream, open service gates full, and treat `R-ROC` as **waived**; defer to the Emergency Action Plan.

**T7 — Water quality / temperature management.**
Given: `plan ∈ {A, B, C}`; releases being made through both the bypass and the outlet works.
Agent actions: blend surface withdrawal (1300.0–1297.0) with bottom release per `R-TEMP` toward a downstream target not exceeding 60–65 °F; hold the 50 cfs `R-MINNORM` floor set for brook trout habitat. Note that selective-withdrawal authority is lost once the pool rises well above the 3-ft bypass window.

**T8 — Seasonal recreation management.**
Given: `season ∈ {recreation_fill, recreation_release, drawdown}`.
Agent actions: fill toward 1370.0 from ~1 April targeting mid-May per `R-ZONE`, following Exhibit D for detailed summer regulation (**not supplied** — escalate rather than infer); make whitewater and fisheries-augmentation releases per `R-RECREATION` subject to hydrologic availability; pre-release recreation storage ahead of any forecast storm, since it is unprotected; return the pool to 1300.0 after mid-October. Notify PA DCNR of release changes affecting whitewater.

---

## Fallback Policy

1. **Life and dam safety first.** Embankment distress, unprecedented pool, or structural anomaly defers to the F.E. Walter Emergency Action Plan and the downstream warning obligation; `R-ROC` is expressly waivable for this. *(WCM §7-05,b,4; §7-13; §7-16)*
2. **Protect downstream control points and channel capacity.** Under any uncovered condition, do not cause White Haven 8.0, Lehighton 10.0, Walnutport 8.0, or Bethlehem 16.0 to be exceeded by release, and do not add to Delaware-oriented stages at Easton; when in doubt, **store**. *(WCM Table 7-2 and notes; §7-01)*
3. **Respect physical invariants.** Spillway flow above 1,450.0 is uncontrollable; outlet capacity bounds any release; gate travel is bounded by `R-ROC`. No decision may assert control authority the project does not have. *(WCM §2-03b; §7-02a; §7-05,c)*
4. **Institutional actions require institutional approval.** Deviations route through NAD per `R-DEVIATION`; there is **no** active water-supply storage contract, so no supply release may be committed. Absent an approved deviation the seasonal rule curve of `R-ZONE` governs. *(WCM §7-14; §9-03)*
5. **Escalate rather than improvise.** Uncovered conditions are referred to Water Control Personnel; on comms loss, revert to Table 7-1 and Exhibit B rather than to invention. Joint operation with Beltzville is the default assumption for any flood or evacuation decision touching Walnutport or Bethlehem. *(WCM §5-08a; §7-03; §7-04)*
6. **Recreation yields.** Any conflict between recreation storage and flood-control readiness resolves in favor of pre-release; recreation storage is never treated as protected. *(WCM §3-05,b,2(b); §8-03b)*
7. **Do not fabricate what TAB-A still withholds.** Release magnitudes are now covered (§2.4.5), but the **Initial Reservoir Filling Plan** (Exhibit C, invoked by `R-FILLING` on any new maximum pool), the **summer regulation detail** (Exhibit D, invoked by Schedule B in the recreation season), the **Standing Instructions to Dam Operators** (Exhibit B, governing comms-loss authority), and all **station stage–discharge ratings** (Tables 8-3 to 8-11) remain out of coverage. Declare and escalate; do not interpolate. *(coverage gap, Provenance 5)*
8. **Prefer Table 7-1 over Chapter 7 prose where they diverge.** The schedules are the operative instrument; the narrative paraphrases them and diverges in at least three places (Provenance 3(o), 3(p), 3(q)). *(Table 7-1 Parts A and B)*

---

## Provenance and Limitations

1. **Extraction basis:** *Water Control Manual (Revised), Francis E. Walter Dam and Reservoir, Lehigh River Basin, Pennsylvania*, USACE Philadelphia District, October 1961, rev. October 1994, **rev. September 2014**, redacted public edition — Pertinent Data and Chapters 1–9 (Tables 1-1, 3-1, 4-1 to 4-10, 5-1 to 5-3, 6-1 to 6-3, 7-2, 8-12, 8-13, 9-1). Plus **TAB-A Tables 7-1 Parts A and B, 7-3 (rev. 2014), 8-1 (WY1961–2013) and 8-2**, supplied separately from the chapter text. Manual expert extraction, August 7, 2026; v1.2 same day. Machine text via `pdftotext -layout`. Station rating tables, Plates and Exhibits remain absent.

2. **Currency:** governing revision **September 2014** replaces the 1994/2003 vintage that PR-73 extracted. This is the sharpest **rule-currency** case in the corpus: the substantive operating regime changed between vintages (recreation pool moved from discretionary deviation to normal rule curve; DRBC storage contract lapsed). Table 7-3 is stamped "revised 2014" and Table 8-1 ends at WY2013, both consistent with a September 2014 issue. Currency risk remaining: the manual is maintained in loose-leaf form with page-level dated revisions, so post-2014 partial revisions may exist; whitewater specifics point to Exhibit D "(2014)" and are reviewed annually, so the release *schedule* is the most volatile element.

3. **Known discrepancies:**
   (a) **Rate-of-change domain error in the evidentiary source.** PR-73 states a 500 cfs/hr discharge limit "based primarily on observed data (WCM p. 7-11)"; the 2014 WCM §7-05,c,6 prescribes only **gate-position** criteria (1.0 ft/10 min at openings ≤6 ft; 1.5 ft/10 min above). No discharge-rate rule exists. **Second independent instance** of the identical defect class logged at Beltzville (0.25–1.2 ft/10 min → 500 cfs/hr) — the pattern is systematic across PR-73's Lehigh-pair extractions.
   (b) **Fabricated control stages.** PR-73 / DKP v1.0 give Lehighton 9.7, Walnutport 6.3, Bethlehem 9.9 ft. None appears in Table 7-2, which prescribes flood stages 10.0 / 8.0 / 16.0 and action stages 9.5 / 7.0 / 12.0 across **five** stations plus a Delaware constraint. The 6.3 ft is traceable to §8-02,d,2 — an event-specific figure inside the August 1955 back-routing narrative, i.e. an *evidentiary* value promoted to *prescriptive* status. A distinct and more insidious defect class than (a).
   (c) **Storage and elevation values.** PR-73 App. B gives 1,793 ac-ft at 1300, 109,608 at 1450, 160,290 at 1474; the 2014 revised survey gives 1,993 / 109,878 / 159,814. All superseded by the WCM. Areas differ likewise (PR-73 80 ac at 1300 vs. WCM 100.5 ac).
   (d) **Outlet capacity at crest.** PR-73 §2.4.2 gives 18,300 cfs at 1450; WCM gives ≈17,000 cfs (§7-02a, §7-05,c,4), corroborated by the SPF routing maximum of 16,950 cfs.
   (e) **Gaged-inflow arithmetic.** §7-05d states Stoddartsville 91.7 + Blakeslee 118.0 = "207.7 square miles"; §8-10a gives 209.7 for the same pair. 209.7 is correct; 207.7 is an arithmetic error.
   (f) **Inflow gages transposed.** §6-02b states Stoddartsville gages 118 sq mi and Blakeslee 92 sq mi — reversed relative to Table 5-1, §4-07 and §7-05d (Stoddartsville 91.7; Blakeslee 118.0).
   (g) **Spillway/design discharge unreconciled.** Pertinent Data 193,721 cfs (total, conduit + spillway); §2-03b ≈170,000 cfs (spillway alone); §8-02b 184,000 cfs (SDF routing combined maximum at 1470.9). Not reconciled in the manual.
   (h) **Station number collision.** Table 4-4 assigns Pohopoco Creek at Kresgeville the number 01449000, which it also assigns to Lehigh River at Lehighton. Transcription error; Table 5-1 does not repeat it.
   (i) **Structural artifacts in §7-05,c.** The constraint list runs 1–6 and then restarts at "3." for the drawdown item (should be 7); the rate-of-change sub-items are lettered (d)/(e) rather than (a)/(b).
   (j) **Arithmetic in the §7-05d worked examples.** Example A computes 1,562 cfs then reports 1,550 cfs. Example B prints "= 942 cfs" where 1,400 − 908 = 492, then reports 490 cfs. Transcription artifacts; the equations themselves are correct.
   (k) **County list.** Pertinent Data gives Carbon, Monroe and Wayne; §2-01 and §4-01 give Carbon, Luzerne, Wayne and Monroe (Luzerne omitted from Pertinent Data).
   (l) **Drainage area reference points.** 288 sq mi above the dam (Pertinent Data, §4-01, used for SDF proration in §8-10a) vs. 290.0 sq mi at the White Haven outflow gage (Table 5-1, and the label used in Tables 8-12/8-13). Not a conflict — different points — but they must not be interchanged.
   (m) **Cross-DKP check pending.** §7-05 states Beltzville flood control storage as 27,664 ac-ft; verify against `DKP-BELTZVILLE-v1.2` §2.1, since `R-BALANCE` divides by it. Table 7-1 additionally supplies Beltzville's normal pool 628.0, crest 651.0, minimum releases 35/35/15 cfs and Parryville action stage 5.30 ft — all should be reconciled against that DKP.
   *(v1.2 additions, from TAB-A:)*
   (o) **Lehighton plan-boundary stage.** Table 7-1 **Part A** sets the Plan-B/Plan-C boundary at Lehighton **9.0 ft**; Table 7-2 gives an action stage of **9.5 ft**, and Table 7-1 **Part B**'s Maximum Release Schedule brackets 9.0–9.5 at 1,000 cfs with storage beginning only "above 9.5." Part A's 9.0 is the outlier and creates a 0.5-ft band in which Parts A and B disagree about whether the project should be storing. Bethlehem (12.0) and Walnutport (7.0) are consistent across all three.
   (p) **Parryville action stage.** Table 7-1 Part B note 4 gives 5.30 ft (1,500 cfs); WCM Table 7-2 gives 5.5 ft. Affects `R-BALANCE`'s Beltzville-side limit.
   (q) **Travel time.** The Time of Travel Schedule gives Walter→Lehighton low flow as 16 hr; Table 4-8 gives 15 hr. All other reaches agree.
   (r) **Table 8-2 cell corruption.** The regulated-Lehighton cells for September 1985 and June 2006 contain date strings ("3-Jul", "24-Oct") instead of discharges. The April 1983 regulated Lehighton value is printed "20, 740". Transcription artifacts, not substantive ambiguity.
   (s) **Table 8-2 vs Table 4-6 — major unresolved conflict.** For June 1972 Table 8-2 gives natural/regulated of 71,000/42,000 at Walnutport and 88,000/64,000 at Bethlehem. Table 4-6 gives, for the same event, *naturalized without Beltzville or Walter* 49,000 at Walnutport and 65,200 at Bethlehem, and *recorded* 39,000 and 57,900. The two tables differ by 20,000–23,000 cfs on the natural values. Most likely Table 8-2 reports HEC-5C system-model output rather than the observed/naturalized event, but the manual does not say so. **Do not mix the two tables.**
   (t) **Table 8-1 flood-storage denominator is off by one foot.** The footer states the allocation as **106,084 ac-ft**, and the printed % column uses it (WY2006: 91,830/106,084 = 86.6% → 87). But from Table 7-3, storage(1450) − storage(1300) = **107,885.66 ac-ft**, matching §7-05's 107,886. The printed figure equals storage(**1449**) − storage(1300) = 106,083.97 — the row immediately above the spillway crest. Every percentage in Table 8-1 is therefore inflated by ~1.7% relative to the governing allocation. This is the most precisely diagnosable defect in the corpus and an excellent labeled test case: it is internally consistent, plausible, and wrong.
   (u) **Table 8-1, WY2011 is internally inconsistent.** Reported pool 1414 with 28,832 ac-ft; from Table 7-3, 1414 corresponds to ~55,704 ac-ft of flood storage, while 28,832 ac-ft corresponds to El. ≈1385.3. The printed % (27) is consistent with the *storage* value, so the elevation is the erroneous field. Note also that the pool elevation is printed without decimals, unlike every other row.
   (v) **No Table 8-1 row recomputes exactly from Table 7-3.** Residuals run from −2,038 to +1,754 ac-ft (WY1985 is closest at −54). Expected: the series ends at WY2013 and the area-capacity table was revised in 2014, so *every* row was computed on a superseded table. Unlike Beltzville, there is no post-revision row available to validate the method against.

4. **Not extracted:** WCM TAB-A **Tables 8-3 to 8-11** (station stage–discharge ratings at Stoddartsville, Blakeslee, White Haven, Lehighton, Walnutport, Bethlehem, Glendon, Kresgeville, Parryville). Plates 7-1a, 7-1b, 7-2 (operational rule curve), 7-3 (gate ratings), 7-4 (percent-FC-storage balancing), 7-5 (spillway rating), 7-6 (drawdown curves), 7-7 (inflow nomograph), 6-1 to 6-7 (unit hydrographs), 8-1 to 8-13. Exhibits A (supplementary pertinent data), B (Standing Instructions to Dam Operators), C (Initial Reservoir Filling Plan), D (2014 Recreation Operations Plan). F.E. Walter Emergency Action Plan. DRBC Water Code (Walter's stated Drought Contingency Plan by reference, §6-05c, §7-12). Request path: **PDPA-NAP@usace.army.mil** (CENAP).

5. **Coverage gaps** *(substantially reduced at v1.2)*:
   - **Closed at v1.2:** release magnitude under all four Schedule Plans (§2.4.5); storage accounting and `R-INFLOW` at 1-ft resolution with the dsf column (§2.4.1); release staging between the two projects (§2.4.6); the annual maximum series and the system flood-reduction record (§2.5.4, §2.5.6).
   - **Exhibit C — Initial Reservoir Filling Plan.** `R-FILLING` is structurally present but has no criteria. It fires on any new maximum pool, i.e. precisely in the extrapolation regime where an agent is least reliable. Highest-value remaining request.
   - **Exhibit D — 2014 Recreation Operations Plan.** Schedule B explicitly defers summer regulation to it. Without it, `R-RECREATION` and T8 are qualitative.
   - **Exhibit B — Standing Instructions to Dam Operators.** The operative text for the comms-loss authority transfer in `R-EMERGENCY` / T6.
   - **Tables 8-3 to 8-11.** Stage→flow conversion at all control stations is unavailable, so `R-DOWNSTREAM` and the Maximum Release Schedule are enforceable only in the stage domain. Sparse anchors exist from Table 4-6 and Table 7-1 notes 4–5.
   - `outlet_capacity(pool_elevation)` and `spillway_discharge(pool_elevation)` remain anchor-points only (Plates 7-3, 7-5 absent).
   - `R-BALANCE`'s allocation curve remains qualitative (Plate 7-4 absent) — the *combined* total is now known, but the split between the two projects is stated as a priority principle, not a formula.
   - `R-TEMP`'s blend ratio is discretionary; no schedule is given even in Table 7-1.

6. **Role in experiments:** full-tier, **single-prescriptive-source gold standard** (third in the corpus, with Prompton and Beltzville). Three distinct experimental affordances. **(i) Rule-currency testbed complementing Rio:** where Rio's strata are contemporaneous and documented side-by-side, Walter's are *temporal* — an agent given the 1994-vintage PR-73 extraction will confidently operate a superseded regime, and the 2014 WCM supplies the ground truth for measuring that error. **(ii) RT1 labeled-defect comparator, now replicated and extended:** discrepancies 3(a) and 3(b) are two distinct extraction-failure classes — domain mistranslation and evidentiary-to-prescriptive promotion — and 3(a) recurring independently at Beltzville converts a single anecdote into a measurable systematic failure mode of expert flat-text extraction. v1.2 adds a third class in 3(t): a *source-internal* arithmetic defect that is self-consistent, plausible, and wrong by exactly one table row — the cleanest available test of whether a pipeline validates derived quantities against their own base table rather than trusting a printed footer. 3(o)–3(q) add a fourth: **instrument-vs-narrative divergence**, where the operative schedule and the chapter prose that paraphrases it disagree, and the extractor must know which governs. **(iii) Joint-constraint pair:** with Beltzville, Walter forms the corpus's only two-reservoir coupled system, where neither project's flood release is computable from its own state alone — Table 7-1 Part B now makes that coupling explicit and numeric, giving a *single* combined cfs value that the two projects must partition; the regulated-frequency flattening at 8.5 kcfs (§2.5.5) gives an independent numerical check on whether an agent has internalized the channel-capacity rule. Supports H1 (extraction fidelity), H2 (information sufficiency), and H4/H7 (rule-following under institutional structure). As of v1.2 this is the **most executable DKP in the corpus** — the only one where plan selection, release magnitude, storage accounting and inter-project allocation are all closed against a single prescriptive source.

*DKP-FEWALTER-v1.2 — prepared August 7, 2026 for the CDS&E LLM-reservoir demonstration (full tier; single-prescriptive-source gold standard; rule-currency and coupled-system exemplar).*
