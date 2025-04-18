import numpy as np
import sys
import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import time
import os 
import matplotlib.pyplot as plt
import platform
#import psutil
from pyomo.environ import *

##################################################################################
############################### READING EXCEL FILE ###############################
##################################################################################

# Function to read all sheets in an Excel file and save each as a .tab file in the current directory
def read_all_sheets(excel):
    # Load the Excel file
    input_excel = pd.ExcelFile(excel)
    
    # Loop over each sheet in the workbook
    for sheet in input_excel.sheet_names:
        # Read the current sheet, skipping the first two rows
        input_sheet = pd.read_excel(excel, sheet_name=sheet, skiprows=2)

        # Drop only fully empty rows (optional)
        data_nonempty = input_sheet.dropna(how='all')

        # Replace spaces in column names with underscores
        data_nonempty.columns = data_nonempty.columns.astype(str).str.replace(' ', '_')

        # Fill missing values with an empty string
        data_nonempty = data_nonempty.fillna('')

        # Convert all columns to strings before replacing whitespace characters in values
        data_nonempty = data_nonempty.applymap(lambda x: str(x) if pd.notnull(x) else "")
        
        # Save as a .tab file using only the sheet name as the file namec
        output_filename = f"{sheet}.tab"
        data_nonempty.to_csv(output_filename, header=True, index=False, sep='\t')
        print(f"Saved file: {output_filename}")

# Call the function with your Excel file
read_all_sheets('Test_data_simple_extended_reduced.xlsx')

####################################################################
######################### MODEL SPECIFICATIONS #####################
####################################################################

model = pyo.AbstractModel()
data = pyo.DataPortal() #Loading the data from a data soruce in a uniform manner (Excel)


"""
SETS 
"""
#Declaring Sets

print("Declaring sets...")

model.Time = pyo.Set(ordered=True) #Set of time periods (hours)
model.Period = pyo.Set(ordered=True) #Set of stages/operational periods
model.LoadShiftingPeriod = pyo.Set(ordered=True) 
#model.LoadShiftingIntervals = pyo.Set(ordered=True)
model.Time_NO_LoadShift = pyo.Set(dimen = 2, ordered = True) 
#model.TimeLoadShift = pyo.Set(dimen = 3, ordered = True) #Subset of time periods for load shifting in stage s
model.Month = pyo.Set(ordered = True) #Set of months
model.PeriodInMonth = pyo.Set(dimen = 2, ordered = True) #Subset of stages in month m
model.Technology = pyo.Set(ordered = True) #Set of technologies
model.EnergyCarrier = pyo.Set(ordered = True)
model.Mode_of_operation = pyo.Set(ordered = True)
model.TechnologyToEnergyCarrier = pyo.Set(dimen=3, ordered = True)
model.EnergyCarrierToTechnology = pyo.Set(dimen=3, ordered = True)
model.FlexibleLoad = pyo.Set(ordered=True) #Set of flexible loads (batteries)
model.FlexibleLoadForEnergyCarrier = pyo.Set(dimen = 2, ordered = True)
model.Nodes = pyo.Set(ordered=True) #Set of Nodess
model.Nodes_in_stage = pyo.Set(dimen = 2, ordered = True) #Subset of Nodess
model.Nodes_first = pyo.Set(within = model.Nodes) #Subset of Nodess
model.Parent = pyo.Set(ordered=True) #Set of parents
model.Parent_Node = pyo.Set(dimen = 2, ordered = True)


#Reading the Sets, and loading the data
print("Reading sets...")

data.load(filename="Set_of_TimeSteps.tab", format="set", set=model.Time)
data.load(filename="Set_of_Periods.tab", format="set", set=model.Period)
data.load(filename="Set_of_LoadShiftingPeriod.tab", format="set", set=model.LoadShiftingPeriod)
data.load(filename="Set_of_TimeSteps_NO_LoadShift.tab", format = "set", set=model.Time_NO_LoadShift)
data.load(filename="Set_of_Month.tab", format = "set", set=model.Month)
data.load(filename="Set_of_PeriodsInMonth.tab", format = "set", set=model.PeriodInMonth)
data.load(filename="Set_of_Technology.tab", format = "set", set=model.Technology)
data.load(filename="Set_of_EnergyCarrier.tab", format="set", set=model.EnergyCarrier)
data.load(filename="Set_Mode_of_Operation.tab", format = "set", set = model.Mode_of_operation)
data.load(filename="Subset_TechToEC.tab", format="set", set=model.TechnologyToEnergyCarrier)
data.load(filename="Subset_ECToTech.tab", format="set", set=model.EnergyCarrierToTechnology)
data.load(filename="Set_of_FlexibleLoad.tab", format="set", set=model.FlexibleLoad)
data.load(filename="Set_of_FlexibleLoadForEC.tab", format="set", set=model.FlexibleLoadForEnergyCarrier)
data.load(filename="Set_of_Nodes.tab", format="set", set=model.Nodes)
data.load(filename="Set_of_NodesInStage.tab", format="set", set=model.Nodes_in_stage)
data.load(filename="Subset_NodesFirst.tab", format="set", set=model.Nodes_first)
data.load(filename="Set_of_Parents.tab", format="set", set=model.Parent)
data.load(filename="Set_ParentCoupling.tab", format = "set", set = model.Parent_Node)


"""
PARAMETERS
"""
#Declaring Parameters
print("Declaring parameters...")

model.Cost_Energy = pyo.Param(model.Nodes, model.Time, model.Technology)  # Cost of using energy source i at time t
model.Cost_Battery = pyo.Param(model.FlexibleLoad)
model.Cost_Export = pyo.Param(model.Nodes, model.Time, model.Technology)  # Income from exporting energy to the grid at time t
model.Cost_Expansion_Tec = pyo.Param(model.Technology) #Capacity expansion cost
model.Cost_Expansion_Bat = pyo.Param(model.FlexibleLoad) #Capacity expansion cost
model.Cost_Emission = pyo.Param() #Carbon price
model.Cost_Grid = pyo.Param() #Grid tariff
model.aFRR_Up_Capacity_Price = pyo.Param(model.Nodes, model.Time)  # Capacity Price for aFRR up regulation 
model.aFRR_Dwn_Capacity_Price = pyo.Param(model.Nodes, model.Time)  # Capcaity Price for aFRR down regulation
model.aFRR_Up_Activation_Price = pyo.Param(model.Nodes, model.Time)  # Activation Price for aFRR up regulation 
model.aFRR_Dwn_Activation_Price = pyo.Param(model.Nodes, model.Time)  # Activatioin Price for aFRR down regulation 
model.Spot_Price = pyo.Param(model.Nodes, model.Time)
model.Intraday_Price = pyo.Param(model.Nodes, model.Time)
model.Demand = pyo.Param(model.Nodes, model.Time, model.EnergyCarrier)  # Energy demand 
model.Max_charge_discharge_rate = pyo.Param(model.FlexibleLoad, default = 1) # Maximum symmetric charge and discharge rate
model.Charge_Efficiency = pyo.Param(model.FlexibleLoad)  # Efficiency of charging flexible load b [-]
model.Discharge_Efficiency = pyo.Param(model.FlexibleLoad)  # Efficiency of discharging flexible load b [-]
model.Technology_To_EnergyCarrier_Efficiency = pyo.Param(model.TechnologyToEnergyCarrier) #Efficiency of technology i when supplying fuel e
model.EnergyCarrier_To_Technlogy_Efficiency = pyo.Param(model.EnergyCarrierToTechnology) #Efficiency of technology i when consuming fuel e
model.Max_Storage_Capacity = pyo.Param(model.FlexibleLoad)  # Maximum energy storage capacity of flexible load b [MWh]
model.Self_Discharge = pyo.Param(model.FlexibleLoad)  # Self-discharge rate of flexible load b [%]
model.Initial_SOC = pyo.Param(model.FlexibleLoad)  # Initial state of charge for flexible load b [-]
model.Node_Probability = pyo.Param(model.Nodes)  # Probability of Nodes s [-]
model.Up_Shift_Max = pyo.Param(model.Time)  # Maximum allowable up-shifting in load shifting periods as a percentage of demand [% of demand]
model.Down_Shift_Max = pyo.Param(model.Time)  # Maximum allowable down-shifting in load shifting periods as a percentage of demand [% of demand]
model.Initial_Installed_Capacity = pyo.Param(model.Technology) #Initial installed capacity at site for technology i
model.Ramping_Factor = pyo.Param(model.Technology)
model.Availability_Factor = pyo.Param(model.Nodes, model.Time, model.Technology) #Availability factor for technology delivering to energy carrier 
model.Carbon_Intensity = pyo.Param(model.Technology, model.Mode_of_operation) #Carbon intensity when using technology i in mode o
model.Max_Export = pyo.Param() #Maximum allowable export per year, if no concession is given
model.Activation_Factor_UP_Regulation = pyo.Param(model.Nodes, model.Time) # Activation factor determining the duration of up regulation
model.Activation_Factor_DWN_Regulation = pyo.Param(model.Nodes, model.Time) # Activation factor determining the duration of dwn regulation
model.Activation_Factor_ID_Up = pyo.Param(model.Nodes, model.Time) # Activation factor determining the duration of up regulation
model.Activation_Factor_ID_Dwn = pyo.Param(model.Nodes, model.Time) # Activation factor determining the duration of dwn regulation
model.Available_Excess_Heat = pyo.Param() #Fraction of the total available excess heat at usable temperature level to \\& be used an energy source for the heat pump.
model.Power2Energy_Ratio = pyo.Param(model.FlexibleLoad)
model.Max_CAPEX_tech = pyo.Param(model.Technology)
model.Max_CAPEX_flex = pyo.Param(model.FlexibleLoad)
model.Max_CAPEX = pyo.Param() #Maximum allowable CAPEX
model.Max_Carbon_Emission = pyo.Param() #Maximum allowable carbon emissions per year
model.Last_Period_In_Month = pyo.Param(model.Month) #Last period in month m
model.Cost_LS = pyo.Param(model.EnergyCarrier) #Cost of load shifting for energy carrier e
model.ID_Cap_Buy_volume = pyo.Param(model.Nodes, model.Time) #Volume of ID total bought in the market
model.ID_Cap_Sell_volume = pyo.Param(model.Nodes, model.Time) #Volume of ID total sold in the market
model.Res_Cap_Up_volume = pyo.Param(model.Nodes, model.Time) #Volume of total mFRR up shift in the market
model.Res_Cap_Down_volume = pyo.Param(model.Nodes, model.Time) #Volume of total mFRR down shift in the market

#Reading the Parameters, and loading the data
print("Reading parameters...")

data.load(filename="Par_EnergyCost.tab", param=model.Cost_Energy, format = "table")
data.load(filename="Par_BatteryCost.tab", param=model.Cost_Battery, format = "table")
data.load(filename="Par_ExportCost.tab", param=model.Cost_Export, format = "table")
data.load(filename="Par_CostExpansion_Tec.tab", param=model.Cost_Expansion_Tec, format = "table")
data.load(filename="Par_CostExpansion_Bat.tab", param=model.Cost_Expansion_Bat, format = "table")
data.load(filename="Par_CostEmission.tab", param=model.Cost_Emission, format = "table")
data.load(filename="Par_CostGridTariff.tab", param=model.Cost_Grid, format = "table")
data.load(filename="Par_aFRR_UP_CAP_price.tab", param=model.aFRR_Up_Capacity_Price, format = "table")
data.load(filename="Par_aFRR_DWN_CAP_price.tab", param=model.aFRR_Dwn_Capacity_Price, format = "table")
data.load(filename="Par_aFRR_UP_ACT_price.tab", param=model.aFRR_Up_Activation_Price, format = "table")
data.load(filename="Par_aFRR_DWN_ACT_price.tab", param=model.aFRR_Dwn_Activation_Price, format = "table")
data.load(filename="Par_SpotPrice.tab", param=model.Spot_Price, format = "table")
data.load(filename="Par_IntradayPrice.tab", param=model.Intraday_Price, format = "table")
data.load(filename="Par_EnergyDemand.tab", param=model.Demand, format = "table")
data.load(filename="Par_MaxChargeDischargeRate.tab", param=model.Max_charge_discharge_rate, format = "table")
data.load(filename="Par_ChargeEfficiency.tab", param=model.Charge_Efficiency, format = "table")
data.load(filename="Par_DischargeEfficiency.tab", param=model.Discharge_Efficiency, format = "table")
data.load(filename="Par_TechToEC_Efficiency.tab", param=model.Technology_To_EnergyCarrier_Efficiency, format = "table")
data.load(filename="Par_ECToTech_Efficiency.tab", param=model.EnergyCarrier_To_Technlogy_Efficiency, format = "table")
data.load(filename="Par_MaxStorageCapacity.tab", param=model.Max_Storage_Capacity, format = "table")
data.load(filename="Par_SelfDischarge.tab", param=model.Self_Discharge, format = "table")
data.load(filename="Par_InitialSoC.tab", param=model.Initial_SOC, format = "table")
data.load(filename="Par_NodesProbability.tab", param=model.Node_Probability, format = "table")
#data.load(filename="Par_MaxCableCapacity.tab", param=model.Max_Cable_Capacity, format = "table")
data.load(filename="Par_MaxUpShift.tab", param=model.Up_Shift_Max, format = "table")
data.load(filename="Par_MaxDwnShift.tab", param=model.Down_Shift_Max, format = "table")
data.load(filename="Par_InitialCapacityInstalled.tab", param=model.Initial_Installed_Capacity, format = "table")
data.load(filename="Par_AvailabilityFactor.tab", param=model.Availability_Factor, format = "table")
data.load(filename="Par_CarbonIntensity.tab", param=model.Carbon_Intensity, format = "table")
data.load(filename="Par_MaxExport.tab", param=model.Max_Export, format = "table")
data.load(filename="Par_ActivationFactor_Up_Reg.tab", param=model.Activation_Factor_UP_Regulation, format = "table")
data.load(filename="Par_ActivationFactor_Dwn_Reg.tab", param=model.Activation_Factor_DWN_Regulation, format = "table")
data.load(filename="Par_ActivationFactor_ID_Up_Reg.tab", param=model.Activation_Factor_ID_Up, format = "table")
data.load(filename="Par_ActivationFactor_ID_Dwn_Reg.tab", param=model.Activation_Factor_ID_Dwn, format = "table")
data.load(filename="Par_AvailableExcessHeat.tab", param=model.Available_Excess_Heat, format = "table")
data.load(filename="Par_Power2Energy_ratio.tab", param=model.Power2Energy_Ratio, format = "table")
data.load(filename="Par_Ramping_factor.tab", param=model.Ramping_Factor, format = "table")
data.load(filename="Par_Max_CAPEX_tec.tab", param=model.Max_CAPEX_tech, format = "table")
data.load(filename="Par_Max_CAPEX_bat.tab", param=model.Max_CAPEX_flex, format = "table")
data.load(filename="Par_Max_CAPEX.tab", param=model.Max_CAPEX, format = "table")
data.load(filename="Par_Max_Carbon_Emission.tab", param=model.Max_Carbon_Emission, format = "table")
data.load(filename="Par_LastPeriodInMonth.tab", param=model.Last_Period_In_Month, format = "table")
data.load(filename="Par_Cost_LS.tab", param=model.Cost_LS, format = "table")
data.load(filename="Par_ID_Capacity_Buy_Volume.tab", param=model.ID_Cap_Buy_volume, format = "table")
data.load(filename="Par_ID_Capacity_Sell_Volume.tab", param=model.ID_Cap_Sell_volume, format = "table")
data.load(filename="Par_Res_CapacityUpVolume.tab", param=model.Res_Cap_Up_volume, format = "table")
data.load(filename="Par_Res_CapacityDownVolume.tab", param=model.Res_Cap_Down_volume, format = "table")


"""
VARIABLES
"""
#Declaring Variables
model.x_UP = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)#, bounds = (0,0))
model.x_DWN = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)#, bounds = (0,0))
model.x_DA_Up = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)
model.x_DA_Dwn = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)
model.x_ID_Up = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)
model.x_ID_Dwn = pyo.Var(model.Nodes, model.Time, domain= pyo.NonNegativeReals)
model.y_out = pyo.Var(model.Nodes, model.Time, model.TechnologyToEnergyCarrier, domain = pyo.NonNegativeReals)
model.y_in = pyo.Var(model.Nodes, model.Time, model.EnergyCarrierToTechnology, domain = pyo.NonNegativeReals)
model.y_activity = pyo.Var(model.Nodes, model.Time, model.Technology, model.Mode_of_operation, domain = pyo.NonNegativeReals)
model.q_charge = pyo.Var(model.Nodes, model.Time, model.FlexibleLoad, domain= pyo.NonNegativeReals)
model.q_discharge = pyo.Var(model.Nodes, model.Time, model.FlexibleLoad, domain= pyo.NonNegativeReals)
model.q_SoC = pyo.Var(model.Nodes, model.Time, model.FlexibleLoad, domain= pyo.NonNegativeReals)
model.v_new_tech = pyo.Var(model.Technology, domain = pyo.NonNegativeReals) 
model.v_new_bat = pyo.Var(model.FlexibleLoad, domain = pyo.NonNegativeReals)
model.y_max = pyo.Var(model.Nodes, model.Month, domain = pyo.NonNegativeReals)
model.d_flex = pyo.Var(model.Nodes, model.Time, model.EnergyCarrier, domain = pyo.NonNegativeReals)
model.Up_Shift = pyo.Var(model.Nodes, model.Time, model.EnergyCarrier, domain = pyo.NonNegativeReals)
model.Dwn_Shift = pyo.Var(model.Nodes, model.Time, model.EnergyCarrier, domain = pyo.NonNegativeReals)
model.aggregated_Up_Shift = pyo.Var(model.Nodes, model.EnergyCarrier, domain = pyo.NonNegativeReals)
model.aggregated_Dwn_Shift = pyo.Var(model.Nodes, model.EnergyCarrier, domain = pyo.NonNegativeReals)
model.I_inv = pyo.Var()
model.I_GT = pyo.Var()
model.I_cap_bid = pyo.Var(model.Time)
model.I_activation = pyo.Var(model.Nodes, model.Time)
model.I_DA = pyo.Var(model.Nodes, model.Time)
model.I_ID = pyo.Var(model.Nodes, model.Time)
model.I_OPEX = pyo.Var(model.Nodes, model.Time)


"""
OBJECTIVE
""" 

#OBJECTIVE SHORT FORM
def objective(model):
    obj_expr = model.I_inv + model.I_GT + sum(
        model.I_cap_bid[t] + sum(sum(
            model.Node_Probability[n] * (
                model.I_activation[n, t] + model.I_DA[n, t] + model.I_ID[n, t] + model.I_OPEX[n, t]
            ) for (n, stage) in model.Nodes_in_stage if stage == s
        ) for s in model.Period    
    ) for t in model.Time)

    return obj_expr

model.Objective = pyo.Objective(rule=objective, sense=pyo.minimize)

"""
CONSTRAINTS
"""  

###########################################
############## COST BALANCES ##############
###########################################
def cost_investment(model):
    return model.I_inv == (sum(
        model.Cost_Expansion_Tec[i] * model.v_new_tech[i] for i in model.Technology
    ) + sum(
        model.Cost_Expansion_Bat[b] * model.v_new_bat[b] for b in model.FlexibleLoad
    ))
model.InvestmentCost = pyo.Constraint(rule=cost_investment)

def cost_capacity_bid(model, t):
    nodes_in_last_stage = {n for (n, stage) in model.Nodes_in_stage if stage == model.Period.last()}
    
    return model.I_cap_bid[t] == sum(
        model.Node_Probability[n] * (
            - (model.aFRR_Up_Capacity_Price[n, t] * model.x_UP[n, t] +
               model.aFRR_Dwn_Capacity_Price[n, t] * model.x_DWN[n, t])
        ) for n in model.Nodes if n not in nodes_in_last_stage
    )

model.CapacityBidCost = pyo.Constraint(model.Time, rule=cost_capacity_bid)

def cost_activation(model, n, p, t, s):
    if (n, s) in model.Nodes_in_stage:
        return model.I_activation[n, t] == (- model.Activation_Factor_UP_Regulation[n, t] * model.aFRR_Up_Activation_Price[n, t] * model.x_UP[p, t]
                + model.Activation_Factor_DWN_Regulation[n, t] * model.aFRR_Dwn_Activation_Price[n, t] * model.x_DWN[p, t])
    else:
        return pyo.Constraint.Skip
model.ActivationCost = pyo.Constraint(model.Parent_Node, model.Time, model.Period, rule=cost_activation)

def cost_DA(model, n, p, t, s):
    if (n,s) in model.Nodes_in_stage:
        return model.I_DA[n, t] == model.Spot_Price[n, t] * (model.x_DA_Up[p, t] - model.x_DA_Dwn[p, t])
    else:
        return pyo.Constraint.Skip
model.DACost = pyo.Constraint(model.Parent_Node, model.Time, model.Period, rule=cost_DA) 

def cost_ID(model, n, p, t, s):
    if (n,s) in model.Nodes_in_stage:
        return model.I_ID[n, t] == model.Intraday_Price[n, t] * (
                model.Activation_Factor_ID_Up[n, t] * model.x_ID_Up[p, t] 
                - model.Activation_Factor_ID_Dwn[n, t] * model.x_ID_Dwn[p, t]
            )
    else:
        return pyo.Constraint.Skip
model.IDCost = pyo.Constraint(model.Parent_Node, model.Time, model.Period, rule=cost_ID)    
"""
def cost_opex(model, n, s, t):
    return model.I_OPEX[n, t] == (sum(
                model.y_out[n, t, i, e, o] * (model.Cost_Energy[n, t, i] 
                + model.Carbon_Intensity[i, o] * model.Cost_Emission)
                for (i, e, o) in model.TechnologyToEnergyCarrier 
            ) 
            - sum(model.Cost_Export[n, t, i] * model.y_in[n, t, i, e, o] for (i, e, o) in model.EnergyCarrierToTechnology)
            + sum(model.Cost_Battery[b] * model.q_discharge[n, t, b] for b in model.FlexibleLoad)
            #Legge til Load shift cost?
    )
model.OPEXCost = pyo.Constraint(model.Nodes_in_stage, model.Time, rule=cost_opex)
"""
def cost_opex(model, n, s, t):
    return model.I_OPEX[n, t] == (sum(
                model.y_activity[n, t, i, o] * (model.Cost_Energy[n, t, i] 
                + model.Carbon_Intensity[i, o] * model.Cost_Emission)
                for (i, e, o) in model.TechnologyToEnergyCarrier 
            ) 
            - sum(model.Cost_Export[n, t, i] * model.y_activity[n, t, i, o] for (i, e, o) in model.EnergyCarrierToTechnology)
            + sum(model.Cost_Battery[b] * model.q_discharge[n, t, b] for b in model.FlexibleLoad)
            + sum(model.Cost_LS[e]*model.Dwn_Shift[n, t, e] for e in model.EnergyCarrier)
    )
model.OPEXCost = pyo.Constraint(model.Nodes_in_stage, model.Time, rule=cost_opex)

def cost_grid_tariff(model):
    return model.I_GT == sum(sum(model.Node_Probability[n] * model.Cost_Grid * model.y_max[n, m] for (n,s) in model.Nodes_in_stage if s == model.Last_Period_In_Month[m]) for m in model.Month)
model.GridTariffCost = pyo.Constraint(rule=cost_grid_tariff)

###########################################
############## ENERGY BALANCE #############
###########################################

def energy_balance(model, n, s, t, e):
    return (
        model.d_flex[n, t, e]
        == sum(sum(model.y_out[n, t, i, e, o] for i in model.Technology if (i,e,o) in model.TechnologyToEnergyCarrier)
        - sum(model.y_in[n, t, i, e, o] for i in model.Technology if(i,e,o) in model.EnergyCarrierToTechnology) for o in model.Mode_of_operation)
        - sum(
            model.Charge_Efficiency[b] * model.q_charge[n, t, b] - model.q_discharge[n, t, b]
            for b in model.FlexibleLoad if (b,e) in model.FlexibleLoadForEnergyCarrier
        )
    )
model.EnergyBalance = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=energy_balance)

def Defining_flexible_demand(model, n, s, t, e):
    return model.d_flex[n, t, e] == model.Demand[n, t, e] + model.Up_Shift[n, t, e] - model.Dwn_Shift[n, t, e]
model.DefiningFlexibleDemand = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule = Defining_flexible_demand)

#####################################################################################
########################### MARKET BALANCE DA/ID/RT #################################
#####################################################################################

def market_balance_import(model, n, p, t, s, i, e, o):
    if (i, e, o) == ("Power_Grid", "Electricity", 1) and (n,s) in model.Nodes_in_stage:
        return (model.y_out[n, t, i, e, o] == model.x_DA_Up[p, t] + model.Activation_Factor_ID_Up[n,t]*model.x_ID_Up[p, t] + model.Activation_Factor_DWN_Regulation[n, t] * model.x_DWN[p, t])
    else:
        return pyo.Constraint.Skip      
model.MarketBalanceImport = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.TechnologyToEnergyCarrier, rule = market_balance_import)

def market_balance_export(model, n, p, t, s, i, e, o):
    if (i, e, o) == ("Power_Grid", "Electricity", 2) and (n,s) in model.Nodes_in_stage:
        return (model.y_in[n, t, i, e, o] == model.x_DA_Dwn[p, t] + model.Activation_Factor_ID_Dwn[n,t]*model.x_ID_Dwn[p, t] + model.Activation_Factor_UP_Regulation[n, t] * model.x_UP[p, t])
    else:
        return pyo.Constraint.Skip      
model.MarketBalanceExport = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.EnergyCarrierToTechnology, rule = market_balance_export)

def Max_ID_Buy_Adjustment(model, n, t):
    nodes_in_last_stage = {n for (n, stage) in model.Nodes_in_stage if stage == model.Period.last()}
    if n not in nodes_in_last_stage:
        return (model.x_ID_Up[n, t] <= 0.5*model.ID_Cap_Buy_volume[n, t])
    else:
        return pyo.Constraint.Skip
model.MaxIDBuyAdjustment = pyo.Constraint(model.Nodes, model.Time, rule = Max_ID_Buy_Adjustment)

def Max_ID_Sell_Adjustment(model, n, t):
    nodes_in_last_stage = {n for (n, stage) in model.Nodes_in_stage if stage == model.Period.last()}
    if n not in nodes_in_last_stage:
        return (model.x_ID_Dwn[n, t] <= 0.5*model.ID_Cap_Sell_volume[n, t])
    else:
        return pyo.Constraint.Skip
model.MaxIDSellAdjustment = pyo.Constraint(model.Nodes, model.Time, rule = Max_ID_Sell_Adjustment)

#####################################################################################
########################### CONVERSION BALANCE ######################################
#####################################################################################

def conversion_balance_out(model, n, s, t, i, e, o):   
    return (model.y_out[n, t, i, e, o] == model.y_activity[n, t, i, o] * model.Technology_To_EnergyCarrier_Efficiency[i, e, o])     
model.ConversionBalanceOut = pyo.Constraint(model.Nodes_in_stage, model.Time, model.TechnologyToEnergyCarrier, rule = conversion_balance_out)

def conversion_balance_in(model, n, s, t, i, e, o):
    return (model.y_in[n, t, i, e, o] == model.y_activity[n, t, i, o] * model.EnergyCarrier_To_Technlogy_Efficiency[i, e, o])           
model.ConversionBalanceIn = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrierToTechnology, rule = conversion_balance_in)

#####################################################################################
########################### TECHNOLOGY RAMPING CONSTRAINTS ##########################
#####################################################################################

def Ramping_Technology(model, n, p, t, s, i, e, o):
    if (n,s) in model.Nodes_in_stage:
        if t == model.Time.first() and s == model.Period.first(): #Første tidssteg i første stage  
            return (model.y_out[n, t, i, e, o] <= model.Ramping_Factor[i] * (model.Initial_Installed_Capacity[i] + model.v_new_tech[i]))
        
        elif t == model.Time.first() and s > model.Period.first():
            return (model.y_out[n, t, i, e, o] - model.y_out[p, model.Time.last(), i, e, o] <= model.Ramping_Factor[i] * (model.Initial_Installed_Capacity[i] + model.v_new_tech[i]))

        else:
            return (model.y_out[n, t, i, e, o] - model.y_out[n, t-1, i, e, o] <= model.Ramping_Factor[i] * (model.Initial_Installed_Capacity[i] + model.v_new_tech[i]))
    else:
        return pyo.Constraint.Skip
model.RampingTechnology = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.TechnologyToEnergyCarrier, rule = Ramping_Technology)

#####################################################################################
############## HEAT PUMP LIMITATION - MÅ ENDRES I HENHOLD TIL INPUTDATA #############
#####################################################################################
"""
def heat_pump_input_limitation_LT(model, n, s, t):
    return (
        model.y_out[n, t, 'HP_LT', 'LT', 1] - model.y_in[n, t, 'HP_LT', 'Electricity', 1]
        <= model.Available_Excess_Heat * (model.d_flex[n, t, 'LT'])# + model.Demand[s, t, 'HT'])
    )
model.HeatPumpInputLimitationLT = pyo.Constraint(model.Nodes_in_stage, model.Time, rule=heat_pump_input_limitation_LT)

def heat_pump_input_limitation_MT(model, n, s, t):
    return (
        model.y_out[n, t, 'HP_MT', 'MT', 1] - model.y_in[n, t, 'HP_MT', 'Electricity', 1]
        <= model.Available_Excess_Heat * (model.d_flex[n, t, 'MT'])# + model.Demand[s, t, 'HT'])
    )
model.HeatPumpInputLimitationMT = pyo.Constraint(model.Nodes_in_stage, model.Time, rule=heat_pump_input_limitation_MT)
"""

def heat_pump_input_limitation(model, n, s, t):
    return (
        model.y_out[n, t, 'HP_MT', 'MT', 1] - model.y_in[n, t, 'HP_MT', 'Electricity', 1] 
        + model.y_out[n, t, 'HP_MT', 'LT', 2] - model.y_in[n, t, 'HP_MT', 'Electricity', 2] 
        + model.y_out[n, t, 'HP_LT', 'LT', 1] - model.y_in[n, t, 'HP_LT', 'Electricity', 1]
        <= model.Available_Excess_Heat * (model.d_flex[n, t, 'LT'] + model.d_flex[n, t, 'MT'])
    )
model.HeatPumpInputLimitation = pyo.Constraint(model.Nodes_in_stage, model.Time, rule=heat_pump_input_limitation)


######################################################
############## LOAD SHIFTING CONSTRAINTS #############
######################################################

def aggregated_up_shift(model, n, p, e):
    return model.aggregated_Up_Shift[n, e] == model.aggregated_Up_Shift[p, e] + sum(model.Up_Shift[n, t, e] for t in model.Time)
model.AggregatedUpShift = pyo.Constraint(model.Parent_Node, model.EnergyCarrier, rule=aggregated_up_shift)

def aggregated_dwn_shift(model, n, p, e):
    return model.aggregated_Dwn_Shift[n, e] == model.aggregated_Dwn_Shift[p, e] + sum(model.Dwn_Shift[n, t, e] for t in model.Time)
model.AggregatedDwnShift = pyo.Constraint(model.Parent_Node, model.EnergyCarrier, rule=aggregated_dwn_shift)

def balancing_aggregated_shifted_load(model, n, s, e):
    if s in model.LoadShiftingPeriod:
        return model.aggregated_Up_Shift[n, e] == model.aggregated_Dwn_Shift[n, e]
    else:
        return pyo.Constraint.Skip
model.BalancingAggregatedShiftedLoad = pyo.Constraint(model.Nodes_in_stage, model.EnergyCarrier, rule=balancing_aggregated_shifted_load)

def initialize_aggregated_up_shift(model, n, e):
    return model.aggregated_Up_Shift[n, e] == 0
model.InitializeAggregatedUpShift = pyo.Constraint(model.Nodes_first, model.EnergyCarrier, rule=initialize_aggregated_up_shift)

def initialize_aggregated_dwn_shift(model, n, e):
    return model.aggregated_Dwn_Shift[n, e] == 0
model.InitializeAggregatedDwnShift = pyo.Constraint(model.Nodes_first, model.EnergyCarrier, rule=initialize_aggregated_dwn_shift)

"""
def No_Up_Shift_outside_window(model, n, s, t, e):
    if (t,s) in model.Time_NO_LoadShift:
        return model.Up_Shift[n, t, e] == 0
    else:
        return pyo.Constraint.Skip
model.NoUpShiftOutsideWindow = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=No_Up_Shift_outside_window)

def No_Dwn_Shift_outside_window(model, n, s, t, e):
    if (t,s) in model.Time_NO_LoadShift:
        return model.Dwn_Shift[n, t, e] == 0
    else:
        return pyo.Constraint.Skip
model.NoDwnShiftOutsideWindow = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=No_Dwn_Shift_outside_window)
"""

###########################################################
############## MAX ALLOWABLE UP/DOWN SHIFT ################
###########################################################

def max_up_shift(model, n, s, t, e):
    return model.Up_Shift[n, t, e] <= model.Up_Shift_Max[t] * model.Demand[n, t, e]    
model.MaxUpShift = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=max_up_shift)

def max_dwn_shift(model, n, s, t, e):
    return model.Dwn_Shift[n, t, e] <= model.Down_Shift_Max[t] * model.Demand[n, t, e]
model.MaxDwnShift = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=max_dwn_shift)

"""
def Max_total_up_dwn_load_shift(model, n, s, t, e):
    return model.Up_Shift[n,t,e] + model.Dwn_Shift[n,t,e] <= model.Up_Shift_Max * model.Demand[n, t, e] 
model.MaxTotalUpDwnLoadShift = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrier, rule=Max_total_up_dwn_load_shift)
"""

########################################################################
############## RESERVE MARKET PARTICIPATION LIMITS #####################
########################################################################

def reserve_down_limit(model, n, p, t, s, e):
    if e == "Electricity" and (n,s) in model.Nodes_in_stage:  # Ensure e = EL
        return model.x_DWN[p, t] <= (
            model.Up_Shift_Max[t] * model.Demand[n, t, e]
            + sum(
                model.Max_charge_discharge_rate[b] + model.Power2Energy_Ratio[b] * model.v_new_bat[b]
                for b in model.FlexibleLoad if (b, e) in model.FlexibleLoadForEnergyCarrier
            )
        )
    else:
        return pyo.Constraint.Skip
model.ReserveDownLimit = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.EnergyCarrier, rule=reserve_down_limit)

def reserve_up_limit(model, n, p, t, s, e):
    if e == "Electricity" and (n,s) in model.Nodes_in_stage:  # Ensure e = EL
        return model.x_UP[p, t] <= (
            model.Down_Shift_Max[t] * model.Demand[n, t, e]
            + sum(
                model.Max_charge_discharge_rate[b] + model.Power2Energy_Ratio[b] * model.v_new_bat[b]
                for b in model.FlexibleLoad if (b, e) in model.FlexibleLoadForEnergyCarrier
            )
        )
    else:
        return pyo.Constraint.Skip
model.ReserveUpLimit = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.EnergyCarrier, rule=reserve_up_limit)

########################################################################
############## UPPER-UPPER BOUND CAPACITY MARKET BIDS ##################
########################################################################

def max_capacity_up_bid(model, n, t):
    return model.x_UP[n,t] <= 50
model.MaxCapacityUpBid = pyo.Constraint(model.Nodes, model.Time, rule=max_capacity_up_bid)

def max_capacity_down_bid(model, n, t):
    return model.x_DWN[n,t] <= 50
model.MaxCapacityDownBid = pyo.Constraint(model.Nodes, model.Time, rule=max_capacity_down_bid)

def maximum_market_down_reserve_limit(model, n, t):
    return model.x_DWN[n,t] <= 0.5*model.Res_Cap_Down_volume[n,t] #Limiting 
model.MaxMarketDownReserveLimit = pyo.Constraint(model.Nodes, model.Time, rule=maximum_market_down_reserve_limit)

def maximum_market_up_reserve_limit(model, n, t):
    return model.x_UP[n,t] <= 0.5*model.Res_Cap_Up_volume[n,t]
model.MaxMarketUpReserveLimit = pyo.Constraint(model.Nodes, model.Time, rule=maximum_market_up_reserve_limit)

########################################################################
############## FLEXIBLE ASSET CONSTRAINTS/STORAGE DYNAMICS #############
########################################################################
def flexible_asset_charge_discharge_limit(model, n, s, t, b, e):
    return (
        model.q_charge[n, t, b] 
        + model.q_discharge[n, t, b] / model.Discharge_Efficiency[b] 
        <= model.Max_charge_discharge_rate[b] + model.Power2Energy_Ratio[b] * model.v_new_bat[b]
    )
model.FlexibleAssetChargeDischargeLimit = pyo.Constraint(model.Nodes_in_stage, model.Time, model.FlexibleLoadForEnergyCarrier, rule=flexible_asset_charge_discharge_limit)

def state_of_charge(model, n, p, t, s, b, e):
    if (n,s) in model.Nodes_in_stage:
        if t == model.Time.first() and s == model.Period.first() :  # Initialisation of flexible assets
            return (
                model.q_SoC[n, t, b]
                == model.Initial_SOC[b] * (model.Max_Storage_Capacity[b] + model.v_new_bat[b]) * (1 - model.Self_Discharge[b])
                + model.q_charge[n, t, b]
                - model.q_discharge[n, t, b] / model.Discharge_Efficiency[b]
            )
        elif t == model.Time.first() and s > model.Period.first():  #Overgangen mellom stages
            return (
                model.q_SoC[n, t, b]
                == model.q_SoC[p, model.Time.last(), b] * (1 - model.Self_Discharge[b])
                + model.q_charge[n, t, b]
                - model.q_discharge[n, t, b] / model.Discharge_Efficiency[b]
            )
        else:        
            return (
                model.q_SoC[n, t, b]
                == model.q_SoC[n, t-1, b] * (1 - model.Self_Discharge[b])
                + model.q_charge[n, t, b]
                - model.q_discharge[n, t, b] / model.Discharge_Efficiency[b]
            )
    else:
        return pyo.Constraint.Skip
model.StateOfCharge = pyo.Constraint(model.Parent_Node, model.Time, model.Period, model.FlexibleLoadForEnergyCarrier, rule=state_of_charge)

def end_of_horizon_SoC(model, n, s, t, b, e):
    if t == model.Time.last() and s == model.Period.last():
        return model.q_SoC[n, t, b] == model.Initial_SOC[b] * (model.Max_Storage_Capacity[b] + model.v_new_bat[b])
    else:
        return pyo.Constraint.Skip
model.EndOfHorizonSoC = pyo.Constraint(model.Nodes_in_stage, model.Time, model.FlexibleLoadForEnergyCarrier, rule = end_of_horizon_SoC)

def flexible_asset_energy_limit(model, n, s, t, b, e):
    return model.q_SoC[n, t, b] <= model.Max_Storage_Capacity[b] + model.v_new_bat[b]
model.FlexibleAssetEnergyLimits = pyo.Constraint(model.Nodes_in_stage, model.Time, model.FlexibleLoadForEnergyCarrier, rule=flexible_asset_energy_limit)

####################################################
############## AVAILABILITY CONSTRAINT #############
####################################################

def supply_limitation(model, n, s, t, i):
    return (sum(model.y_out[n, t, i, e, o] for e,o in model.EnergyCarrier * model.Mode_of_operation if (i,e,o) in model.TechnologyToEnergyCarrier)  
                <= model.Availability_Factor[n, t, i] * (model.Initial_Installed_Capacity[i] + model.v_new_tech[i]))
model.SupplyLimitation = pyo.Constraint(model.Nodes_in_stage, model.Time, model.Technology, rule=supply_limitation)

##############################################################
############## EXPORT LIMITATION AND GRID TARIFF #############
##############################################################

def export_limitation(model, n, s, t, i, e, o):
    if (i, e, o) == ('Power_Grid', 'Electricity', 2):
        return model.y_in[n, t, i, e, o] <= model.Max_Export
    else:
        return pyo.Constraint.Skip
model.ExportLimitation = pyo.Constraint(model.Nodes_in_stage, model.Time, model.EnergyCarrierToTechnology, rule=export_limitation)

def peak_load(model, n, s, t, m, i, e, o):
    if i == 'Power_Grid' and e == 'Electricity' and (m,s) in model.PeriodInMonth:
        return (model.y_out[n, t, i, e, o] <= model.y_max[n, m])
    else:
        return pyo.Constraint.Skip
model.PeakLoad = pyo.Constraint(model.Nodes_in_stage, model.Time, model.Month, model.TechnologyToEnergyCarrier, rule=peak_load)

def Node_greater_than_parent(model, n, p, s, m):
    """
    if (n,s) in model.Nodes_in_stage and (m,s) in model.PeriodInMonth:
        return model.y_max[p, m] <= model.y_max[n, m]
    else:
        return pyo.Constraint.Skip
    """
    # n i stage s og måned m
    if (n, s) in model.Nodes_in_stage and (m, s) in model.PeriodInMonth:
        # Finn alle s_p der p er i den samme måneden
        for s_p in model.Period:
            if (p, s_p) in model.Nodes_in_stage and (m, s_p) in model.PeriodInMonth:
                return model.y_max[p, m] <= model.y_max[n, m]
    return pyo.Constraint.Skip
model.NodeGreaterThanParent = pyo.Constraint(model.Parent_Node, model.Period, model.Month, rule = Node_greater_than_parent)

##############################################################
##################### INVESTMENT LIMITATIONS #################
##############################################################
"""
def CAPEX_technology_limitations(model, i):
    return (model.Cost_Expansion_Tec[i] * model.v_new_tech[i] <= model.Max_CAPEX_tech[i])
model.CAPEXTechnologyLim = pyo.Constraint(model.Technology, rule=CAPEX_technology_limitations)

def CAPEX_flexibleLoad_limitations(model, b):
    return (model.Cost_Expansion_Bat[b] * model.v_new_bat[b] <= model.Max_CAPEX_flex[b])
model.CAPEXFlexibleLoadLim = pyo.Constraint(model.FlexibleLoad, rule=CAPEX_flexibleLoad_limitations)
"""

def CAPEX_limitations(model):
    return model.I_inv <= model.Max_CAPEX
model.CAPEXLim = pyo.Constraint(rule=CAPEX_limitations)

##############################################################
##################### CARBON EMISSION LIMIT ##################
##############################################################
"""
def Carbon_Emission_Limit(model, n): #Kan løses med aggregert variabel og parent-nodes
    total_emission = sum(
        model.y_activity[n, t, i, o] * model.Carbon_Intensity[i, o]
        for t in model.Time
        for (i,e,o) in model.TechnologyToEnergyCarrier
    )
    return total_emission <= model.Max_Carbon_Emission
model.CarbonEmissionLimit = pyo.Constraint(model.Nodes_in_stage, rule=Carbon_Emission_Limit)
"""

def Carbon_Emission_Limit(model, n, s): 
    return sum(sum(sum(
        model.y_activity[n, t, i, o] * model.Carbon_Intensity[i, o]
        for o in model.Mode_of_operation if (i,o) in model.Carbon_Intensity) for i in model.Technology) for t in model.Time) <= model.Max_Carbon_Emission
model.CarbonEmissionLimit = pyo.Constraint(model.Nodes_in_stage, rule=Carbon_Emission_Limit)

print("Objective and constraints read...")

"""
MATCHING DATA FROM CASE WITH MATHEMATICAL MODEL AND PRINTING DATA
"""
print("Building instance...")

our_model = model.create_instance(data)   
our_model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT) #Import dual values into solver results
#import pdb; pdb.set_trace()

"""
SOLVING PROBLEM
"""
print("Solving...")

opt = SolverFactory("gurobi", Verbose=True)
#opt.options['LogFile'] = 'gurobi_log.txt'

#start the timer
start_time = time.time()

results = opt.solve(our_model, tee=True)

#stop the timer
end_time = time.time()
running_time = end_time - start_time

"""
DISPLAY RESULTS??
"""
print("Writing results to .csv...")

our_model.display('results.csv')
our_model.dual.display()
print("-" * 70)
print("Objective and running time:")
print(f"Objective value for this mongo model is: {round(pyo.value(our_model.Objective),2)}")
print(f"The instance was solved in {round(running_time, 4)} seconds🙂")
print("-" * 70)
print("Hardware details:")
print(f"Processor: {platform.processor()}")
print(f"Machine: {platform.machine()}")
print(f"System: {platform.system()} {platform.release()}")
#print(f"CPU Cores: {psutil.cpu_count(logical=True)} (Logical), {psutil.cpu_count(logical=False)} (Physical)")
#print(f"Total Memory: {psutil.virtual_memory().total / 1e9:.2f} GB")
print("-" * 70)
#import pdb; pdb.set_trace()



"""
EXTRACT VALUE OF VARIABLES AND WRITE THEM INTO EXCEL FILE
"""
print("Writing results to .xlsx...")

def save_results_to_excel(model_instance, filename="Variable_Results.xlsx"):
    
    # Saves Pyomo variable results into an Excel file with filtered output.
    # Only includes rows with non-zero or non-null values for variables.
    
    import pandas as pd
    from pyomo.environ import value

    # Create an Excel writer object
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        # Loop over all active variables in the model
        for var in model_instance.component_objects(pyo.Var, active=True):
            var_name = var.name  # Get the variable name
            var_data = []
            
            # Collect variable data
            for index in var:
                try:
                    var_value = value(var[index])  # Safely get the variable value
                except ValueError:
                    var_value = 0  # If uninitialized, set to None
                if var_value:  # Include only non-zero and non-null values
                    var_data.append((index, var_value))
            
            # Transform data into a DataFrame
            if var_data:  # Only proceed if there is data
                df = pd.DataFrame(var_data, columns=["Index", var_name])
                
                # Dynamically unpack the indices into separate columns
                max_index_length = max(len(idx) if isinstance(idx, tuple) else 1 for idx, _ in var_data)
                unpacked_indices = pd.DataFrame(
                    [list(index) + [None] * (max_index_length - len(index)) if isinstance(index, tuple) else [index] for index, _ in var_data]
                )
                
                # Add unpacked indices to the DataFrame
                unpacked_indices.columns = [f"Index_{i+1}" for i in range(max_index_length)]
                df = pd.concat([unpacked_indices, df[var_name]], axis=1)
                
                # Write the filtered DataFrame to an Excel sheet
                df.to_excel(writer, sheet_name=var_name[:31], index=False)
    
    print(f"Variable results saved to {filename}")

# Usage after solving the model
save_results_to_excel(our_model, filename="Variable_Results.xlsx")


"""
PLOT RESULTS
"""
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap
import numpy as np

def generate_unique_colors(n):
    cmap = plt.get_cmap("tab10")  # Use the tab10 colormap for distinct colors
    return [cmap(i % 10) for i in range(n)]

def plot_results_from_excel(input_file, output_folder, model):
    os.makedirs(output_folder, exist_ok=True)  # Create folder if it doesn't exist

    # Construct Nodes mapping dynamically
    Nodes_mapping = {n: f"Node {n}" for n in model.Nodes}

    ########################################################################################
    ############## ENDRE FOR Å DEFINERE HVILKE VARIABLER SOM IKKE SKAL PLOTTES #############
    ########################################################################################
    exclude_sheets = ["y_max", "y_activity", "Up_shift", "Dwn_Shift", "d_flex", "I_OPEX", "I_DA", "I_ID", "I_activation", "I_cap_bid", "I_inv"]
    exclude_sheets = [x.strip().lower() for x in exclude_sheets]  # Normalize sheet names

    # Read the Excel file
    excel_file = pd.ExcelFile(input_file)

    for sheet_name in excel_file.sheet_names:
        if sheet_name.strip().lower() in exclude_sheets:
            print(f"Skipping variable: {sheet_name}") 
            continue  

        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        if sheet_name in ["x_aFRR_DWN", "x_aFRR_UP"]:
            # Plot Index_1 vs second column for these sheets
            x_axis = df["Index_1"]
            y_axis = df.iloc[:, 1]  # Second column

            plt.figure(figsize=(12, 8))
            plt.plot(x_axis, y_axis, label=sheet_name, marker='o', color='blue')

            plt.title(f"{sheet_name}")
            plt.xlabel("Hours")
            plt.ylabel("Values")
            plt.legend(loc='best')
            plt.grid(True)

            plot_filename = f"{sheet_name}.png"
            plt.tight_layout()
            plt.savefig(os.path.join(output_folder, plot_filename))
            plt.close()

        elif sheet_name in ["x_aFRR_DWN_ind", "x_aFRR_UP_ind"]:
            # Handle indexed reserve market data
            if "Index_1" in df.columns and "Index_2" in df.columns:
                plt.figure(figsize=(12, 8))

                x_axis = df["Index_1"]
                value_column = df.columns[-1]
                unique_variables = df["Index_2"].dropna().unique()  # Drop NaN values
                colors = generate_unique_colors(len(unique_variables))

                for variable, color in zip(unique_variables, colors):
                    variable_data = df[df["Index_2"] == variable]
                    plt.plot(
                        variable_data["Index_1"], variable_data[value_column],
                        label=variable, marker='o', color=color
                    )

                plt.title(f"{sheet_name}")
                plt.xlabel("Hours")
                plt.ylabel("Values")
                plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, title="Variables", borderaxespad=0.)
                plt.grid(True)

                plot_filename = f"{sheet_name}.png"
                plt.tight_layout()
                plt.savefig(os.path.join(output_folder, plot_filename))
                plt.close()

        else:
            # General plotting for other sheets
            if "Index_1" in df.columns and "Index_2" in df.columns:
                unique_index_1 = df["Index_1"].unique()

                for index_1_value in unique_index_1:
                    filtered_df = df[df["Index_1"] == index_1_value]

                    plt.figure(figsize=(12, 8))

                    if "Index_3" in filtered_df.columns:
                        variable_column = "Index_3"
                        value_column = df.columns[-1]
                        unique_variables = filtered_df[variable_column].dropna().unique()
                        colors = generate_unique_colors(len(unique_variables))

                        for variable, color in zip(unique_variables, colors):
                            variable_data = filtered_df[filtered_df[variable_column] == variable]
                            plt.plot(
                                variable_data["Index_2"], variable_data[value_column],
                                label=variable, marker='o', color=color
                            )

                        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, title="Variables", borderaxespad=0.)
                    else:
                        value_column = df.columns[-1]
                        plt.plot(filtered_df["Index_2"], filtered_df[value_column], label=value_column, marker='o', color='blue')

                    # Use Nodes mapping for title
                    Nodes_name = Nodes_mapping.get(index_1_value, f"Index_1 = {index_1_value}")
                    plt.title(f"{sheet_name} ({Nodes_name})")
                    plt.xlabel("Hours")
                    plt.ylabel("Values")
                    plt.grid(True)

                    plot_filename = f"{sheet_name}_{Nodes_name.replace(' ', '_')}.png"
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_folder, plot_filename))
                    plt.close()


# Usage
if __name__ == "__main__":
    input_excel_file = "Variable_Results.xlsx"  # Path to the Excel file
    output_plots_folder = "plots"  # Folder to save the plots

    # Generate plots
    plot_results_from_excel(input_excel_file, output_plots_folder, our_model)


def extract_demand_and_flex_demand(model):
    demand_data = []
    flex_demand_data = []

    for n in model.Nodes_RT:
        for t in model.Time:
            for e in model.EnergyCarrier:
                if e == "Electricity":
                    demand_value = pyo.value(model.Demand[n, t, e])
                    flex_demand_value = pyo.value(model.d_flex[n, t, e])

                    demand_data.append({'Nodes': n, 'Time': t, 'EnergyCarrier': e, 'Reference_Demand': demand_value})
                    flex_demand_data.append({'Nodes': n, 'Time': t, 'EnergyCarrier': e, 'flex_demand': flex_demand_value})

    # Convert to DataFrame
    demand_df = pd.DataFrame(demand_data)
    flex_demand_df = pd.DataFrame(flex_demand_data)

    return demand_df, flex_demand_df
 # Get the data
demand_df, flex_demand_df = extract_demand_and_flex_demand(our_model)

# Merge the DataFrames for unified plotting
merged_df = pd.merge(demand_df, flex_demand_df, on=['Nodes', 'Time', 'EnergyCarrier'])

# Endre denne for å plotte utvalgte noder (eks. første 4 i driftsnodene)
subset_nodes = merged_df["Nodes"].unique()[:4]
subset_df = merged_df[merged_df["Nodes"].isin(subset_nodes)]

# Plotting
plt.figure(figsize=(12, 6))

#####################################################################################
########################### FOR Å PLOTTE ALLE NODENE ################################
#####################################################################################

#for Nodes in merged_df['Nodes'].unique():
#    Nodes_data = merged_df[merged_df['Nodes'] == Nodes]
#    plt.step(Nodes_data['Time'], Nodes_data['Reference_Demand'],label=f'Demand - Nodes {Nodes}')
#    plt.step(Nodes_data['Time'], Nodes_data['flex_demand'], "--", label=f'Flex Demand - Nodes {Nodes}')


#####################################################################################
########################### FOR Å PLOTTE UTVALGTE NODER #############################
#####################################################################################
for node in subset_nodes:
    node_data = subset_df[subset_df["Nodes"] == node]
    plt.step(node_data["Time"], node_data["Reference_Demand"], label=f"Ref Demand - Node {node}", linestyle="-")
    plt.step(node_data["Time"], node_data["flex_demand"], label=f"Flex Demand - Node {node}", linestyle="--")


plt.xlabel('Time')
plt.ylabel('Demand (MW)')
plt.title('Demand and Flexible Demand Over Time')
plt.legend()
plt.grid(True)
plt.show()
"""