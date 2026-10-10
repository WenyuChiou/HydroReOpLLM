"""Benchmark reservoir release rules from Abeshu et al. (2023), Sect. 2.3.1-2.3.3.

WHAT THIS FILE DOES
===================
This module answers ONE question each simulated decision step:

    "Given today's inflow and the current storage, how much water should the
     reservoir release?"  (the "benchmark" way - published generic rules)

It implements the three release rules of:

    Abeshu, G. W., et al. (2023): Enhancing the representation of water
    management in global hydrological models, Geosci. Model Dev., 16,
    5449-5472.

one rule per reservoir purpose:

    * Irrigation reservoirs   (Sect. 2.3.1, Eqs. 1-2) - release follows the
      downstream water demand (Hanasaki et al., 2006 scheme).
    * Hydropower reservoirs   (Sect. 2.3.2) - release follows a power-
      maximizing lookup table built by dynamic programming.
    * Flood control / other   (Sect. 2.3.3, Eq. 4)   - release is a function
      of mean inflow, current inflow, and storage only.

HOW THE PIECES FIT TOGETHER
===========================
    reservoir_model.py  (the driver: water balance, input/output)
        |
        |  creates one BenchmarkPolicy per reservoir, then calls
        |  policy.target_release(date, inflow, storage) every step
        v
    BenchmarkPolicy  (bottom of this file - the "traffic director")
        |-- irrigation      -> irrigation_provisional_release() + hanasaki_final_release()
        |-- hydropower      -> HydropowerSDP.release()  (table lookup)
        |-- flood_control / other -> hanasaki_final_release() with i_mean

KEY SYMBOLS (used throughout, following the paper's notation)
=============================================================
    i_mean  mean annual inflow (m^3/s)      C      storage capacity (m^3)
    gamma   degree of regulation = C / (annual inflow volume)  [-]
    alpha   capacity reduction factor (paper fixes it at 0.85) [-]
    k_rls   release coefficient = S_start_of_year / (alpha*C)  [-]

UNITS
=====
All flows are m^3/s and all storages m^3 unless a name says otherwise.
The paper works at a MONTHLY time step. The project can also call the same
policy daily; in that case the current day's inflow stands in for i_m,y,
while k_rls still updates only once per operational year.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# --- unit-conversion constants used across the project ---------------------
SECONDS_PER_DAY = 86400.0     # seconds in one day (converts m^3/s <-> m^3/day)
DAYS_PER_YEAR = 365.25        # average days per year (includes leap years)


# ===========================================================================
# SECTION 1 - THE CORE RELEASE EQUATIONS (plain functions, no state)
# ===========================================================================
# These two small functions ARE the benchmark method. Everything else in the
# file is bookkeeping around them.

def irrigation_provisional_release(i_mean: float, d_now: float, d_mean: float) -> float:
    """Provisional release R'_m,y for irrigation reservoirs (paper Eq. 1).

    The idea: an irrigation reservoir should release more when downstream
    demand is high and less when it is low, centred on the mean inflow.

    Parameters
    ----------
    i_mean : mean annual inflow (m^3/s)
    d_now  : current downstream water demand (m^3/s)
    d_mean : long-term mean downstream water demand (m^3/s)
    """
    # Case 1 (Eq. 1, top): demand is LARGE relative to inflow
    # -> release half the mean inflow as a base, scaled by relative demand.
    if d_mean >= 0.5 * i_mean:
        return (i_mean / 2.0) * (1.0 + d_now / d_mean)
    # Case 2 (Eq. 1, bottom): demand is SMALL relative to inflow
    # -> release the mean inflow, shifted by the demand anomaly.
    return i_mean + d_now - d_mean


def hanasaki_final_release(provisional: float, i_now: float,
                           gamma: float, k_rls: float) -> float:
    """Adjust a provisional release for the degree of regulation (Eqs. 2 & 4).

    The idea: a LARGE reservoir (gamma >= 0.5) can fully smooth the flow, so
    it releases the provisional value scaled by how full it currently is
    (k_rls). A SMALL reservoir cannot store much, so its release is a blend
    between the smoothed value and today's actual inflow.

    Parameters
    ----------
    provisional : R'_m,y from Eq. 1 (irrigation) or i_mean (flood control)
    i_now       : current inflow i_m,y (m^3/s)
    gamma       : degree of regulation C / I_mean (dimensionless)
    k_rls       : release coefficient S_first,y / (alpha * C)
    """
    # Hydrologically LARGE reservoir: full smoothing.
    if gamma >= 0.5:
        return k_rls * provisional
    # Hydrologically SMALL reservoir: blend. The weight (gamma/0.5)^2 grows
    # from 0 (tiny reservoir -> release = inflow) to 1 (at gamma = 0.5).
    ratio = (gamma / 0.5) ** 2
    return ratio * k_rls * provisional + (1.0 - ratio) * i_now


# ===========================================================================
# SECTION 2 - HYDROPOWER RESERVOIRS (Sect. 2.3.2)
# ===========================================================================
# Hydropower is different: instead of a formula, the paper builds a POLICY
# TABLE offline ("if storage is X in month M, release Y"), chosen so that
# long-term power production is maximized. Power = eta * rho*g * R * H, so
# maximizing power means maximizing release * head.
#
# The table is found by BACKWARD-RECURSIVE DYNAMIC PROGRAMMING (DP):
# starting from December and stepping backwards, we ask at every storage
# level "which release gives the best power NOW plus the best expected
# power LATER?" - sweeping the 12-month cycle until the answer stabilizes.

@dataclass
class HydropowerSDP:
    """Energy-maximizing monthly release policy via backward-recursive DP.

    Discretization follows the paper: 10 release increments x 1000 storage
    levels x 12 months; a wedge-shaped reservoir converts storage to head;
    inflow uncertainty enters as the average over the historical inflows
    observed in each calendar month.

    Parameters
    ----------
    capacity_m3   : usable storage capacity alpha*C (m^3)
    q_max         : maximum turbine flow (m^3/s)
    installed_kw  : plant installed capacity (kW)
    dam_height_m  : dam height = maximum storage depth (m)
    efficiency    : turbine efficiency eta (0.9 in the paper)
    """

    capacity_m3: float
    q_max: float
    installed_kw: float
    dam_height_m: float
    efficiency: float = 0.9
    n_storage: int = 1000          # storage levels in the table
    n_release: int = 10            # release increments in the table
    # internal results, filled in by fit(): the policy table and its axis
    _policy: np.ndarray = field(default=None, repr=False)       # (12, n_storage) m^3/s
    _storage_grid: np.ndarray = field(default=None, repr=False)

    RHO_G = 9.81  # specific weight of water (kN/m^3): P[kW] = eta*rho_g*Q*H

    # ------------------------------------------------------------------
    def head(self, storage_m3: np.ndarray) -> np.ndarray:
        """Turbine head (m) as a function of storage, for a wedge reservoir.

        Geometry: for a wedge-shaped reservoir the water DEPTH grows with
        the square root of the stored VOLUME:  y = H_dam * sqrt(V / C).
        The turbine head = depth above the intake + fixed intake elevation.
        The intake elevation itself is backed out from the power equation
        at installed capacity (H_max = P / (eta * rho_g * q_max)).
        """
        # maximum head the plant was designed for (from the power equation)
        h_max = self.installed_kw / (self.efficiency * self.RHO_G * self.q_max)
        # elevation of the intake above the turbine (fixed part of the head)
        intake = h_max - self.dam_height_m
        # water depth above the intake (varies with storage; clip guards
        # against tiny negative storages from floating-point arithmetic)
        depth = self.dam_height_m * np.sqrt(np.clip(storage_m3, 0.0, None)
                                            / self.capacity_m3)
        return intake + depth

    # ------------------------------------------------------------------
    def fit(self, monthly_inflows: pd.Series, n_cycles: int = 30) -> "HydropowerSDP":
        """Build the 12 x n_storage release-policy table.

        Parameters
        ----------
        monthly_inflows : Series of monthly mean inflow (m^3/s) indexed by
                          month timestamps, spanning several years. These are
                          the "scenarios" the DP averages over.
        n_cycles        : how many times to sweep the 12-month cycle
                          backwards (enough for the table to converge).
        """
        # --- set up the discretized state (storage) and decision (release) axes
        s_grid = np.linspace(0.0, self.capacity_m3, self.n_storage)
        r_grid = np.linspace(0.0, self.q_max, self.n_release + 1)
        sec_month = DAYS_PER_YEAR / 12.0 * SECONDS_PER_DAY  # seconds per month
        head_now = self.head(s_grid)                        # head at each storage level

        # --- group the historical inflows by calendar month --------------
        months = monthly_inflows.index.month
        inflow_by_month = {
            m: monthly_inflows.values[months == m] for m in range(1, 13)
        }

        # --- OPTIMIZATION: precompute, once per (month, release, inflow), --
        # the immediate power benefit and the resulting next storage. These
        # never change between DP sweeps; only the "future value" curve does,
        # so recomputing them inside the sweep loop (as a naive DP would)
        # wastes ~n_cycles x the work.
        #
        # precomp[month] is a list with one entry per candidate release:
        #     (release, [(benefit array, next-storage array), one per inflow])
        precomp = {}
        for m in range(1, 13):
            inflows = inflow_by_month[m]
            inflows = inflows[~np.isnan(inflows)]           # drop missing months
            per_release = []
            for r in r_grid:
                scenarios = []
                for i in inflows:
                    # water available this month limits the actual release
                    avail = s_grid / sec_month + i
                    r_act = np.minimum(r, avail)
                    # mass balance to next month's storage (spill is clipped
                    # off at capacity and earns no power)
                    s_next = np.clip(s_grid + (i - r_act) * sec_month,
                                     0.0, self.capacity_m3)
                    # power produced this month at each storage level
                    benefit = self.efficiency * self.RHO_G * r_act * head_now
                    scenarios.append((benefit, s_next))
                per_release.append((r, scenarios))
            precomp[m] = per_release if len(inflows) else []

        # --- the backward recursion ---------------------------------------
        future = np.zeros(self.n_storage)          # value of ending at each storage
        policy = np.zeros((12, self.n_storage))    # best release per (month, storage)

        for sweep in range(n_cycles * 12):
            m = 12 - (sweep % 12)                  # December -> January, repeated
            if not precomp[m]:
                continue                            # no inflow data for this month
            best_val = np.full(self.n_storage, -np.inf)
            best_rel = np.zeros(self.n_storage)
            # evaluate each candidate release: its value = average over the
            # inflow scenarios of (power now + best value of what follows)
            for r, scenarios in precomp[m]:
                value = np.zeros(self.n_storage)
                for benefit, s_next in scenarios:
                    # np.interp reads the future-value curve at next storage
                    value += benefit + np.interp(s_next, s_grid, future)
                value /= len(scenarios)            # average over scenarios
                better = value > best_val          # keep this release where it wins
                best_val[better] = value[better]
                best_rel[better] = r
            future = best_val                      # becomes "later" for month m-1
            policy[m - 1] = best_rel

        # paper rule: at full pool always release the maximum turbine flow
        policy[:, -1] = self.q_max
        self._policy = policy
        self._storage_grid = s_grid
        return self

    # ------------------------------------------------------------------
    def release(self, storage_m3: float, month: int) -> float:
        """Look up the optimal release (m^3/s) for a storage level and month."""
        if self._policy is None:
            raise RuntimeError("call fit() before release()")
        # find the storage grid cell we are in (clipped to the table edges)
        idx = int(np.clip(np.searchsorted(self._storage_grid, storage_m3),
                          0, self.n_storage - 1))
        return float(self._policy[month - 1, idx])


# ===========================================================================
# SECTION 3 - THE POLICY OBJECT THE SIMULATION DRIVER TALKS TO
# ===========================================================================
# reservoir_model.py never calls the equations above directly. It builds ONE
# BenchmarkPolicy per reservoir and calls target_release() once per simulation
# step.
# This class precomputes the long-term statistics the equations need and
# routes each daily decision to the right rule for the reservoir's purpose.

@dataclass
class BenchmarkPolicy:
    """Release decisions per Abeshu et al. (2023) for one reservoir.

    Parameters
    ----------
    purpose      : 'irrigation', 'hydropower', 'flood_control', or 'other'
    capacity_m3  : total storage capacity C (m^3)
    inflow       : full daily or monthly inflow series (m^3/s), matching the
                   requested simulation timestep; used only for long-term
                   statistics (mean inflow and seasonality)
    alpha        : capacity reduction factor (the paper fixes 0.85)
    demand       : daily downstream demand series (m^3/s); irrigation only
    hydropower   : a fitted HydropowerSDP instance; hydropower only
    """

    purpose: str
    capacity_m3: float
    inflow: pd.Series
    alpha: float = 0.85
    demand: pd.Series = None
    hydropower: HydropowerSDP = None

    # ------------------------------------------------------------------
    def __post_init__(self):
        """Precompute every long-term statistic the release rules will need."""
        # mean annual inflow i_mean (m^3/s) - the anchor of all the rules
        self.i_mean = float(self.inflow.mean())
        # mean annual inflow VOLUME (m^3/yr), to compare with capacity
        annual_volume = self.i_mean * SECONDS_PER_DAY * DAYS_PER_YEAR
        # degree of regulation: how many years of inflow the reservoir holds
        self.gamma = self.capacity_m3 / annual_volume
        # environmental floor: never release less than 10% of mean inflow
        self.env_flow = 0.1 * self.i_mean
        # mean demand (irrigation rule only; 0 when no demand is supplied)
        self.d_mean = float(self.demand.mean()) if self.demand is not None else 0.0
        # month in which the "operational year" begins (see helper below)
        self.op_year_start_month = self._op_year_start_month()
        # k_rls is (re)set on the first call and at each operational new year
        self.k_rls = None

    # ------------------------------------------------------------------
    def _op_year_start_month(self) -> int:
        """First month whose typical inflow drops below the annual mean.

        Hanasaki et al. (2006) start the "operational year" when the wet
        season ends, i.e. the first calendar month whose climatological mean
        inflow falls below the annual mean while the previous month was
        above it. If no such transition exists we fall back to October
        (the standard US water-year start).
        """
        clim = self.inflow.groupby(self.inflow.index.month).mean()
        for m in range(1, 13):
            prev = clim.get(12 if m == 1 else m - 1, np.nan)   # previous month
            if prev >= self.i_mean and clim.get(m, np.nan) < self.i_mean:
                return m
        return 10  # fallback: start of the US water year

    # ------------------------------------------------------------------
    def target_release(self, date: pd.Timestamp, inflow_now: float,
                       storage_start_m3: float) -> float:
        """Rule-based target release (m^3/s) for one decision interval.

        NOTE: this is the rule's WISH. Physical feasibility (enough water in
        storage, spill above capacity) is enforced by reservoir_model.py.
        """
        # (1) refresh k_rls once per operational year: it is the fraction of
        #     usable capacity that is full at the START of the year, and it
        #     scales this year's releases up (full) or down (empty).
        if self.k_rls is None or (date.month == self.op_year_start_month
                                  and date.day == 1):
            self.k_rls = storage_start_m3 / (self.alpha * self.capacity_m3)

        # (2) route to the rule for this reservoir's purpose
        if self.purpose == "irrigation":
            # today's demand (fall back to the mean when no series given)
            d_now = (float(self.demand.get(date, self.d_mean))
                     if self.demand is not None else 0.0)
            provisional = irrigation_provisional_release(self.i_mean, d_now,
                                                         self.d_mean)
            release = hanasaki_final_release(provisional, inflow_now,
                                             self.gamma, self.k_rls)
        elif self.purpose == "hydropower":
            # simple table lookup in the pre-fitted DP policy
            release = self.hydropower.release(storage_start_m3, date.month)
        elif self.purpose in ("flood_control", "other"):
            # Eq. 4: same shape as Eq. 2 but the "provisional" is i_mean
            release = hanasaki_final_release(self.i_mean, inflow_now,
                                             self.gamma, self.k_rls)
        else:
            raise ValueError(f"unknown reservoir purpose: {self.purpose!r}")

        # (3) apply the environmental-flow floor (paper Sect. 2.3): if the
        #     rule produced nothing usable or less than 10% of mean annual
        #     inflow, release that 10% instead.
        if not np.isfinite(release) or release < self.env_flow:
            release = self.env_flow
        return release
