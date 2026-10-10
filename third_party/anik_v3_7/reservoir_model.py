"""Daily or monthly reservoir operation model - the MAIN PROGRAM.

WHAT THIS FILE DOES
===================
Simulates reservoir operation: it reads daily inflow, optionally aggregates
it to monthly means, asks a RELEASE POLICY how much to release each step,
applies the physical water balance over the actual step duration,
and writes results + evaluation against the observed releases.

    inflow data          release policy (pick one with --method)
    (daily CSVs)         +---------------------------------------------+
        |                | benchmark : published equations             |
        |                |             (benchmark_release.py)          |
        v                | zeroshot  : LLM + basic facts only          |
    +-----------+        |             (zeroshot_llm_release.py)       |
    | WATER     | <----- | dkp       : LLM + retrieved DKP knowledge   |
    | BALANCE   |        |             (dkp_llm_release.py)            |
    | (daily)   |        +---------------------------------------------+
    +-----------+
        |
        v
    results/*.csv  +  skill scores (NSE, PBIAS) vs. observed releases

THE DAILY LOOP (the heart of the model, in simulate())
======================================================
For each daily or monthly step t:
    0. CONSULT? for LLM methods only, decide whether today warrants a new
       LLM consultation or whether the prior release decision still stands
       (see INFLOW_CHANGE_THRESHOLD below - this check lives HERE, in the
       driver, not inside the policy classes)
    1. POLICY   the release rule proposes a release decision R_t
    2. PHYSICS  constraints are enforced (dead storage, water availability)
    3. BALANCE  storage updates: S_t = S_{t-1} + (I_t - R_t) * dt
    4. SPILL    storage above capacity spills (added to the release)

WHY THE LLM-CONSULTATION CHECK IS IN THIS FILE
===============================================
It used to live inside ZeroShotLLMPolicy as a _can_reuse() method plus an
inflow_change_threshold field, which DKPLLMPolicy inherited. Two problems:
the behavior of a DKP run was invisible when reading dkp_llm_release.py,
and the two LLM conditions had separate (silently divergent) copies of a
setting that must be identical for the comparison to be controlled.

It is also not reservoir decision knowledge - it is a run-control/cost
decision about how often the simulation pays for an LLM call. So it lives
here, as ONE module-level constant applied identically to both LLM
methods. If it ever becomes a deliberate experimental factor (e.g. a
different sensitivity per method), that must be an explicit, approved
change here - not a per-policy default that drifts.

All policies expose the same interface, so they are plug-in
interchangeable and any performance difference between methods is
attributable to the decision knowledge, not the plumbing:

    policy.target_release(date, inflow_cms, storage_start_m3,
                          runtime_state=...) -> m^3/s
    policy.record_outcome(...)   # optional; gives LLM policies their prior
                                 # simulated decision plus the resulting state
    policy.record_reuse(...)     # optional; LLM policies only, so days
                                 # without a consultation still get logged
    policy.uses_llm              # optional flag; True -> apply the
                                 # consultation criterion below

UNITS
=====
Input CSVs are in cfs (US units, as published by USGS). Internally the
model works in SI (m^3 and m^3/s). Outputs report cfs and acre-feet.

HOW TO RUN
==========
    python reservoir_model.py [--method benchmark|zeroshot|dkp]
                              [--llm gemma4] [--reservoir NAME]
                              [--timestep daily|monthly] [--steps N]

    --method     release rule to use (default: benchmark)
    --llm        decision engine for the LLM methods (default: gemma4)
                   gemma4  - gemma4:12b via a local Ollama server (current)
                   sonnet5 - Claude Sonnet 5 via the Anthropic API
                             (registered but not currently used - needs
                             ANTHROPIC_API_KEY if selected)
    --reservoir  run only this reservoir by name (default: all active
                 reservoirs in RESERVOIRS). Example:
                 --reservoir "F.E. Walter Dam"
    --timestep   decision and water-balance interval (default: daily)
    --steps      simulate only the first N daily/monthly steps
"""

import argparse
from datetime import datetime
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark_release import BenchmarkPolicy, HydropowerSDP, SECONDS_PER_DAY

# --- folder layout (everything is relative to this file) --------------------
BASE_DIR = Path(__file__).parent                    # the project folder
DAILY_DIR = BASE_DIR / "data" / "dailystreamflow"   # daily flow CSVs (model input)
RESULTS_DIR = BASE_DIR / "results"                  # simulation outputs

# --- unit-conversion constants ----------------------------------------------
CFS_TO_CMS = 0.028316847      # cubic feet per second -> cubic meters per second
ACREFT_TO_M3 = 1233.4818      # acre-feet -> cubic meters
CF_PER_ACREFT = 43_560.0      # cubic feet per acre-foot (exact)
M3_PER_CF = CFS_TO_CMS        # 1 ft^3 = 0.028316847 m^3 (same factor as cfs->cms)

# F.E. Walter WCM Table 7-3 (revised 2014), storage at whole-foot
# elevations 1247 through 1474 ft NGVD29. This is the curve supplied in
# Wenyu's storage_to_elevation.py. The model interpolates between adjacent
# rows, so the conversion stays in the shared physics code and is never an
# LLM task or prompt input table.
FE_WALTER_STORAGE_BY_ELEVATION_AF = (
    0.00, 0.00, 0.01, 0.04, 0.10, 0.19, 0.32, 0.66,
    1.50, 3.03, 5.30, 8.38, 12.20, 16.61, 21.64, 27.45,
    34.18, 42.11, 51.95, 64.30, 79.37, 97.05, 117.38, 140.37,
    165.69, 193.16, 222.60, 254.01, 287.42, 322.94, 361.11, 402.37,
    447.26, 495.99, 548.41, 603.59, 661.11, 720.83, 782.56, 846.11,
    911.60, 979.39, 1049.76, 1122.84, 1198.27, 1275.95, 1356.02, 1438.89,
    1524.41, 1612.64, 1703.59, 1797.20, 1893.48, 1992.61, 2094.46, 2199.25,
    2306.99, 2417.99, 2532.08, 2648.94, 2768.72, 2891.83, 3018.58, 3148.43,
    3281.12, 3416.77, 3555.60, 3697.62, 3842.68, 3991.02, 4143.28, 4299.25,
    4458.43, 4620.88, 4786.79, 4956.54, 5130.32, 5308.40, 5491.28, 5679.85,
    5873.63, 6072.04, 6274.91, 6482.73, 6695.66, 6914.26, 7138.83, 7369.79,
    7607.65, 7852.13, 8103.51, 8361.75, 8626.48, 8898.44, 9178.00, 9464.82,
    9759.05, 10060.78, 10370.02, 10687.63, 11013.69, 11347.91, 11689.92, 12039.87,
    12397.75, 12763.12, 13135.13, 13514.05, 13899.81, 14292.87, 14694.24, 15104.32,
    15522.66, 15949.30, 16384.60, 16828.66, 17281.93, 17744.14, 18214.74, 18693.69,
    19180.97, 19676.85, 20181.80, 20696.47, 21221.30, 21761.87, 22339.82, 22948.00,
    23575.93, 24218.86, 24875.11, 25544.46, 26226.48, 26921.10, 27628.56, 28348.13,
    29079.64, 29822.44, 30577.62, 31345.10, 32123.65, 32913.48, 33715.53, 34529.86,
    35356.01, 36194.09, 37044.10, 37907.01, 38783.08, 39671.38, 40571.66, 41483.74,
    42407.40, 43342.31, 44288.47, 45246.15, 46215.54, 47196.63, 48189.21, 49193.50,
    50209.47, 51237.28, 52278.62, 53334.09, 54403.33, 55486.81, 56584.62, 57696.87,
    58823.72, 59965.41, 61122.02, 62294.14, 63482.01, 64686.35, 65908.44, 67149.47,
    68410.02, 69688.46, 70984.15, 72296.70, 73626.37, 74973.79, 76339.66, 77725.04,
    79130.40, 80554.80, 81998.51, 83464.87, 84953.31, 86468.39, 88010.95, 89574.11,
    91156.45, 92757.80, 94378.69, 96019.42, 97680.38, 99362.19, 101065.15, 102788.42,
    104531.48, 106294.34, 108076.58, 109878.27, 111699.82, 113541.21,
    115402.45, 117283.46, 119184.11, 121104.23, 123044.03, 125004.69,
    126988.81, 128996.57, 131027.72, 133081.77, 135158.57, 137258.72,
    139382.91, 141532.53, 143707.78, 145908.94, 148138.56, 150399.17,
    152693.01, 155022.79, 157392.55, 159814.09,
)
FE_WALTER_ELEVATION_STORAGE_CURVE = tuple(
    (1247.0 + index, storage)
    for index, storage in enumerate(FE_WALTER_STORAGE_BY_ELEVATION_AF)
)

# Shared operating target specified by Prof. Yang for BOTH LLM conditions.
# Adjacent dates at each boundary make this a calendar step rather than an
# interpolated April/October ramp: 1300 ft November-April and 1370 ft May-October.
FE_WALTER_SEASONAL_TARGET_CURVE = (
    ("01-01", 1300.0),
    ("04-30", 1300.0),
    ("05-01", 1370.0),
    ("10-31", 1370.0),
    ("11-01", 1300.0),
    ("12-31", 1300.0),
)

# --- LLM-consultation criterion (applies to BOTH LLM methods) ---------------
# On a day when today's inflow differs from yesterday's by no more than this
# fraction, the simulation reuses the prior release decision instead of paying
# for another LLM call. This is run/cost control, NOT reservoir decision
# knowledge, and it is deliberately ONE constant shared by the zeroshot and
# dkp methods so the two conditions cannot drift apart on it. Changing it
# changes both methods at once, by design.
INFLOW_CHANGE_THRESHOLD = 0.10


# ===========================================================================
# SECTION 1 - CONFIGURATION (everything reservoir-specific lives here)
# ===========================================================================

@dataclass
class ReservoirConfig:
    """Everything the model needs to know about ONE reservoir."""

    # --- identity and input data --------------------------------------
    name: str                          # display name, also used in filenames
    inflow_csv: str                    # daily inflow CSV in daily/ (from
    #                                    convert_15min_to_daily.py)
    # --- physical characteristics (from the water control manual) ------
    capacity_af: float                 # total storage capacity C (acre-feet)
    initial_storage_af: float          # storage on the first simulation day
    purpose: str                       # 'flood_control', 'irrigation',
    #                                    'hydropower', or 'other'
    dead_storage_af: float = 0.0       # pool below which nothing can be released
    alpha: float = 0.85                # capacity reduction factor
    #                                    (benchmark method; Abeshu et al. 2023)
    observed_release_csv: str = None   # observed release CSV - EVALUATION ONLY,
    #                                    never shown to any policy
    # --- basic information for BOTH LLM methods ------------------------
    river: str = ""                    # river and location
    max_release_cfs: float = 10_000.0  # outlet / non-damaging release capacity
    min_release_cfs: float = 0.0       # minimum (environmental) release
    normal_pool_af: float = None       # typical non-flood pool (also the
    #                                    fallback/annual-average value when
    #                                    monthly_target_af is set below)
    monthly_target_af: dict = None     # {1..12: acre-feet} first-of-month
    #                                    target storage, for reservoirs run
    #                                    against a seasonal elevation-target
    #                                    schedule instead of one steady pool
    #                                    (e.g. Wallenpaupack) - None for
    #                                    every other reservoir in RESERVOIRS
    elevation_storage_curve: tuple = None  # ((elevation_ft, storage_af), ...)
    seasonal_target_curve: tuple = None    # (("MM-DD", elevation_ft), ...)
    # --- zero-shot knowledge tier (public, Wikipedia-level facts) -----
    # Zero-shot is defined as the knowledge anyone could obtain from the
    # reservoir's public Wikipedia page. Operating constants taken from the
    # Water Control Manual (release limits, crest-level capacity) belong to
    # the DKP tier and must NOT appear here. Leave empty to fall back to
    # the legacy zero-shot facts for reservoirs not yet profiled.
    public_profile: tuple = ()             # one fact per string
    public_capacity_af: float = None       # capacity as publicly reported
    # key in the `reservoir` column of a multi-reservoir inflow file
    # (e.g. daily_simulated_reservoir_inflow_1991_2025.csv)
    inflow_reservoir_key: str = None
    operation_target_description: str = ""  # identical baseline prompt text
    #                                         supplied to both LLM conditions
    flood_pool_bottom_ft: float = None     # 0% flood-control storage elevation
    flood_pool_top_ft: float = None        # 100% flood-control storage elevation
    operation_scope: str = ""              # explicit reduced/full-model scope
    runtime_missing_inputs: tuple = ()     # observations not supplied to policy
    inflow_scale: float = 1.0          # drainage-area ratio correction when the
    #                                    inflow gauge sits upstream of the dam
    # --- knowledge file for the DKP_LLM method -------------------------
    dkp_path: str = None               # the reservoir's DKP markdown file
    # --- research-validity gate ----------------------------------------
    config_confirmed: bool = True      # False when ANY value above is still a
    #                                    placeholder, an observed stand-in, or
    #                                    otherwise not traceable to a source
    #                                    document. The None-check in main()
    #                                    cannot catch these, because a
    #                                    placeholder is a number like any
    #                                    other - see --run-mode final.
    config_notes: str = ""             # what specifically is unconfirmed, shown
    #                                    whenever this reservoir is run or skipped


# All four project reservoirs, in one script. Prompton and Beltzville are
# not being actively run right now - use --reservoir to select just one
# (e.g. --reservoir "F.E. Walter Dam"), or omit --reservoir to run all
# reservoirs that have complete data (Wallenpaupack is automatically
# skipped until its TODOs below are resolved - see the safety check in main()).
RESERVOIRS = [
    ReservoirConfig(
        name="Prompton Reservoir",
        inflow_reservoir_key="prompton",
        inflow_csv="USGS-01428750-Prompton Reservoir-Inflow_daily.csv",
        capacity_af=54_673.0,          # spillway crest, el. 1205 ft (WCM Table 7-2)
        initial_storage_af=3_543.0,    # recreation pool, el. 1125 ft
        dead_storage_af=1_786.0,       # ~zero-release pool, el. 1122.8 ft
        purpose="flood_control",
        observed_release_csv="USGS-01429000-Prompton Reservoir-Release_daily.csv",
        river="West Branch Lackawaxen River, Pennsylvania",
        max_release_cfs=3_000.0,       # non-damaging channel capacity below dam
        min_release_cfs=5.0,           # low-flow releases via 48-in pipe
        normal_pool_af=3_543.0,
        dkp_path="data/DKP_Prompton_Reservoir_v1_1.md",  # updated: Prof. Yang's
        #                                multi-authority extraction, supersedes v2.0 -
        #                                see the DKP file itself for the critical
        #                                no-gates reframing note
    ),
    ReservoirConfig(
        name="F.E. Walter Dam",
        inflow_reservoir_key="fe_walter",
        inflow_csv="fe_walter_simulated_reservoir_inflow_daily.csv",
        capacity_af=109_878.27,        # spillway crest, El. 1450; WCM Table 7-3
        initial_storage_af=1_992.61,   # conservation pool, El. 1300; Table 7-3
        dead_storage_af=0.04,          # inactive pool, El. 1250; Table 7-3
        purpose="flood_control",
        # USGS 01447800, Lehigh R. below F.E. Walter Dam near White Haven -
        # the outflow gage at which the WCM minimum releases are measured.
        # 1996-01-01 to 2025-12-31, complete. EVALUATION ONLY: read after the
        # simulation finishes; never passed to any policy or prompt.
        observed_release_csv="USGS-01447800-F.E. Walter Dam-Release_daily.csv",
        river="Lehigh River, Pennsylvania",
        max_release_cfs=10_000.0,      # maximum allowed release (Q_ATSITE_MAX)
        min_release_cfs=50.0,          # water-quality minimum (Q_MIN_WQ)
        normal_pool_af=1_992.61,
        elevation_storage_curve=FE_WALTER_ELEVATION_STORAGE_CURVE,
        seasonal_target_curve=FE_WALTER_SEASONAL_TARGET_CURVE,
        # Source: Wikipedia, "Francis E. Walter Dam" infobox (accessed
        # September 2026). The public capacity (110,700 ac-ft) differs from
        # the WCM Table 7-3 value at spillway crest (109,878 ac-ft);
        # zero-shot deliberately receives the PUBLIC figure.
        public_profile=(
            "Location: Bear Creek Township, Luzerne County and Kidder Township, "
            "Carbon County, Pennsylvania",
            "Purpose: flood control, water storage, recreation",
            "Opened: 1961; operated by the U.S. Army Corps of Engineers",
            "Type: earth-fill embankment with rock shell, impounding the Lehigh River",
            "Dam height (foundation): 234 ft; length: 3,000 ft",
            "Spillway type: concrete",
            "Catchment area: 289 square miles",
        ),
        public_capacity_af=110_700.0,
        operation_target_description=(
            "Your goal is to keep the water level at or near the designated "
            "normal pool elevation: 1300.0 ft N.G.V.D. in the winter "
            "(November through April) and 1370.0 ft N.G.V.D. in the summer "
            "(May through October)."
        ),
        flood_pool_bottom_ft=1300.0,
        flood_pool_top_ft=1450.0,
        operation_scope="single-reservoir F.E. Walter simulation",
        runtime_missing_inputs=(
            "downstream stages and trends",
            "active drought declaration",
            "approved annual recreation plan",
            "ice, gate-outage, and emergency status",
        ),
        dkp_path="data/DKP_FEWalter_Dam_v1.2.md",   # v1.2 (Prof. Yang's approved version; R-PLAN gauge lines removed 2026-10-07)
    ),
    ReservoirConfig(
        name="Beltzville Lake",
        inflow_reservoir_key="beltzville",
        inflow_csv="USGS-01449360-Beltzville Lake-Inflow_daily.csv",
        capacity_af=70_127,            # spillway crest El. 651 ft = 86.5 M m3 (WCM)
        initial_storage_af=42_758,     # Jan 2015 pool = 52.74 M m3 (USACE CDA)
        purpose="other",               # water supply; no demand series, so the
        #                                Abeshu flood/other rule (Eq. 4) applies
        dead_storage_af=1_516,         # inactive/sediment pool El. 537 ft = 1.87 M m3
        observed_release_csv="USGS-01449800-Beltzville Lake-Release_daily.csv",
        river="Pohopoco Creek, Lehigh River basin, PA",
        max_release_cfs=10_000.0,      # placeholder outlet capacity - refine from WCM
        min_release_cfs=35.0,          # PR-73 "Min_35" minimum release, confirmed in real WCM
        normal_pool_af=42_758,         # NOTE: currently the Jan 2015 OBSERVED pool
        #                                (USACE CDA), not a documented target level.
        #                                _make_query() in dkp_llm_release.py uses this
        #                                as its above/below reference, so it should be
        #                                replaced with the WCM's documented normal
        #                                pool when that value is confirmed.
        dkp_path="data/DKP_Beltzville_Lake_v1_2.md",  # updated: Prof. Yang's
        #                                multi-authority extraction, supersedes our own
        #                                v2.1 fix - verified its T1 template (Schedule
        #                                Plan A, pool < 628.0) correctly instructs
        #                                "hold pool at EL_NORMAL... release >= Q_MIN"
        #                                rather than defaulting to the floor, so it
        #                                should not reintroduce the drought
        #                                floor-anchoring pathology v2.1 fixed
        inflow_scale=1.93,             # DA ratio 96.3/49.9 mi2, CONFIRMED against real WCM gauge table
        config_confirmed=False,
        config_notes=("max_release_cfs is a placeholder outlet capacity (refine "
                      "from the WCM); normal_pool_af is the Jan 2015 OBSERVED "
                      "pool from USACE CDA, not a documented target level - and "
                      "DKP retrieval now uses it as the above/below reference"),
    ),
    # --- Wallenpaupack: numeric config now filled from DKP_Wallenpaupack_v1.1's
    # §2.4.1 elevation-storage-area curve (PR-73 App. B, p. B-11) and Table 4.19
    # constants. STILL INCOMPLETE on the data-file side (inflow_csv /
    # observed_release_csv are real placeholders, not yet backed by actual
    # gauge data - see the project's gauge investigation notes) - main() will
    # still fail at load_daily_flow() until those exist. That's expected and
    # intentional; the safety guard below only checks the five numeric fields,
    # which is why this reservoir now clears that check but still can't
    # complete a run end-to-end.
    ReservoirConfig(
        name="Lake Wallenpaupack",
        inflow_reservoir_key="wallenpaupack",
        inflow_csv="USGS-01432000-Wallenpaupack-Inflow_daily.csv",  # STAND-IN,
        #                                not real 2015-2016 data: WY2005 outflow
        #                                (station 01432000, discontinued after
        #                                2005-09-29) relabeled onto the WY2016
        #                                calendar per Prof. Yang's interim plan -
        #                                see the file's "flag" column and the
        #                                May-Sep 2005 zero-flow clustering tied to
        #                                the documented Apr 2005 flood aftermath
        #                                (DKP §2.5). Supersede once Prof. Yang's
        #                                generated inflow is ready.
        capacity_af=269_584.0,         # el. 1,200 ft (EL_TOP_OF_DAM), DKP §2.4.1 curve
        initial_storage_af=148_210.0,  # Oct 1 "Normal" target, 1,179.0 ft, interpolated
        #                                on DKP §2.4.1 curve between 1,178 ft (142,839 af)
        #                                and 1,180 ft (153,580 af) - matches every other
        #                                reservoir's Oct 1, 2015 simulation start date
        purpose="hydropower",
        dead_storage_af=52_000.0,      # EL_INACTIVE, el. 1,160 ft - direct DKP §2.4.1
        #                                table value (PR-73 Table 4.19 / App. B)
        observed_release_csv=None,     # deliberately None, not TODO: no clean
        #                                observed-release gauge exists (Rowland/01432110
        #                                includes ~361 sq mi of extra drainage beyond
        #                                Wallenpaupack's own 228 sq mi) - evaluate() will
        #                                report "no observed release provided" instead of
        #                                an NSE/PBIAS score, which is expected and fine
        river="Wallenpaupack Creek / Lackawaxen River, PA",
        max_release_cfs=8_000.0,       # Q_CHANNEL_WALLENPAUPACK_CK - combined spillway
        #                                + powerhouse channel-capacity ceiling (DKP §2.1)
        min_release_cfs=0.0,           # documented, not guessed: DKP Fallback Policy #3 -
        #                                the bypassed reach is "dry by design (1-5 cfs
        #                                leakage; the license deliberately includes no
        #                                continuous bypass flow)" - there is no minimum
        #                                release floor for this reservoir
        normal_pool_af=167_600.0,      # annual mean of the 12 monthly targets below -
        #                                fallback value only (zero-shot's static prompt
        #                                line, and the main() safety-guard check); the
        #                                DKP method uses monthly_target_af instead, below
        monthly_target_af={            # first-of-month "Normal" column, DKP Water Code
            #                            Table 2, each elevation run through the §2.4.1
            #                            elevation-storage curve (linear interpolation
            #                            between the nearest two 2-ft table rows)
            1: 170_152.0,   # Jan 1, 1183.0 ft
            2: 161_866.0,   # Feb 1, 1181.5 ft
            3: 153_580.0,   # Mar 1, 1180.0 ft (exact table row)
            4: 166_285.0,   # Apr 1, 1182.3 ft
            5: 184_514.0,   # May 1, 1185.6 ft
            6: 192_402.0,   # Jun 1, 1187.0 ft
            7: 181_200.0,   # Jul 1, 1185.0 ft
            8: 170_152.0,   # Aug 1, 1183.0 ft (*subject to Article 302 dam-safety gate)
            9: 159_104.0,   # Sep 1, 1181.0 ft
            10: 148_210.0,  # Oct 1, 1179.0 ft
            11: 159_104.0,  # Nov 1, 1181.0 ft
            12: 164_628.0,  # Dec 1, 1182.0 ft (exact table row)
        },
        dkp_path="data/DKP_Wallenpaupack_v1.1.md",  # updated: Prof. Yang's
        #                                multi-authority extraction (FERC license +
        #                                DRBC Water Code + PR-73), supersedes v2.0
        inflow_scale=1.0,              # TODO: still unconfirmed - drainage area (228
        #                                sq mi, cross-validated via USGS station
        #                                metadata) is known, but the scaling gauge
        #                                itself hasn't been chosen/finalized yet
        config_confirmed=False,
        config_notes=("inflow_csv is WY2005 outflow relabeled onto the WY2016 "
                      "calendar, not real inflow data; inflow_scale is not yet "
                      "confirmed"),
    ),
]

# LLM decision engines for the zeroshot/dkp methods:
#   CLI name -> (module, backend class, constructor arguments)
LLM_BACKENDS = {
    "sonnet5": ("zeroshot_llm_release", "AnthropicBackend",
                {"model": "claude-sonnet-5"}),
    "gemma4": ("zeroshot_llm_release", "OllamaBackend",
               {"model": "gemma4:12b"}),
}


# ===========================================================================
# SECTION 2 - INPUT
# ===========================================================================

def load_daily_flow(csv_name: str, reservoir_key: str = None) -> pd.Series:
    """Load daily flow in cfs and return it in m³/s.

    `csv_name` may be a bare filename (looked up in data/dailystreamflow) or a
    path. A multi-reservoir file - one with a `reservoir` column, such as
    daily_simulated_reservoir_inflow_1991_2025.csv - is filtered to
    `reservoir_key`; without that filter its four reservoirs would share dates.
    """
    path = Path(csv_name)
    if not path.is_absolute() and not path.exists():
        path = DAILY_DIR / csv_name
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    if "reservoir" in df.columns:
        if not reservoir_key:
            raise ValueError(f"{path.name}: multi-reservoir file but no "
                             f"inflow_reservoir_key configured for this reservoir")
        available = sorted(df["reservoir"].unique())
        df = df[df["reservoir"] == reservoir_key]
        if df.empty:
            raise ValueError(f"{path.name}: reservoir '{reservoir_key}' not found; "
                             f"available: {available}")

    possible_columns = [
        "flow_cfs_daily_mean",  # processed USGS release data
        "simulated_inflow_cfs",  # simulated F.E. Walter inflow
        "simulated_reservoir_inflow_cfs",
    ]

    matches = [column for column in possible_columns if column in df.columns]

    if len(matches) != 1:
        raise ValueError(
            f"{path.name}: expected one supported flow column; found {matches}"
        )

    flow = pd.to_numeric(df[matches[0]], errors="raise").sort_index()

    if flow.index.has_duplicates:
        raise ValueError(f"{path.name}: duplicate dates found")
    if flow.isna().any():
        raise ValueError(f"{path.name}: missing flow values found")
    if (flow < 0).any():
        raise ValueError(f"{path.name}: negative flow values found")

    return flow * CFS_TO_CMS


def aggregate_flow(flow_daily: pd.Series, timestep: str) -> pd.Series:
    """Return daily flow unchanged or complete-calendar-month mean flow.

    Monthly operation uses mean discharge, not a monthly sum. Incomplete
    boundary months are dropped so the water balance never applies a partial
    month's mean over a full calendar month.
    """
    if timestep == "daily":
        return flow_daily.sort_index()
    if timestep != "monthly":
        raise ValueError(f"unsupported timestep: {timestep!r}")

    flow_daily = flow_daily.sort_index()
    monthly_mean = flow_daily.resample("MS").mean()
    observed_days = flow_daily.resample("MS").count()
    expected_days = pd.Series(
        monthly_mean.index.days_in_month,
        index=monthly_mean.index,
        dtype=int,
    )
    complete = observed_days.eq(expected_days)
    return monthly_mean[complete].dropna()


def elevation_to_storage_af(cfg: ReservoirConfig, elevation_ft: float) -> float:
    """Linearly interpolate storage from a documented elevation-storage curve."""
    if not cfg.elevation_storage_curve:
        raise ValueError(f"{cfg.name} has no elevation-storage curve")
    elevations = np.asarray([row[0] for row in cfg.elevation_storage_curve], dtype=float)
    storages = np.asarray([row[1] for row in cfg.elevation_storage_curve], dtype=float)
    return float(np.interp(elevation_ft, elevations, storages))


def storage_to_elevation_ft(cfg: ReservoirConfig,
                            storage_af: float) -> float | None:
    """Convert storage to elevation using Wenyu's table interpolation.

    Values between documented rows are linearly interpolated. Values outside
    the rating-curve range return ``None`` rather than being extrapolated.
    """
    if not cfg.elevation_storage_curve:
        raise ValueError(f"{cfg.name} has no elevation-storage curve")
    elevations = np.asarray([row[0] for row in cfg.elevation_storage_curve], dtype=float)
    storages = np.asarray([row[1] for row in cfg.elevation_storage_curve], dtype=float)
    value = float(storage_af)
    if not np.isfinite(value):
        raise ValueError("Storage must be a finite number of acre-feet")
    if value < storages[0] or value > storages[-1]:
        return None

    upper = 0
    while storages[upper] < value:
        upper += 1
    if storages[upper] == value:
        return float(elevations[upper])
    lower = upper - 1
    fraction = (value - storages[lower]) / (storages[upper] - storages[lower])
    return float(elevations[lower] + fraction)


def _daily_seasonal_target_ft(cfg: ReservoirConfig, date: pd.Timestamp) -> float:
    """Interpolate the documented seasonal target at one calendar date."""
    if not cfg.seasonal_target_curve:
        return None
    points = []
    for month_day, elevation in cfg.seasonal_target_curve:
        month, day = (int(part) for part in month_day.split("-"))
        points.append((pd.Timestamp(year=date.year, month=month, day=day), elevation))
    points.sort(key=lambda item: item[0])
    dates = np.asarray([point[0].dayofyear for point in points], dtype=float)
    elevations = np.asarray([point[1] for point in points], dtype=float)
    return float(np.interp(date.dayofyear, dates, elevations))


def seasonal_target_elevation_ft(cfg: ReservoirConfig, date: pd.Timestamp,
                                 timestep: str) -> float:
    """Return the target at the END of the decision interval.

    A monthly release changes storage across the entire month, so the
    operational endpoint is the last day's target.  The monthly mean target
    is still calculated separately in ``build_runtime_state`` for reporting.
    """
    if not cfg.seasonal_target_curve:
        return None
    if timestep == "daily":
        return _daily_seasonal_target_ft(cfg, date)
    if timestep != "monthly":
        raise ValueError(f"unsupported timestep: {timestep!r}")
    end_date = date.normalize() + pd.offsets.MonthEnd(0)
    return _daily_seasonal_target_ft(cfg, end_date)


def build_runtime_state(cfg: ReservoirConfig, date: pd.Timestamp,
                        storage_af: float, timestep: str) -> dict:
    """Build deterministic physical state supplied to LLM policies.

    Raw pool and target elevations are supplied separately. Deliberately no
    ``above_target``/``below_target`` label is produced; comparing the two
    values remains part of the LLM decision task.
    """
    state = {"timestep": timestep}
    if not cfg.elevation_storage_curve:
        return state

    pool_elevation = storage_to_elevation_ft(cfg, storage_af)
    state["pool_elevation_ft"] = pool_elevation
    target_elevation = seasonal_target_elevation_ft(cfg, date, timestep)
    if target_elevation is not None:
        start_target = _daily_seasonal_target_ft(cfg, date)
        if timestep == "monthly":
            days = pd.date_range(date.normalize(), periods=date.days_in_month,
                                 freq="D")
            mean_target = float(np.mean([
                _daily_seasonal_target_ft(cfg, day) for day in days
            ]))
        else:
            mean_target = target_elevation
        state["seasonal_target_start_ft"] = start_target
        state["seasonal_target_mean_ft"] = mean_target
        state["seasonal_target_ft"] = target_elevation
        state["seasonal_target_storage_af"] = elevation_to_storage_af(
            cfg, target_elevation
        )

    if cfg.flood_pool_bottom_ft is not None and cfg.flood_pool_top_ft is not None:
        bottom = elevation_to_storage_af(cfg, cfg.flood_pool_bottom_ft)
        top = elevation_to_storage_af(cfg, cfg.flood_pool_top_ft)
        fraction = (storage_af - bottom) / (top - bottom)
        state["flood_storage_percent"] = 100.0 * float(np.clip(fraction, 0.0, 1.0))
    if cfg.operation_scope:
        state["operation_scope"] = cfg.operation_scope
    if cfg.runtime_missing_inputs:
        state["runtime_missing_inputs"] = list(cfg.runtime_missing_inputs)
    return state


# ===========================================================================
# SECTION 3 - POLICY SELECTION (build the release rule the user asked for)
# ===========================================================================

def archive_existing(path) -> None:
    """Rename an existing output file to <name>.superseded-<timestamp> so a
    rerun of the same configuration cannot destroy earlier evidence."""
    path = Path(path)
    if not path.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.superseded-{stamp}")
    k = 0
    while target.exists():                      # same-second rerun
        k += 1
        target = path.with_name(f"{path.name}.superseded-{stamp}-{k}")
    path.rename(target)
    print(f"  previous output kept: {target.name}")


def build_policy(cfg: ReservoirConfig, method: str, llm: str, inflow: pd.Series,
                 timestep: str = "daily", dkp_audit_action: str = "warn",
                 run_tag: str = "", prompt_storage: bool = False,
                 max_audit_revisions: int = 0,
                 zeroshot_audit_action: str = "warn",
                 hide_availability_line: bool = False,
                 dkp_no_missing_inputs: bool = False,
                 release_categories: int = 0,
                 category_value: str = "llm",
                 temperature=None, seed: int = None,
                 zeroshot_knowledge: str = "target"):
    """Construct the release policy for one reservoir.

    `inflow` is the full inflow series at the requested timestep. The
    benchmark uses it for long-term statistics (mean inflow and seasonality),
    which should come from the whole record even when the simulated period is
    shortened.
    """
    # ---- option 1: the published benchmark rules ----------------------
    if method == "benchmark":
        hydropower = None
        if cfg.purpose == "hydropower":
            # BenchmarkPolicy routes purpose="hydropower" reservoirs to a
            # fitted HydropowerSDP table lookup (Abeshu et al. 2023, Sect.
            # 2.3.2) - nothing builds/fits that table automatically, it must
            # be done here. Wallenpaupack is the first (and so far only)
            # reservoir in RESERVOIRS with purpose="hydropower", so this
            # branch was never exercised before it existed.
            CFS_TO_M3S = 0.0283168466
            # `inflow` is ALREADY in m^3/s: load_daily_flow() multiplied the
            # CSV's cfs column by CFS_TO_CMS before returning it. An earlier
            # version multiplied by CFS_TO_M3S again here, shrinking the
            # inflow the DP fits against by a factor of ~35.3 and silently
            # corrupting the hydropower policy table (Wallenpaupack only,
            # since it is the one purpose="hydropower" reservoir).
            monthly_inflow_m3s = inflow.resample("MS").mean()
            # only one year of inflow to fit against (Wallenpaupack's proxy
            # data) - fit()'s docstring calls for "several years" of monthly
            # scenarios; with one year the DP still converges, just without
            # real inter-annual variability to average over. Consistent
            # with this reservoir's data being a stand-in throughout.
            hydropower = HydropowerSDP(
                # "usable" storage = alpha*C, per HydropowerSDP's own
                # docstring - matches how BenchmarkPolicy applies alpha
                # separately for k_rls, so alpha is applied once here.
                capacity_m3=cfg.capacity_af * ACREFT_TO_M3 * cfg.alpha,
                # Q_POWERHOUSE_MAX (turbine-only, NOT the 8,000 cfs channel
                # ceiling which includes emergency spillway flow that never
                # runs through turbines) - DKP §2.4.2 / PR-73 Table 4.19,
                # which documents PR-73 itself "forces min 1999 to saturate
                # it"; 2,000 cfs is that practical ceiling.
                q_max=2_000.0 * CFS_TO_M3S,
                installed_kw=44_000.0,          # 44 MW, FERC license ¶7
                # EL_TOP_OF_DAM (1,200 ft) - EL_INACTIVE (1,160 ft), DKP
                # §2.1 - the full depth range the wedge-reservoir head
                # model should span, anchored to the same top-of-dam
                # reference elevation capacity_af itself uses.
                dam_height_m=(1_200.0 - 1_160.0) * 0.3048,
            ).fit(monthly_inflow_m3s)
        return BenchmarkPolicy(
            purpose=cfg.purpose,
            capacity_m3=cfg.capacity_af * ACREFT_TO_M3,
            inflow=inflow,
            alpha=cfg.alpha,
            hydropower=hydropower,
        )

    # ---- options 2 & 3: LLM decision engines ---------------------------
    if method in ("zeroshot", "dkp"):
        # imported lazily so the benchmark method never needs LLM packages
        import importlib
        from zeroshot_llm_release import ReservoirBasicInfo, ZeroShotLLMPolicy

        # instantiate the chosen backend (Anthropic or Ollama)
        module_name, class_name, kwargs = LLM_BACKENDS[llm]
        if class_name == "OllamaBackend":
            # sampling settings for the local model: temperature None = the
            # model's own default (not sent); seed = Monte Carlo replicate
            kwargs = dict(kwargs, temperature=temperature, seed=seed)
        backend = getattr(importlib.import_module(module_name), class_name)(**kwargs)

        # the basic facts BOTH LLM methods start from - identical for the
        # two conditions, so retrieved DKP text is the only difference
        info = ReservoirBasicInfo(
            name=cfg.name,
            purpose=cfg.purpose.replace("_", " "),   # 'flood_control' -> 'flood control'
            capacity_af=cfg.capacity_af,
            max_release_cfs=cfg.max_release_cfs,
            min_release_cfs=cfg.min_release_cfs,
            river=cfg.river,
            normal_pool_af=cfg.normal_pool_af,
            monthly_target_af=cfg.monthly_target_af,
            operation_target_description=cfg.operation_target_description,
            decision_interval=timestep,
            public_profile=tuple(cfg.public_profile or ()),
            public_capacity_af=cfg.public_capacity_af,
            prompt_storage=prompt_storage,          # identical for BOTH arms
            show_availability_line=not hide_availability_line,  # identical for BOTH arms
            show_operation_target=(zeroshot_knowledge != "wiki"),  # zero-shot only (guarded)
            # The shared operation target restated as storage, using the same
            # rating curve applied to all three methods. BOTH target
            # elevations are converted, so the LLM still decides which one
            # applies to the current date; Python does not select the season.
            target_storage_equivalents=(
                {float(el): elevation_to_storage_af(cfg, float(el))
                 for el in sorted({e for _, e in cfg.seasonal_target_curve})}
                if cfg.seasonal_target_curve and cfg.elevation_storage_curve
                else None),
        )

        # Output files carry the method, engine, timestep, and simulated date
        # range. This preserves earlier smoke-test evidence instead of silently
        # overwriting it with the next run of the same method.
        period_suffix = f"_{run_tag}" if run_tag else ""
        stem = (f"{cfg.name.replace(' ', '_')}_{method}_{llm}_{timestep}"
                f"{period_suffix}")
        log = RESULTS_DIR / f"{stem}_decisions.txt"
        samples = RESULTS_DIR / f"{stem}_prompt_samples.txt"
        trace = RESULTS_DIR / f"{stem}_trace.jsonl"   # every prompt and raw reply
        # A rerun of the same configuration must not erase the evidence of the
        # previous run (register EX-02): existing outputs are renamed with a
        # timestamp, never deleted.
        for old in (log, trace, samples):
            archive_existing(old)

        if method == "zeroshot":
            return ZeroShotLLMPolicy(info=info, backend=backend,
                                     log_path=log, sample_path=samples,
                                     trace_path=trace,
                                     audit_action=zeroshot_audit_action,
                                     max_audit_revisions=max_audit_revisions)

        # method == "dkp": same baseline info + retrieved DKP knowledge.
        # Prefer the explicitly configured path.  A same-named file beside
        # the script is only a portability fallback; otherwise a stale copy
        # could silently shadow the intended data/DKP file.
        from dkp_llm_release import DKPLLMPolicy
        dkp_file = BASE_DIR / cfg.dkp_path
        if not dkp_file.exists():
            dkp_file = BASE_DIR / Path(cfg.dkp_path).name
        return DKPLLMPolicy(info=info, backend=backend,
                            log_path=log, sample_path=samples,
                            trace_path=trace,
                            dkp_path=dkp_file,
                            audit_action=dkp_audit_action,
                            max_audit_revisions=max_audit_revisions,
                            include_missing_inputs=not dkp_no_missing_inputs,
                            release_categories=release_categories,
                            category_value=category_value)

    raise ValueError(f"unknown method: {method!r}")


# ===========================================================================
# SECTION 4 - THE WATER-BALANCE SIMULATION (identical for every method)
# ===========================================================================

def needs_llm_consultation(inflow_now: float, inflow_yesterday: float,
                           threshold: float = INFLOW_CHANGE_THRESHOLD) -> bool:
    """Decide whether today warrants a fresh LLM consultation.

    Returns True when the LLM should be asked, False when the prior decision
    release can stand. The rule: consult whenever today's inflow differs
    from yesterday's by MORE than `threshold` (a fraction).

    Lives here, in the driver, rather than inside a policy class - it is
    run/cost control applied identically to every LLM method, not
    reservoir decision knowledge. See this module's docstring.

    Edge cases:
      * no yesterday yet (first simulated day) -> always consult
      * yesterday's inflow was zero -> consult unless today is also zero
        (a relative change is undefined against a zero baseline)

    TWO PROPERTIES OF THIS CRITERION TO ACCEPT CONSCIOUSLY (both are
    experimental-design choices, not bugs - confirm them with Prof. Yang
    before the production runs):

      1. It compares today with YESTERDAY, not with the inflow on the day
         of the last actual consultation. Successive +5% days therefore
         never trigger a call even though inflow has drifted well past 10%
         since the LLM last saw it (100 -> 105 -> 110 -> 115.5 = +15.5%,
         zero consultations). Switching to "change since the last
         consultation" means passing that day's inflow in place of
         `inflow_yesterday` from simulate() - a one-line change at the
         call site, deliberately not made unilaterally.
      2. It watches INFLOW only. Storage can move a long way on steady
         inflow (sustained drawdown or refill) without ever triggering a
         consultation.
    """
    if inflow_yesterday is None:
        return True
    if inflow_yesterday <= 0.0:
        return inflow_now > 0.0
    change = abs(inflow_now - inflow_yesterday) / inflow_yesterday
    return change > threshold


def simulate(cfg: ReservoirConfig, policy, inflow: pd.Series, *,
             inflow_change_threshold: float = INFLOW_CHANGE_THRESHOLD,
             timestep: str = "daily",
             llm_failure_action: str = "fallback") -> pd.DataFrame:
    """Run a daily or calendar-month water-balance simulation.

    Parameters
    ----------
    cfg    : the reservoir's configuration (capacities, pools)
    policy : any object with target_release(date, inflow_cms, storage_m3);
             may optionally provide record_outcome(...) to retain its prior
             simulated decision and the resulting physical outcome, and
             record_reuse(...) to be told about days with no consultation
    inflow : daily values or calendar-month mean values in m^3/s
    inflow_change_threshold : the LLM-consultation criterion (ignored for
             policies that don't set uses_llm)
    llm_failure_action : ``fallback`` continues with the policy fallback;
             ``stop`` aborts immediately so failed LLM calls cannot create a
             publishable-looking but invalid trajectory
    """
    if llm_failure_action not in ("fallback", "stop"):
        raise ValueError("llm_failure_action must be 'fallback' or 'stop'")
    # WATER BALANCE UNITS - explicit cubic feet, per Prof. Yang: "all of your
    # mass balance calculation should be cubic feet per month". Storage is a
    # volume in ft^3; inflow and release enter as ft^3 ACCUMULATED OVER THE
    # INTERVAL (rate_cfs x 86,400 x days). Every physical quantity in the
    # balance - capacity, inactive pool, availability, spill - is in ft^3, so
    # no term can silently mix units. Storage leaves ft^3 only at two
    # boundaries: acre-feet for the rating curve, and m^3 for the policy
    # interface (the policies convert internally to their prompt units).
    capacity_cf = cfg.capacity_af * CF_PER_ACREFT
    dead_cf = cfg.dead_storage_af * CF_PER_ACREFT
    storage_cf = cfg.initial_storage_af * CF_PER_ACREFT

    # does this policy consult an LLM? (benchmark doesn't - it is cheap and
    # deterministic, so it is asked every single day)
    uses_llm = getattr(policy, "uses_llm", False)
    prev_inflow_cms = None        # yesterday's inflow, for the criterion
    prev_decision_cms = None      # last bounded release decision; distinct from
    #                               controlled outflow and uncontrolled spill
    prev_seasonal_target_ft = None

    records = []                                   # one output row per step
    total_steps = len(inflow)
    for step_number, (date, i_now) in enumerate(inflow.items(), start=1):
        storage_start_cf = storage_cf              # storage at start of interval
        step_days = 1 if timestep == "daily" else date.days_in_month
        step_seconds = step_days * SECONDS_PER_DAY
        inflow_cfs = i_now / CFS_TO_CMS            # input series is m^3/s
        inflow_volume_cf = inflow_cfs * step_seconds
        s_start = storage_start_cf * M3_PER_CF     # policy interface (m^3)
        runtime_state = build_runtime_state(
            cfg, date, storage_start_cf / CF_PER_ACREFT, timestep
        )
        runtime_state["step_days"] = step_days
        # rating-curve conversion for audits that judge a model against the
        # target level it states itself (zero-shot Wikipedia-only version)
        runtime_state["storage_af_for_elevation"] = (
            lambda e, _cfg=cfg: elevation_to_storage_af(_cfg, e))
        # Neutral physical feasibility information, not an operating rule:
        # the interval-mean release cannot exceed inflow plus water stored
        # above the inactive pool. Supplying this ceiling prevents a later
        # physics clip from silently changing an LLM decision.
        available_volume_cf = inflow_volume_cf + max(storage_start_cf - dead_cf, 0.0)
        runtime_state["physically_available_release_cfs"] = (
            available_volume_cf / step_seconds
        )

        # STEP 0 - CONSULT?: for LLM policies only, decide whether today
        # needs a fresh consultation or the prior decision still stands.
        #
        # A prior decision may only be reused if it came from a SUCCESSFUL LLM
        # decision. If yesterday's call failed, the policy returned a
        # fallback number, and reusing that would let one transient timeout
        # silently govern several later days - the counters would report
        # "1 failure, 3 reuse days" when in truth all four days trace back
        # to the failure. So a failed decision forces a retry regardless of
        # how little inflow moved.
        last_failed = getattr(policy, "last_decision_failed", False)
        current_seasonal_target_ft = runtime_state.get("seasonal_target_ft")
        seasonal_target_changed = (
            current_seasonal_target_ft is not None
            and prev_seasonal_target_ft is not None
            and abs(current_seasonal_target_ft - prev_seasonal_target_ft) > 0.01
        )
        consulted = True
        # Monthly runs consult every month: with only 12 decisions per year,
        # reusing a prior decision could skip the April/October seasonal change.
        if (timestep == "daily" and uses_llm and prev_decision_cms is not None
                and not last_failed
                and not seasonal_target_changed
                and not needs_llm_consultation(i_now, prev_inflow_cms,
                                               inflow_change_threshold)):
            consulted = False

        # STEP 1 - POLICY: ask the release rule what it wants to do (or
        # reuse the prior decision and tell the policy so it can log the day)
        if consulted:
            if uses_llm:
                policy_request = policy.target_release(
                    date, i_now, s_start, runtime_state=runtime_state
                )
            else:
                policy_request = policy.target_release(date, i_now, s_start)
        else:
            policy_request = prev_decision_cms
            if hasattr(policy, "record_reuse"):
                policy.record_reuse(
                    date, i_now, s_start, policy_request,
                    runtime_state=runtime_state
                )

        # Monthly LLM runs previously appeared frozen because the driver only
        # printed after all calls completed. Report each completed consultation
        # immediately. Final runs stop on the first failed call rather than
        # allowing a repeated fallback to distort all subsequent storage.
        current_call_failed = bool(
            uses_llm and consulted
            and getattr(policy, "last_decision_failed", False)
        )
        if uses_llm and consulted:            # progress line, monthly AND daily
            if current_call_failed:
                call_status = "LLM FAILED"
            else:
                stats = getattr(getattr(policy, "backend", None),
                                "last_call_stats", None) or {}
                wall_seconds = stats.get("wall_seconds")
                call_status = (f"LLM success - {wall_seconds:.1f} sec"
                               if wall_seconds is not None else "LLM success")
            print(
                f"[{step_number}/{total_steps}] {date:%Y-%m-%d} - {call_status}",
                flush=True,
            )
        if current_call_failed and llm_failure_action == "stop":
            raise RuntimeError(
                f"LLM call failed on {date:%Y-%m-%d}; run stopped before "
                "the fallback could alter storage. See the decision log."
            )

        # STEP 2 - SHARED MODEL ENVELOPE: apply the configured controlled-
        # release range identically to benchmark, zero-shot and DKP. These
        # min/max values are model/operating limits, not the mass balance.
        # Then apply the true physical availability constraint. Uncontrolled
        # spill is calculated separately and is never called a decision.
        # The LLM (or benchmark) chooses a RATE; Python converts it to an
        # interval VOLUME. The LLM is never asked to do this conversion.
        policy_request_cfs = policy_request / CFS_TO_CMS
        policy_request_volume_cf = policy_request_cfs * step_seconds
        decision_release_cfs = float(np.clip(
            policy_request_cfs, cfg.min_release_cfs, cfg.max_release_cfs
        ))
        decision_release_volume_cf = decision_release_cfs * step_seconds
        controlled_release_volume_cf = float(np.clip(
            decision_release_volume_cf, 0.0, max(available_volume_cf, 0.0)
        ))

        # STEP 3 - WATER BALANCE, explicitly in cubic feet:
        #   storage_end_cf = storage_start_cf + inflow_volume_cf
        #                    - controlled_release_volume_cf
        storage_end_cf = (storage_start_cf + inflow_volume_cf
                          - controlled_release_volume_cf)

        # STEP 4 - SPILL: storage cannot exceed capacity; the excess volume
        # leaves over the spillway and counts as part of the total outflow
        spill_volume_cf = 0.0
        if storage_end_cf > capacity_cf:
            spill_volume_cf = storage_end_cf - capacity_cf
            storage_end_cf = capacity_cf

        # STEP 4b - HARD SAFETY NET: assert the balance closes to floating-
        # point precision, every single step. This does not change any
        # number; it only catches a future bug immediately (a raised
        # exception) instead of relying on a later, separate spot-check.
        water_balance_residual_cf = (
            storage_start_cf + inflow_volume_cf
            - controlled_release_volume_cf - spill_volume_cf - storage_end_cf
        )
        residual_tolerance_cf = max(1.0, 1e-9 * max(capacity_cf, 1.0))
        if abs(water_balance_residual_cf) > residual_tolerance_cf:
            raise RuntimeError(
                f"water-balance residual {water_balance_residual_cf:,.3f} ft^3 "
                f"on {date:%Y-%m-%d} exceeds tolerance "
                f"{residual_tolerance_cf:,.3f} ft^3"
            )

        storage_cf = storage_end_cf                # next interval starts here

        # rates, derived from the volumes, for interpretation and the policies
        decision_release = decision_release_cfs * CFS_TO_CMS          # m^3/s
        controlled_release = (controlled_release_volume_cf / step_seconds) * CFS_TO_CMS
        spill = (spill_volume_cf / step_seconds) * CFS_TO_CMS
        s_end = storage_end_cf * M3_PER_CF                            # m^3

        # Give LLM policies the previous SIMULATED RELEASE DECISION requested
        # by Prof. Yang. Keep actual controlled outflow and spill available
        # separately for bookkeeping; uncontrolled spill is not a decision and
        # therefore must not appear in the prompt's decision-history list.
        if hasattr(policy, "record_outcome"):
            policy.record_outcome(
                date=date,
                decision_release_cms=decision_release,
                storage_end_m3=s_end,
                inflow_cms=i_now,
                implemented_release_cms=controlled_release + spill,
            )

        end_state = build_runtime_state(
            cfg, date, storage_end_cf / CF_PER_ACREFT, timestep
        )

        # Remember the bounded decision for tomorrow's consultation decision.
        # Reuse repeats the prior decision, never a spill-inclusive outflow.
        prev_inflow_cms = i_now
        prev_decision_cms = decision_release
        prev_seasonal_target_ft = current_seasonal_target_ft

        # collect the day's numbers (converted to reporting units)
        records.append({
            "date": date,
            "inflow_cfs": i_now / CFS_TO_CMS,
            "policy_release_request_cfs": policy_request / CFS_TO_CMS,
            "decision_release_cfs": decision_release / CFS_TO_CMS,
            "controlled_release_cfs": controlled_release / CFS_TO_CMS,
            "release_cfs": (controlled_release + spill) / CFS_TO_CMS,
            "spill_cfs": spill / CFS_TO_CMS,
            # explicit names: the decision log records START storage and this
            # CSV previously called END storage "storage_af", which made a
            # one-month timing error easy to introduce when joining the two
            "storage_start_af": storage_start_cf / CF_PER_ACREFT,
            "storage_end_af": storage_end_cf / CF_PER_ACREFT,
            "step_days": step_days,
            # --- auditable interval volumes (ft^3) - the water balance itself
            "storage_start_cf": storage_start_cf,
            "inflow_volume_cf": inflow_volume_cf,
            "policy_release_request_volume_cf": policy_request_volume_cf,
            "decision_release_volume_cf": decision_release_volume_cf,
            "controlled_release_volume_cf": controlled_release_volume_cf,
            "spill_volume_cf": spill_volume_cf,
            "storage_end_cf": storage_end_cf,
            "water_balance_residual_cf": water_balance_residual_cf,
            "pool_elevation_start_ft": runtime_state.get("pool_elevation_ft"),
            # explicit end-of-interval name, matching storage_start/end_af
            # (previously "pool_elevation_ft", which did not say which end)
            "pool_elevation_end_ft": end_state.get("pool_elevation_ft"),
            "seasonal_target_ft": runtime_state.get("seasonal_target_ft"),
            "seasonal_target_start_ft": runtime_state.get(
                "seasonal_target_start_ft"
            ),
            "seasonal_target_mean_ft": runtime_state.get(
                "seasonal_target_mean_ft"
            ),
            "seasonal_target_storage_af": runtime_state.get(
                "seasonal_target_storage_af"
            ),
            "physically_available_release_cfs": runtime_state.get(
                "physically_available_release_cfs"
            ),
            "flood_storage_percent_start": runtime_state.get(
                "flood_storage_percent"
            ),
            "llm_consulted": consulted if uses_llm else "",
        })

    # No rounding: the results file keeps full precision, so anyone can
    # recompute the water balance from ANY column (cfs or cubic feet) and
    # reproduce Python's end storage exactly. (Rounding to 3 decimals made a
    # hand recalculation from cfs differ by up to ~1,800 ft3 a month.)
    return pd.DataFrame(records).set_index("date")


# ===========================================================================
# SECTION 5 - EVALUATION METRICS (simulated vs. observed release)
# ===========================================================================

def nse(obs: pd.Series, sim: pd.Series) -> float:
    """Nash-Sutcliffe efficiency: 1 = perfect, 0 = no better than the mean,
    negative = worse than just predicting the observed mean."""
    mask = obs.notna() & sim.notna()               # only days both exist
    obs, sim = obs[mask], sim[mask]
    return 1.0 - ((obs - sim) ** 2).sum() / ((obs - obs.mean()) ** 2).sum()


def pbias(obs: pd.Series, sim: pd.Series) -> float:
    """Percent bias (%): positive = simulation releases too much water
    overall, negative = too little."""
    mask = obs.notna() & sim.notna()
    obs, sim = obs[mask], sim[mask]
    return 100.0 * (sim - obs).sum() / obs.sum()


def _resolve_observed_path(cfg: ReservoirConfig):
    """Find the observed-release file. Tries the configured name first, then
    any USGS file for the same gage number, so both "F.E. Walter Dam" and the
    underscore variant ("F_E__Walter_Dam") that file transfers produce work."""
    if cfg.observed_release_csv is None:
        return None
    exact = DAILY_DIR / cfg.observed_release_csv
    if exact.exists():
        return exact
    gage = cfg.observed_release_csv.split("-")[0:2]          # ["USGS", "01447800"]
    if len(gage) == 2:
        hits = sorted(DAILY_DIR.glob(f"{gage[0]}-{gage[1]}*Release_daily.csv"))
        if hits:
            return hits[0]
    return None


def observed_release_cfs(cfg: ReservoirConfig, timestep: str):
    """Observed release (cfs) aggregated to the simulation timestep, or None.

    Called only AFTER simulate() returns. Observations are never passed to a
    policy, a prompt or the water balance."""
    path = _resolve_observed_path(cfg)
    if path is None:
        return None
    return aggregate_flow(load_daily_flow(str(path)), timestep) / CFS_TO_CMS


def evaluate(cfg: ReservoirConfig, result: pd.DataFrame,
             timestep: str = "daily") -> str:
    """Skill summary against the observed release gauge.

    Reports the whole run and, when the run spans 2014, two evaluation
    windows split at 2014 (the year of the current WCM revision). The split
    is a reporting convenience ONLY. It makes no claim about which operating
    rules governed historical operations in either window: the 1370 ft
    recreation pool appears on Plate 7-2 (dated 2011), and the manual does
    not establish when it began. Do not describe either window as having a
    particular rule "in force" unless that is independently confirmed.
    """
    if cfg.observed_release_csv is None:
        return "observed release evaluation deferred"
    obs = observed_release_cfs(cfg, timestep)
    if obs is None:
        return ("observed release evaluation deferred (file not found in "
                f"{DAILY_DIR.name}: {cfg.observed_release_csv})")
    sim = result["release_cfs"]
    obs = obs.reindex(sim.index)
    n_all = int((obs.notna() & sim.notna()).sum())
    if n_all < 2:
        return "observed release evaluation skipped (no overlapping dates)"

    def line(label, o, s):
        k = int((o.notna() & s.notna()).sum())
        return (f"{label}: NSE = {nse(o, s):.3f}, PBIAS = {pbias(o, s):+.1f} % "
                f"({k} steps)")

    parts = [line("vs observed release, whole run", obs, sim)]
    pre, post = sim.index.year < 2014, sim.index.year >= 2014
    min_steps = 12 if timestep == "monthly" else 365
    if pre.sum() >= min_steps and post.sum() >= min_steps:
        y0, y1 = sim.index.year.min(), sim.index.year.max()
        parts.append(line(f"    {y0}-2013 evaluation window", obs[pre], sim[pre]))
        parts.append(line(f"    2014-{y1} evaluation window", obs[post], sim[post]))
    return "\n  ".join(parts)


# ===========================================================================
# SECTION 6 - MAIN PROGRAM
# ===========================================================================

def main() -> None:
    # ---- read the command line -----------------------------------------
    parser = argparse.ArgumentParser(
        description="Daily or monthly reservoir operation model"
    )
    parser.add_argument("--method", choices=["benchmark", "zeroshot", "dkp"],
                        default="benchmark",
                        help="release rule (see module docstring)")
    parser.add_argument("--llm", choices=sorted(LLM_BACKENDS), default="gemma4",
                        help="decision engine for the zeroshot/dkp methods")
    parser.add_argument("--reservoir", type=str, default=None,
                        help='run only this reservoir by name, e.g. '
                             '--reservoir "F.E. Walter Dam" (default: all '
                             "reservoirs with complete data)")
    parser.add_argument("--timestep", choices=["daily", "monthly"],
                        default="daily",
                        help="decision and water-balance interval")
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="simulate only the first N daily/monthly steps",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="first simulation date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="last simulation date in YYYY-MM-DD format",
    )
    parser.add_argument("--days", type=int, default=None,
                        help=argparse.SUPPRESS)  # backward-compatible daily alias
    parser.add_argument("--run-mode", choices=["exploratory", "final"],
                        default="exploratory",
                        help="'exploratory' (default) runs reservoirs whose "
                             "config is not fully confirmed, with a warning; "
                             "'final' refuses them, for results that go in "
                              "the paper")
    parser.add_argument(
        "--prompt-storage",
        choices=["on", "off"],
        default="off",
        help=("'off' (default) gives the LLM exactly Prof. Yang's specified "
              "inputs - inflow, beginning water level, previous simulated "
              "releases - plus interval length. 'on' is a SEPARATE condition "
              "that also supplies beginning storage and the target in storage "
              "terms, to BOTH zero-shot and DKP. Outputs are labelled."),
    )
    parser.add_argument(
        "--max-audit-revisions",
        type=int,
        default=0,
        help=("Self-correction rounds after a failed audit, applied "
              "IDENTICALLY to zero-shot and DKP (default 0 = single pass, "
              "the controlled comparison). On a FAIL the same model is asked "
              "to re-answer using the same information it already had - no "
              "release value is ever supplied - up to this many times; if "
              "still FAIL, the last candidate is accepted and the month is "
              "flagged. Any value > 0 is a separate, labelled self-"
              "correction experiment, not comparable with single-pass runs."),
    )
    parser.add_argument(
        "--dkp-include-missing-inputs",
        action="store_true",
        help=("Restore the 2026-10-03 baseline DKP prompt: the missing_inputs "
              "answer field, the missing-information fallback mode and its "
              "instructions. By DEFAULT these are removed (reservoir-only model "
              "boundary; files tagged noMissingInputs). For an exact baseline "
              "reproduction also use DKP v1.3 and --show-availability-line."),
    )
    parser.add_argument(
        "--zeroshot-knowledge",
        choices=["target", "wiki"],
        default="target",
        help=("Zero-shot only. 'target' (default): public facts plus the "
              "1300/1370 ft operation target. 'wiki': public (Wikipedia-level) "
              "facts only - no target levels; the audit then judges the model "
              "against the target it states itself. Files tagged wikiOnly."),
    )
    parser.add_argument(
        "--temperature",
        default="default",
        help=("LLM sampling temperature. 'default' (the default) sends no "
              "temperature, so Ollama uses the model's own default (recorded in "
              "the provenance log); or give a number, e.g. 0 for the earlier "
              "deterministic runs. Files tagged tempDefault or tempN."),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=("Random seed for the LLM's sampling. Use a different seed for "
              "each Monte Carlo replicate (1, 2, 3, ...): each run is then "
              "repeatable on the same computer. Files tagged seedN."),
    )
    parser.add_argument(
        "--release-categories",
        type=int,
        default=0,
        help=("DKP only. 0 (default) = numerical mode: the LLM gives a release "
              "in cfs. N > 0 = category mode: N release ranges built from the "
              "manual's minimum and maximum release (50 and 10,000 cfs for F.E. "
              "Walter), spaced evenly on a logarithmic scale; the LLM picks one. "
              "Files tagged catN."),
    )
    parser.add_argument(
        "--category-value",
        choices=["llm", "midpoint"],
        default="llm",
        help=("Category mode only. 'llm' (default): the LLM also gives the "
              "release inside its chosen range, and Python only checks it lies "
              "inside. 'midpoint': Python applies the range's geometric midpoint. "
              "Files tagged catNmid."),
    )
    parser.add_argument(
        "--consult-every-day",
        action="store_true",
        help=("Daily runs only: ask the LLM every day. By default a daily run "
              "reuses the previous decision when today's inflow differs from "
              "yesterday's by 10%% or less (cost control); monthly runs always "
              "consult every month. Output files are tagged everyDay."),
    )
    parser.add_argument(
        "--show-availability-line",
        action="store_true",
        help=("Restore the 2026-10-03 baseline prompt line 'Maximum release given "
              "the water available this interval' (item 6), in BOTH arms. By "
              "DEFAULT it is not shown (files tagged noAvailLine): the model copied "
              "that number, and it is not information a Wikipedia-level source "
              "provides. Python still enforces the same limit on the water "
              "available, the audit and the water balance either way."),
    )
    parser.add_argument(
        "--inflow-file",
        default=None,
        help=("inflow CSV to use instead of the reservoir's configured file. "
              "A multi-reservoir file (with a `reservoir` column) is filtered "
              "automatically. Outputs are tagged with the file's year span."),
    )
    parser.add_argument(
        "--initial-elevation-ft",
        type=float, default=None,
        help=("starting pool elevation (ft NGVD29), converted to storage with "
              "the rating curve. Use for a historical start, e.g. the observed "
              "pool on the start date. Default: the configured start (1300 ft)."),
    )
    parser.add_argument(
        "--initial-storage-af",
        type=float, default=None,
        help="starting storage (acre-feet). Alternative to --initial-elevation-ft.",
    )
    parser.add_argument(
        "--zeroshot-audit-action",
        choices=["warn", "record", "stop"],
        default=None,
        help=("zero-shot physics audit action - the SAME physics checks as the "
              "DKP arm, which record or stop but never correct. Default: stop "
              "for final runs, warn for exploratory runs."),
    )
    parser.add_argument(
        "--dkp-audit-action",
        choices=["warn", "record", "stop"],
        default=None,
        help=("what to do when a DKP decision fails the deterministic "
              "rule-consistency audit. A failure is ALWAYS classified FAIL; "
              "this only sets the action. 'stop' aborts before an invalid "
              "decision alters storage (required for any reported result); "
              "'warn' continues; 'record' continues and marks the whole run "
              "a DIAGNOSTIC trajectory, for documenting a failure mode "
              "across a full season. Default: warn for exploratory runs, "
              "stop for final runs"),
    )
    parser.add_argument(
        "--llm-failure-action",
        choices=["fallback", "stop"],
        default=None,
        help=("what to do when a zero-shot or DKP LLM call fails; default: "
              "fallback for exploratory runs, stop for final runs"),
    )
    args = parser.parse_args()

    if args.days is not None:
        if args.timestep != "daily":
            parser.error("--days is only valid with --timestep daily; use --steps")
        if args.steps is not None:
            parser.error("use only one of --steps or --days")
        args.steps = args.days

    RESULTS_DIR.mkdir(exist_ok=True)   # make sure the output folder exists
    # output label: 'benchmark', or method + engine like 'dkp_sonnet5'
    run_label = (args.method if args.method == "benchmark"
                 else f"{args.method}_{args.llm}")
    # prompt-condition tags - storage on/off and self-correction are separate
    # experimental conditions, so their outputs must never overwrite each other
    prompt_storage = args.prompt_storage == "on"
    if args.max_audit_revisions < 0:
        raise SystemExit("--max-audit-revisions must be >= 0")
    condition_tags = []
    if args.method in ("zeroshot", "dkp"):
        condition_tags.append("storageON" if prompt_storage else "storageOFF")
    if args.method in ("zeroshot", "dkp") and args.max_audit_revisions > 0:
        condition_tags.append(f"selfcorrect{args.max_audit_revisions}")
    if args.zeroshot_knowledge == "wiki":
        if args.method != "zeroshot":
            parser.error("--zeroshot-knowledge wiki applies to the zero-shot method only")
        condition_tags.append("wikiOnly")
    if args.method in ("zeroshot", "dkp") and not args.show_availability_line:
        condition_tags.append("noAvailLine")
    if args.method in ("zeroshot", "dkp") and args.consult_every_day:
        if args.timestep != "daily":
            parser.error("--consult-every-day is only valid with --timestep daily")
        condition_tags.append("everyDay")
    if args.method == "dkp" and not args.dkp_include_missing_inputs:
        condition_tags.append("noMissingInputs")
    if args.method in ("zeroshot", "dkp"):
        if str(args.temperature).lower() == "default":
            args.temperature_value = None
            condition_tags.append("tempDefault")
        else:
            try:
                args.temperature_value = float(args.temperature)
            except ValueError:
                parser.error("--temperature must be 'default' or a number")
            if args.temperature_value < 0:
                parser.error("--temperature must not be negative")
            if args.temperature_value == int(args.temperature_value):
                args.temperature_value = int(args.temperature_value)
            condition_tags.append(f"temp{args.temperature_value}")
        if args.seed is not None:
            condition_tags.append(f"seed{args.seed}")
    else:
        args.temperature_value = None
    if args.release_categories:
        if args.method != "dkp":
            parser.error("--release-categories is DKP only: zero-shot has no manual "
                         "release limits to build categories from (numerical mode)")
        if args.release_categories < 1:
            parser.error("--release-categories must be a positive number")
        condition_tags.append(f"cat{args.release_categories}"
                              + ("mid" if args.category_value == "midpoint" else ""))
    condition_tag = "_".join(condition_tags)
    if condition_tag:
        run_label += f"_{condition_tag}"

    # ---- select which reservoir(s) to run --------------------------------
    if args.reservoir:
        matches = [cfg for cfg in RESERVOIRS if cfg.name == args.reservoir]
        if not matches:
            names = ", ".join(f'"{cfg.name}"' for cfg in RESERVOIRS)
            raise SystemExit(f'--reservoir "{args.reservoir}" not found. '
                              f"Available: {names}")
        reservoirs_to_run = matches
    else:
        reservoirs_to_run = RESERVOIRS

    # ---- run every selected reservoir --------------------------------
    for cfg in reservoirs_to_run:
        # safety guard: never silently simulate a reservoir with unconfirmed
        # physical constants (e.g. Wallenpaupack, pending real gauge/license
        # data) - an incorrect guess here would corrupt results silently.
        required = ["capacity_af", "initial_storage_af", "max_release_cfs",
                    "min_release_cfs", "normal_pool_af"]
        # research-validity gate: a placeholder or observed stand-in is a
        # NUMBER, so the None-check below cannot see it. config_confirmed
        # carries that information explicitly.
        if not cfg.config_confirmed:
            note = f"{cfg.name}: config not confirmed - {cfg.config_notes}"
            if args.run_mode == "final":
                raise SystemExit(
                    f"ERROR: {note}\n"
                    f"       --run-mode final refuses unconfirmed configs. "
                    f"Confirm the values against the source documents, set "
                    f"config_confirmed=True, or re-run with "
                    f"--run-mode exploratory.")
            print(f"WARNING {note}")
            print("        (exploratory run - do not use these results in "
                  "the paper)")

        missing = [f for f in required if getattr(cfg, f) is None]
        if missing:
            msg = (f'{cfg.name}: missing/unconfirmed field(s) {missing} - '
                   f"see the TODO comments in this reservoir's config block.")
            if args.reservoir:
                # explicitly requested - fail loudly, don't guess
                raise SystemExit(f"ERROR: {msg}")
            else:
                # running "all" - skip it, but say so clearly
                print(f"SKIPPING {msg}")
                continue

        # Load daily source data once, then aggregate consistently for the
        # requested decision interval. Monthly values are mean discharge.
        # --- initial condition: configured default, or a historical start ---
        if args.initial_elevation_ft is not None and args.initial_storage_af is not None:
            raise SystemExit("ERROR: give --initial-elevation-ft OR --initial-storage-af, not both")
        extra_tags = []
        if args.initial_elevation_ft is not None:
            curve = cfg.elevation_storage_curve
            lo, hi = curve[0][0], curve[-1][0]
            if not lo <= args.initial_elevation_ft <= hi:
                raise SystemExit(f"ERROR: --initial-elevation-ft outside the rating "
                                 f"curve ({lo}-{hi} ft)")
            cfg = replace(cfg, initial_storage_af=elevation_to_storage_af(
                cfg, args.initial_elevation_ft))
            extra_tags.append(f"init{args.initial_elevation_ft:.2f}ft")
        elif args.initial_storage_af is not None:
            if args.initial_storage_af < 0 or args.initial_storage_af > cfg.capacity_af:
                raise SystemExit("ERROR: --initial-storage-af outside 0..capacity")
            cfg = replace(cfg, initial_storage_af=args.initial_storage_af)
            extra_tags.append(f"init{args.initial_storage_af:.0f}af")

        # --- inflow: configured file, or an alternative via --inflow-file ---
        inflow_source = args.inflow_file or cfg.inflow_csv
        inflow_daily = (load_daily_flow(inflow_source, cfg.inflow_reservoir_key)
                        * cfg.inflow_scale)
        if args.inflow_file:
            extra_tags.append(f"inflow{inflow_daily.index.min().year}-"
                              f"{inflow_daily.index.max().year}")
        inflow_full = aggregate_flow(inflow_daily, args.timestep)

        # Select the requested simulation period. Keep inflow_full unchanged
        # so the benchmark method still derives its long-term statistics from
        # the complete available record.
        inflow_sim = inflow_full.copy()

        if args.start_date:
            start_date = pd.Timestamp(args.start_date)
            inflow_sim = inflow_sim.loc[inflow_sim.index >= start_date]

        if args.end_date:
            end_date = pd.Timestamp(args.end_date)
            inflow_sim = inflow_sim.loc[inflow_sim.index <= end_date]

        if args.steps:
            inflow_sim = inflow_sim.iloc[:args.steps]

        if inflow_sim.empty:
            raise SystemExit(
                f"ERROR: no inflow observations found between "
                f"{args.start_date or 'record start'} and "
                f"{args.end_date or 'record end'}"
            )

        covered_start = inflow_sim.index.min()
        covered_end = inflow_sim.index.max()
        if args.timestep == "monthly":
            # Monthly rows are labelled on the first day, but each decision
            # covers the complete calendar month. Name the artifact with the
            # actual covered month-end date rather than its first-day label.
            covered_end = covered_end + pd.offsets.MonthEnd(0)
        run_tag = f"{covered_start:%Y%m%d}_{covered_end:%Y%m%d}"
        if extra_tags:     # alternative inflow / initial condition never overwrite
            run_tag += "_" + "_".join(extra_tags)

        dkp_audit_action = args.dkp_audit_action or (
            "stop" if args.run_mode == "final" else "warn"
        )
        zeroshot_audit_action = args.zeroshot_audit_action or (
            "stop" if args.run_mode == "final" else "warn"
        )
        llm_failure_action = args.llm_failure_action or (
            "stop" if args.run_mode == "final" else "fallback"
        )
        policy = build_policy(
            cfg, args.method, args.llm, inflow_full,
            timestep=args.timestep,
            dkp_audit_action=dkp_audit_action,
            # log and prompt-sample filenames carry the same condition tag
            run_tag=(f"{condition_tag}_{run_tag}" if condition_tag else run_tag),
            prompt_storage=prompt_storage,
            max_audit_revisions=args.max_audit_revisions,
            zeroshot_audit_action=zeroshot_audit_action,
            hide_availability_line=not args.show_availability_line,
            dkp_no_missing_inputs=not args.dkp_include_missing_inputs,
            release_categories=args.release_categories,
            category_value=args.category_value,
            temperature=args.temperature_value, seed=args.seed,
            zeroshot_knowledge=args.zeroshot_knowledge,
        )
        try:
            result = simulate(
                cfg, policy, inflow_sim, timestep=args.timestep,
                llm_failure_action=llm_failure_action,
                # a negative threshold makes every daily step a consultation
                inflow_change_threshold=(-1.0 if args.consult_every_day
                                         else INFLOW_CHANGE_THRESHOLD),
            )
        finally:
            # Preserve prompt/audit evidence even when strict DKP validation
            # stops a run on the first invalid decision.
            if hasattr(policy, "finalize"):
                policy.finalize()

        # ---- write the daily results CSV --------------------------------
        out_path = RESULTS_DIR / (
            f"{cfg.name.replace(' ', '_')}_{run_label}_{args.timestep}_"
            f"{run_tag}.csv"
        )
        # Observed release is attached AFTER the simulation has finished, for
        # plotting and evaluation only - it played no part in any decision.
        obs_release = observed_release_cfs(cfg, args.timestep)
        if obs_release is not None:
            result["observed_release_cfs"] = obs_release.reindex(result.index).round(3)
        archive_existing(out_path)     # never overwrite a previous run's CSV
        result.to_csv(out_path, date_format="%Y-%m-%d")

        # ---- print the run summary --------------------------------------
        print(f"\n{cfg.name} ({cfg.purpose}, {run_label} method, "
              f"{args.timestep})")
        if args.method in ("zeroshot", "dkp"):
            print(f"  inflow: {Path(inflow_source).name}"
                  + (f" [{cfg.inflow_reservoir_key}]" if cfg.inflow_reservoir_key else "")
                  + f" | initial storage {cfg.initial_storage_af:,.1f} af "
                  f"({storage_to_elevation_ft(cfg, cfg.initial_storage_af):.2f} ft)")
            print(f"  prompt condition: storage {args.prompt_storage.upper()}"
                  + (f", self-correction {args.max_audit_revisions} round(s) "
                     "(separate experiment - not comparable with single-pass runs)"
                     if args.max_audit_revisions > 0
                     else ", single-pass")
                  + (", availability line not shown"
                     if not args.show_availability_line else ", availability line SHOWN (baseline)")
                  + ((", missing-inputs content removed (reservoir-only boundary)"
                      if not args.dkp_include_missing_inputs else ", missing-inputs content INCLUDED (baseline)")
                     if args.method == "dkp" else "")
                  + (", Wikipedia-only knowledge (no operation target)"
                     if args.zeroshot_knowledge == "wiki" else "")
                  + (f", {args.release_categories} release categories ({args.category_value} value)"
                     if args.release_categories else ", numerical release"))
            prov = getattr(policy, "provenance", None) or {}
            print(f"  provenance: Ollama {prov.get('ollama_version')} | "
                  f"model {prov.get('model')} | digest {prov.get('model_digest')}")
            print(f"  temperature: {prov.get('temperature_setting')} -> effective "
                  f"{prov.get('effective_temperature')} | seed {prov.get('seed')}")
        if args.method == "benchmark":
            print(f"  degree of regulation gamma = {policy.gamma:.3f}, "
                  f"mean annual inflow = {policy.i_mean / CFS_TO_CMS:,.0f} cfs, "
                  f"operational year starts in month {policy.op_year_start_month}")
        if args.method in ("zeroshot", "dkp"):
            # attempts / successes / failures / reuses reported separately,
            # so a run of silent timeouts can't look like a run of decisions
            criterion = ("every monthly step" if args.timestep == "monthly"
                         else f"inflow change > {INFLOW_CHANGE_THRESHOLD:.0%}")
            print(f"  steps decided: {policy.days_decided} "
                  f"(consultation criterion: {criterion})")
            print(f"  LLM attempts: {policy.llm_attempts} "
                  f"({policy.llm_successes} succeeded, "
                  f"{policy.llm_failures} failed -> fallback), "
                      f"reuse steps: {policy.reuse_days}")
            if policy.llm_failures:
                print(f"  WARNING: {policy.llm_failures} of "
                      f"{policy.llm_attempts} LLM calls failed - see the "
                      f"reasoning= entries in the decision log")
            # only prints when the backend actually reports timing/tokens
            # (Ollama does; AnthropicBackend/GroqBackend currently don't)
            if getattr(policy, "total_wall_seconds", 0.0) > 0:
                avg_wall = policy.total_wall_seconds / max(policy.llm_successes, 1)
                print(f"  LLM compute: {policy.total_wall_seconds:,.0f} sec total "
                      f"({avg_wall:.1f} sec/call avg), "
                      f"{policy.total_prompt_tokens:,} prompt + "
                      f"{policy.total_response_tokens:,} response tokens")
            if getattr(policy, "total_backend_retries", 0) > 0:
                print(
                    f"  backend retries: {policy.total_backend_retries} "
                    f"({policy.total_backend_attempts} raw requests for "
                    f"{policy.llm_attempts} decision steps)"
                )
            # shared physics audit - the SAME metric for both LLM arms
            physics_fails = (policy.physics_audit_failure_count
                             if args.method == "dkp" else policy.audit_failures)
            print(f"  physics audit (shared by both arms): {physics_fails} FAIL "
                  f"of {policy.llm_successes} decisions "
                  f"(hard physics {getattr(policy, 'hard_physics_failures', 0)}, "
                  f"policy {getattr(policy, 'policy_failures', 0)}, "
                  f"unattributed-hard "
                  f"{getattr(policy, 'unattributed_hard_physics', 0)})")
            if args.method == "zeroshot":
                if getattr(policy, "audit_revision_attempts", 0):
                    print(
                        f"  self-correction: "
                        f"{policy.audit_revision_successes} accepted after "
                        f"{policy.audit_revision_attempts} revision call(s)"
                    )
                if policy.audit_failures and policy.audit_action != "stop":
                    first = policy.first_audit_failure or {}
                    print("  " + "!" * 66)
                    print("  DIAGNOSTIC TRAJECTORY - NOT A VALID RESEARCH RESULT")
                    print(f"  {policy.audit_failures} decision(s) failed the physics "
                          f"audit (after self-correction, if any) and still altered "
                          f"storage.")
                    if first:
                        print(f"  First failure {first.get('date')}: "
                              f"{'; '.join(first.get('failures', []))}")
                    print("  " + "!" * 66)
            if args.method == "dkp":
                print(
                    f"  DKP rule audit: {policy.audit_passes} PASS, "
                    f"{policy.audit_warnings} WARN, "
                    f"{policy.audit_failures} FAIL "
                    f"(action={policy.audit_action})"
                )
                if getattr(policy, "audit_revision_attempts", 0):
                    print(
                        f"  self-correction: "
                        f"{policy.audit_revision_successes} accepted after "
                        f"{policy.audit_revision_attempts} revision call(s)"
                    )
                # A FAIL means an invalid decision entered the storage
                # trajectory. With --dkp-audit-action stop the run has
                # already aborted; if it did not, the completed CSV is a
                # diagnostic artefact and must not be reported as a result.
                if policy.audit_failures and policy.audit_action != "stop":
                    first = policy.first_audit_failure or {}
                    print("  " + "!" * 66)
                    print("  DIAGNOSTIC TRAJECTORY - NOT A VALID RESEARCH RESULT")
                    print(f"  {policy.audit_failures} decision(s) failed the rule "
                          f"audit and still altered storage.")
                    if first:
                        print(f"  First failure {first.get('date')}: "
                              f"{'; '.join(first.get('failures', []))}")
                    print("  Re-run with --dkp-audit-action stop for a reportable run.")
                    print("  " + "!" * 66)
        print(f"  mean simulated release = {result['release_cfs'].mean():,.0f} cfs, "
              f"storage range = {result['storage_end_af'].min():,.0f}-"
              f"{result['storage_end_af'].max():,.0f} af")
        print(f"  maximum absolute water-balance residual = "
              f"{result['water_balance_residual_cf'].abs().max():,.6f} ft^3")
        print(f"  {evaluate(cfg, result, args.timestep)}")
        print(f"  results -> {out_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
