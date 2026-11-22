# GWLF module.
# by Chung-Yi Lin @ Lehigh University (philip928lin@gmail.com)
# Last update at 2021/12/22.

import numpy as np
from pandas import date_range, to_datetime, DataFrame


def run_GWLF(pars, inputs, temp, prec, pet, monthly_Tavg, vars=None, **kwargs):
    """GWLF rainfall-runoff model.

    Inputs:
        Area:     [ha] Subbasin area.
        Latitude: [deg]
        S0:       [cm] Shallow saturated soil water content. E.g., 10
        U0:       [cm] Unsaturated soil water content. E.g., 10
        SnowS:    [cm] Snow storage. E.g., 5

    Pars:
        CN2:   Curve number.
        IS:    Interception coefficient.
        Res:   Recession coefficient.
        Sep:   Deep seepage coefficient.
        Alpha: Baseflow coefficient.
        Beta:  Percolation coefficient.
        Ur:    [cm] Available/Soil water capacity.
        Kc:    Land cover coefficient.
        Df:    [cm/degC] Degree-day coefficient.
    Note that the simulation period has to be longer than a month.

    Parameters
    ----------
    pars : dict
        Parameter dictionary containing 9 parameters: CN2, IS, Res, Sep, Alpha,
        Beta, Ur, Kc, Df.
    inputs : dict
        Input dictionary containing 5 inputs: Area, Latitude, S0, U0, SnowS.
    temp : array
        [degC] Daily mean temperature.
    prec : array
        [cm] Daily precipitation.
    pet : array
        [cm] Daily potential evaportranspiration.
    monthly_Tavg: str
        Monthly average temperature in a daily format.
    vars : int, optional
        Initial values.

    Returns
    -------
    array
        [cms] Discharge
    """
    # ----- Setup  -------------------------------------------------------------
    diagnostics = kwargs.get("diagnostics")
    if diagnostics is not None and not isinstance(diagnostics, list):
        raise ValueError("diagnostics must be a list or None")
    records = []
    sim_length = len(prec)
    # Pars
    CN2 = pars["CN2"]  # Curve number
    IS = pars["IS"]  # Interception coefficient 0.05 ~ 0.2
    Res = pars["Res"]  # Recession coefficient
    Sep = pars["Sep"]  # Deep seepage coefficient
    Alpha = pars["Alpha"]  # Baseflow coefficient
    ##(Eq 4 in Luo et al. (2012))
    Beta = pars["Beta"]  # Deep seepage coefficient
    ##(Eq 2 in Luo et al. (2012))
    Ur = pars["Ur"]  # [cm] Avaliable/Soil water capacity
    ##(Root zone)
    Df = pars["Df"]  # [cm/degC] Degree-day coefficient for snowmelt.
    Kc = pars["Kc"]  # Land cover coefficient.

    # Variables
    if vars is None:
        BFt = Res * inputs["S0"]  # [cm] Initialize baseflow to stream.
        ## = Gt =  Res*inputs["S0"]
        St = inputs["S0"]  # [cm] Initialize shallow saturated soil water
        ##content.
        Ut = inputs["U0"]  # [cm] Initialize unsaturated soil water
        ##content.
        SnowSt = inputs["SnowS"]  # [cm] Initial snow storage.
        AnteMois = [0, 0, 0, 0, 0]  # [cm] Define the initial Antecedent Moisture
        ##(5 days) as 0.
    else:
        BFt = vars["BFt"]
        St = vars["St"]
        Ut = vars["Ut"]
        SnowSt = vars["SnowSt"]
        AnteMois = vars["AnteMois"]
    if vars is None and ("B0" in inputs or "BF0" in inputs):
        from .groundwater import initialize_groundwater
        BFt = initialize_groundwater(pars, inputs, scale="daily")["daily_baseflow_cm_per_day"]
    if diagnostics is not None:
        from .groundwater import daily_baseflow_to_storage, initialize_groundwater, validate_daily_diagnostics
        validate_daily_diagnostics(pars, inputs,
            dict(temp=temp, prec=prec, pet=pet, monthly_Tavg=monthly_Tavg),
            dict(BFt=BFt, St=St, Ut=Ut, SnowSt=SnowSt))
        if vars is None:
            initialize_groundwater(pars, inputs, scale="daily")
        elif not np.isfinite(Alpha) or Alpha < 0:
            raise ValueError("diagnostic Alpha must be finite and nonnegative")
    # --------------------------------------------------------------------------

    # ----- Loop through all days (Python for loop ending needs +1) ------------
    CMS = np.empty(sim_length)  # Create a 1D array to store results
    for i in range(sim_length):
        if diagnostics is not None:
            start_u, start_s, start_snow = Ut, St, SnowSt
            start_b = daily_baseflow_to_storage(BFt, Alpha) if Alpha > 0 else None
        # Determine the am1 and am2 values based on growing season for CN
        # calculation. Growing season (mean monthly temperature > 10 deg C).
        if monthly_Tavg[i] > 10:  # monthly_Tavg in a daily format
            am1 = 3.6
            am2 = 5.3
        else:
            am1 = 1.3
            am2 = 2.8

        # Determine rainfall, snowfall and snow accumulation-------------------
        if temp[i] > 0:  # If temperature is above 0 degC,
            Rt = prec[i]  # precipitation is rainfall (cm) and no snow
            ##accumulation
        else:
            Rt = 0  # Else, precipitation is snowfall (cm) so rainfall = 0
            # Snowfall will accumulated and become snow storage(cm)
            SnowSt = SnowSt + prec[i]
        # ----------------------------------------------------------------------
        # Determine snowmelt (Degree-day method)-------------------------------
        if temp[i] > 0:  # Temperature above 0 degC
            # Snowmelt (cm) capped by snow storage
            Mt = min(SnowSt, Df * temp[i])
            SnowSt = SnowSt - Mt  # Update snow storage
        else:
            Mt = 0
        # ----------------------------------------------------------------------
        # Calculate the Antecedent Moisture (at)-------------------------------
        AnteMois = [Rt + Mt] + AnteMois[0:4]  # Add new data and drop last data.
        at = np.sum(AnteMois)  # Five days antecedent moisture
        # ----------------------------------------------------------------------
        # CN calculation (Following GWLF2 setting)-----------------------------
        CN1 = (4.2 * CN2) / (10 - 0.058 * CN2)
        CN3 = (23 * CN2) / (10 + 0.13 * CN2)
        CN = None
        if at < am1:
            CN = CN1 + ((CN2 - CN1) / am1) * at

        if am1 <= at and at <= am2:
            CN = CN2 + ((CN3 - CN2) / (am2 - am1)) * (at - am1)

        if am2 < at:
            CN = CN3
        # ----------------------------------------------------------------------
        # Calculate runoff (Qt)------------------------------------------------
        DSkt = (2540 / CN) - 25.4  # Detention parameter (cm)
        if (Rt + Mt) > IS * DSkt:
            Qt = (((Rt + Mt) - (IS * DSkt)) ** 2) / ((Rt + Mt) + ((1 - IS) * DSkt))
        else:
            Qt = 0
        # ----------------------------------------------------------------------
        # Calculate Evapotranspiration (Et)------------------------------------
        # Consider water stress (Ks) and land cover (Kc).
        if Ut >= Ur * 0.5:
            Ks = 1
        else:
            Ks = Ut / (Ur * 0.5)
        Et = min((Ut + Rt + Mt - Qt), Ks * Kc * pet[i])
        # ----------------------------------------------------------------------
        # Calculate Percolation (Pct) from unsaturated zone (Ut) to shallow
        # saturated zone (St)--------------------------------------------------
        PCt = max((Ut + Rt + Mt - Qt - Et - Ur), 0)
        # ----------------------------------------------------------------------
        # Update unsaturated zone soil moistures (Ut)--------------------------
        Ut = Ut + Rt + Mt - Qt - Et - PCt  # Rt+Mt-Qt is infiltration
        # ----------------------------------------------------------------------
        # Calculate groundwater discharge (Gt) and deep seepage (Dt)-----------
        Gt = Res * St
        Dt = Sep * St
        # ----------------------------------------------------------------------
        # Update shallow saturated zone soil moistures (St)--------------------
        St = St + PCt - Gt - Dt
        # ----------------------------------------------------------------------
        # Groundwater: Deep seepage loss (Dset)--------------------------------
        Dset = Beta * Dt  # Eq 2 in Luo et al. (2012)
        # ----------------------------------------------------------------------
        # Groundwater: Recharge (Ret)------------------------------------------
        Ret = Dt - Dset  # Eq 3 in Luo et al. (2012)
        # ----------------------------------------------------------------------
        # Groundwater:Baseflow (BFt)-------------------------------------------
        # Eq 4 in Luo et al. (2012)
        BFt = BFt * np.exp(-Alpha) + Ret * (1 - np.exp(-Alpha))
        # ----------------------------------------------------------------------
        # Calculate streamflow (SF) and Monthly Qt, prec, Et, Gt and SF--------
        # Streamflow = surface quick flow + subsurface flow + baseflow
        SF = Qt + Gt + BFt
        # ----------------------------------------------------------------------
        # Change unit to cms (m^3/sec)-----------------------------------------
        # Area [ha]
        CMS[i] = (SF * 0.01 * inputs["Area"] * 10000) / 86400
        if diagnostics is not None:
            end_b = daily_baseflow_to_storage(BFt, Alpha) if Alpha > 0 else None
            status = "COMPUTABLE" if start_b is not None else "UNAVAILABLE_ZERO_ALPHA"
            total_start = float(start_u + start_s + start_b + start_snow) if start_b is not None else None
            total_end = float(Ut + St + end_b + SnowSt) if end_b is not None else None
            residual = (total_start + prec[i] - total_end - SF - Et - Dset) * inputs["Area"] * 100 if total_start is not None else None
            records.append(dict(
                step=i, dt_seconds=86400, precipitation_cm=float(prec[i]),
                rain_cm=float(Rt), melt_cm=float(Mt), quickflow_cm=float(Qt),
                shallow_flow_cm=float(Gt), seepage_cm=float(Dt),
                baseflow_cm=float(BFt), deep_recharge_cm=float(Ret),
                actual_et_cm=float(Et), deep_loss_cm=float(Dset), percolation_cm=float(PCt),
                U_start_cm=float(start_u), U_end_cm=float(Ut),
                S_start_cm=float(start_s), S_end_cm=float(St),
                B_start_cm=start_b, B_end_cm=end_b,
                snow_start_cm=float(start_snow), snow_end_cm=float(SnowSt),
                storage_start_cm=total_start, storage_end_cm=total_end,
                mass_balance_residual_m3=float(residual) if residual is not None else None,
                mass_balance_status=status, cn=float(CN), initial_abstraction_cm=float(IS * DSkt),
            ))
        # ----------------------------------------------------------------------
    # return the result array
    vars = {"BFt": BFt, "St": St, "Ut": Ut, "SnowSt": SnowSt, "AnteMois": AnteMois}
    if diagnostics is not None:
        diagnostics.extend(records)
    return CMS, vars


# def run_GWLF(pars, inputs, temp, prec, pet, start_date, data_length, **kwargs):
#     """GWLF rainfall-runoff model.

#     Inputs:
#         Area:     [ha] Subbasin area.
#         Latitude: [deg]
#         S0:       [cm] Shallow saturated soil water content.
#         U0:       [cm] Unsaturated soil water content.
#         SnowS:    [cm] Snow storage.

#     Pars:
#         CN2:   Curve number.
#         IS:    Interception coefficient.
#         Res:   Recession coefficient.
#         Sep:   Deep seepage coefficient.
#         Alpha: Baseflow coefficient.
#         Beta:  Percolation coefficient.
#         Ur:    [cm] Available/Soil water capacity.
#         Kc:    Land cover coefficient.
#         Df:    [cm/degC] Degree-day coefficient.
#     Note that the simulation period has to be longer than a month.

#     Parameters
#     ----------
#     pars : dict
#         Parameter dictionary containing 9 parameters: CN2, IS, Res, Sep, Alpha,
#         Beta, Ur, Kc, Df.
#     inputs : dict
#         Input dictionary containing 5 inputs: Area, Latitude, S0, U0, SnowS.
#     temp : array
#         [degC] Daily mean temperature.
#     prec : array
#         [cm] Daily precipitation.
#     pet : array
#         [cm] Daily potential evaportranspiration.
#     start_date: str
#         Start date "yyyy/mm/dd".

#     data_length : int
#         Total data length (i.e., simulation period).

#     Returns
#     -------
#     array
#         [cms] Discharge
#     """
#     #----- Setup  -------------------------------------------------------------

#     r"""
#     Inputs:
#         Area:                   # [ha] Sub-basin area.
#         S0:     10              # [cm] Shallow saturated soil water content.
#         U0:     10              # [cm] Unsaturated soil water content
#         SnowS:  5               # [cm] Snow storage.
#     """

#     # Data
#     temp = np.array(temp)           # [degC] Daily mean temperature.
#     prec = np.array(prec)           # [cm] Daily precipitation.
#     pet = np.array(pet)         # [cm] Daily potential evapotranspiration.

#     # Pars
#     CN2 = pars["CN2"]     # Curve number
#     IS = pars["IS"]       # Interception coefficient 0.05 ~ 0.2
#     Res = pars["Res"]     # Recession coefficient
#     Sep = pars["Sep"]     # Deep seepage coefficient
#     Alpha = pars["Alpha"] # Baseflow coefficient
#                                ##(Eq 4 in Luo et al. (2012))
#     Beta = pars["Beta"]   # Deep seepage coefficient
#                                ##(Eq 2 in Luo et al. (2012))
#     Ur = pars["Ur"]       # [cm] Avaliable/Soil water capacity
#                                ##(Root zone)
#     Df = pars["Df"]       # [cm/degC] Degree-day coefficient for snowmelt.
#     Kc = pars["Kc"]       # Land cover coefficient.

#     # Variables
#     Gt =  Res*inputs["S0"]      # [cm] Initialize saturated zone discharge to
#                                 ##the stream.
#     BFt = Gt					# [cm] Initialize baseflow to stream.
#     St = inputs["S0"]           # [cm] Initialize shallow saturated soil water
#                                 ##content.
#     Ut = inputs["U0"]           # [cm] Initialize unsaturated soil water
#                                 ##content.
#     SnowSt = inputs["SnowS"]    # [cm] Initial snow storage.
#     AnteMois = [0, 0, 0, 0, 0]  # [cm] Define the initial Antecedent Moisture
#                                 ##(5 days) as 0.

#     # Calculate monthly mean temperature for distinguishing growing season
#     # purpose.
#     start_date = to_datetime(start_date, format="%Y/%m/%d")
#     pdDatedateIndex = date_range(start=start_date, periods=data_length,
#                                  freq="D")
#     MonthlyTavg = DataFrame(index=pdDatedateIndex)
#     MonthlyTavg["T"] = temp
#     MonthlyTavg = MonthlyTavg.resample("MS").mean()
#     # Broadcast back to daily sequence.
#     # Note: Data has to longer than a month or it will show error.
#     try:
#         MonthlyTavg.index = [pdDatedateIndex[0]] + list(MonthlyTavg.index[1:-1]) \
#                             + [pdDatedateIndex[-1]]
#         MonthlyTavg = MonthlyTavg.resample('D').ffill()["T"].to_numpy()
#     except Exception as e:
#         print(e)
#         print("The simulation period has to be longer than a month.")
#     #--------------------------------------------------------------------------

#     #----- Loop through all days (Python for loop ending needs +1) ------------
#     CMS = np.zeros(data_length) # Create a 1D array to store results
#     for i in range(data_length):
#         # Determine the am1 and am2 values based on growing season for CN
#         # calculation.
#         # Growing season (mean monthly temperature > 10 deg C).
#         if MonthlyTavg[i] > 10:     # MonthlyTavg
#             am1 = 3.6
#             am2 = 5.3
#         else:
#             am1 = 1.3
#             am2 = 2.8

#         # Determine rainfall, snowfall and snow accumulation-------------------
#         if temp[i] > 0:           # If temperature is above 0 degC,
#             Rt = prec[i]          # precipitation is rainfall (cm) and no snow
#                                   ##accumulation
#         else:
#             Rt = 0      # Else, precipitation is snowfall (cm) so rainfall = 0
#             # Snowfall will accumulated and become snow storage(cm)
#             SnowSt = SnowSt + prec[i]
#         #----------------------------------------------------------------------
#         # Determine snowmelt (Degree-day method)-------------------------------
#         if temp[i] > 0:           # Temperature above 0 degC
#             # Snowmelt (cm) capped by snow storage
#             Mt = min(SnowSt, Df * temp[i])
#             SnowSt = SnowSt - Mt  # Update snow storage
#         else:
#             Mt = 0
#         #----------------------------------------------------------------------
#         # Calculate the Antecedent Moisture (at)-------------------------------
#         AnteMois = [Rt + Mt] + AnteMois[0:4] # Add new data and drop last data.
#         at = np.sum(AnteMois)                # Five days antecedent moisture
#         #----------------------------------------------------------------------
#         # CN calculation (Following GWLF2 setting)-----------------------------
#         CN1 = (4.2 * CN2) / (10 - 0.058 * CN2)
#         CN3 = (23 * CN2) / (10 + 0.13 * CN2)
#         CN = None
#         if at < am1:
#             CN = CN1 + ((CN2 - CN1) / am1) * at

#         if (am1 <= at and at <= am2):
#             CN = CN2 + ((CN3 - CN2) / (am2 - am1)) * (at - am1)

#         if am2 < at:
#             CN = CN3
#         #----------------------------------------------------------------------
#         # Calculate runoff (Qt)------------------------------------------------
#         DSkt = (2540 / CN) - 25.4               # Detention parameter (cm)
#         if (Rt + Mt) > IS * DSkt:
#             Qt = (((Rt + Mt) - (IS * DSkt))**2) / ((Rt + Mt) + ((1-IS) * DSkt))
#         else:
#             Qt = 0
#         #----------------------------------------------------------------------
#         # Calculate Evapotranspiration (Et)------------------------------------
#         # Consider water stress (Ks) and land cover (Kc).
#         if (Ut >= Ur*0.5):
#             Ks = 1
#         else:
#             Ks = Ut/(Ur*0.5)
#         Et = min((Ut+ Rt + Mt - Qt), Ks*Kc*pet[i])
#         #----------------------------------------------------------------------
#         # Calculate Percolation (Pct) from unsaturated zone (Ut) to shallow
#         # saturated zone (St)--------------------------------------------------
#         PCt = max((Ut+ Rt + Mt - Qt - Et - Ur), 0)
#         #----------------------------------------------------------------------
#         # Update unsaturated zone soil moistures (Ut)--------------------------
#         Ut = Ut + Rt + Mt - Qt - Et - PCt       # Rt+Mt-Qt is infiltration
#         #----------------------------------------------------------------------
#         # Calculate groundwater discharge (Gt) and deep seepage (Dt)-----------
#         Gt = Res * St
#         Dt = Sep * St
#         #----------------------------------------------------------------------
#         # Update shallow saturated zone soil moistures (St)--------------------
#         St = St + PCt - Gt - Dt
#         #----------------------------------------------------------------------
#         # Groundwater: Deep seepage loss (Dset)--------------------------------
#         Dset = Beta * Dt    #Eq 2 in Luo et al. (2012)
#         #----------------------------------------------------------------------
#         # Groundwater: Recharge (Ret)------------------------------------------
#         Ret = Dt - Dset     #Eq 3 in Luo et al. (2012)
#         #----------------------------------------------------------------------
#         # Groundwater:Baseflow (BFt)-------------------------------------------
#         # Eq 4 in Luo et al. (2012)
#         BFt = BFt * np.exp(-Alpha) + Ret * (1-np.exp(-Alpha))
#         #----------------------------------------------------------------------
#         # Calculate streamflow (SF) and Monthly Qt, prec, Et, Gt and SF--------
#         # Streamflow = surface quick flow + subsurface flow + baseflow
#         SF = Qt + Gt + BFt
#         #----------------------------------------------------------------------
#         # Change unit to cms (m^3/sec)-----------------------------------------
#         # Area [ha]
#         CMS[i] = (SF * 0.01 * inputs["Area"] * 10000) / 86400
#         #----------------------------------------------------------------------
#     # return the result array
#     return CMS
