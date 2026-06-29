"""Draft that taking in a specific folder with some specific structure taken from pressure sweep, generate interesting plots.

Use : python3 generate_plot_results_v1.py plotting_data_case001

Here it is assumed that the folder plotting_data_case001 is the folder contains the following structure:
- one json file reference that contains rho and Cp to compute some post-processes quantities.
- several folders, each containing the results of a simulation. The name of the folder should follow a specific structure, namely f"pressure_sweep_{chip}_real.txt", where chip is the name of the chip considered in the simulation.

!!! Note !!!: the use of this is deprecated in favor of the use of glaciercore plot
"""

import json
import os
import sys

import numpy as np
from pint import UnitRegistry

ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
ureg.setup_matplotlib(True)

import matplotlib.pyplot as plt
import numpy as np
from colorama import Fore
from project_plotting_utils import (
    DataPlotInput,
    NumpyEncoder,
    PlotOptions,
    chip,
    colors,
    delta_p_title,
    delta_p_units,
    fills,
    get_problem_data,
    linestyles,
    makeplot,
    markeredgecolors,
    markers,
    powermap_path,
    read_power_map_file,
    sizes,
    style_perso,
    txtname_chip,
    update_savedparams,
)
from pylab import *

plt.style.use([style_perso])
# --------------------------------------
#                INPUTS
# --------------------------------------
excel_folder = "excel_data/"
input_dir = sys.argv[1] + "/"
jsondir = "jsonfiles/"
suffix = "topopt_vs_channels"
(power_map_width, power_map_length) = read_power_map_file(powermap_path)
power_map_width = power_map_width * ureg.meters
power_map_length = power_map_length * ureg.meters
print(
    f"{Fore.RED} The power map considered in this case has a width of {power_map_width.to(ureg.millimeters)} and a height of {power_map_length.to(ureg.millimeters)}{Fore.RESET}"
)
max_temperature_allowed = 105 * ureg.degC
plotinput = DataPlotInput(
    input_dir=input_dir,
    jsondir=jsondir,
    suffix=suffix,
    chip=chip,
    power_map_width=power_map_width,
    power_map_length=power_map_length,
    max_temperature_allowed=max_temperature_allowed,
)


# --------------------------------------
#                Extracting rho and Cp from reference json file
# --------------------------------------
directory_contents = os.listdir(plotinput.input_dir)
directory_contents = sorted(directory_contents)
json_files = [f for f in directory_contents if f.endswith(".json")]
json_file = json_files[0]
problem_data = get_problem_data(
    json_path=plotinput.input_dir + json_file, field="problem_data"
)
rho = problem_data["density_fluid"] * ureg.kilograms / ureg.meters**3
Cp = problem_data["capacity_fluid"] * ureg.J / ureg.kilograms / ureg.K
A = plotinput.power_map_length * plotinput.power_map_width
rho = rho.to_base_units()
Cp = Cp.to_base_units()

print(
    f"{Fore.BLUE} ATTENTION : Please take note that this is the template script! The inputs of your real projects should be modified accordingly!{Fore.RESET}"
)
print(f"{Fore.RED}=========================")
print(f"         {chip}         ")
print(f"========================={Fore.RESET}")


Tout_sim_all = []
DT_sim_all = []
f_sim_all = []
R_sim_all = []
Tin_sim_all = []
Q_maximum_all = []
Qd_maximum_all = []
Tout_maximum_all = []
DP_sim_all = []
labels_all = []
pumping_power_all = []
COP_max_all = []
COP_60_all = []
COP_normal_all = []
is_chiplet_activated = False
Chiplet_DT_sim_all = []
Chiplet_DT_sim = None

prefix = []
simulation_information = {}
for content in directory_contents:
    if os.path.isdir(plotinput.input_dir + content) and "jsonfiles" not in content:
        design = content + "/"
        print("%s is a directory" % design)

        prefix.append(content)
        if "channel" in design:
            simulation_information["sim_label"] = "Straight channels, "
            if "schannels_50" in design:
                simulation_information["sim_label"] += "width 50um"
            elif "100" in design:
                simulation_information["sim_label"] += "width 100um"
            elif "schannels_150" in design:
                simulation_information["sim_label"] += "width 150um"
            elif "200" in design:
                simulation_information["sim_label"] += "width 200um"
            elif "uniform50" in design:
                simulation_information["sim_label"] += "width 50um - uniform powermap"
            elif "uniform100" in design:
                simulation_information["sim_label"] += "width 100um - uniform powermap"
            else:
                simulation_information["sim_label"] += ""
        else:
            simulation_information["sim_label"] = f"optimized design"
        print(
            f"{Fore.GREEN}reading {plotinput.input_dir+design+txtname_chip}{Fore.RESET}"
        )

        # Read the file
        data = np.genfromtxt(
            plotinput.input_dir + design + txtname_chip,
            skip_header=1,
            unpack=True,
            delimiter=",",
        )

        # Determine the number of columns in the data
        num_columns = data.shape[0]

        # Unpack the data based on the number of columns
        if num_columns == 7:
            Tin_sim, DP_sim, f_sim, DT_sim, Tout_sim, Q_currentsim, Remax = data
        elif num_columns == 8:
            is_chiplet_activated = True
            (
                Tin_sim,
                DP_sim,
                f_sim,
                DT_sim,
                Chiplet_DT_sim,
                Tout_sim,
                Q_currentsim,
                Remax,
            ) = data
        else:
            raise ValueError("Unexpected number of columns in the data file")

        # additional labelling
        if "inchip" in design:
            simulation_information["sim_label"] += ", in-chip"
        if "timA" in design:
            simulation_information[
                "sim_label"
            ] += ", TIM AWS reference case for PTM7950"
        if "timC" in design:
            simulation_information[
                "sim_label"
            ] += ", TIM Expected scenario for TCG Grease"
        if "timD" in design:
            simulation_information["sim_label"] += ", TIM Expected scenario for ELM"
        Q_full = Q_currentsim * ureg.watt
        Qd = Q_full / A
        simulation_information["sim_label"] += f", {int(Tin_sim[0])} [C] inlet"

        Tin_sim *= ureg.degC
        DP_sim *= ureg.Pa
        f_sim *= ureg.meters**3 / ureg.seconds
        DT_sim *= ureg.kelvin

        # extract the Tin_sim values
        Delta = Q_full / (f_sim * rho * Cp)
        Delta = Delta.to(ureg.delta_degC)
        Tout_sim = Delta + Tin_sim
        Tout_sim = Tout_sim.to(ureg.degC)

        R_sim = DT_sim / Q_full  # thermal resistance of the whole chip
        R_sim.to(ureg.kelvin / ureg.W)
        Q_maximum = (
            max_temperature_allowed - Tin_sim
        ) / R_sim  # power of the whole chip
        Q_maximum60 = (60 * ureg.degC - Tin_sim) / R_sim  # power of the whole chip
        Qd_maximum = Q_maximum / Q_full * Qd
        Qd_maximum = Qd_maximum.to(ureg.W / ureg.centimeters**2)
        Delta_out_maximum = Q_maximum / (f_sim * rho * Cp)
        Delta_out_maximum = Delta_out_maximum.to(ureg.delta_degC)
        Tout_maximum = Delta_out_maximum + Tin_sim
        Tout_maximum = Tout_maximum.to(ureg.degC)

        pumping_power = DP_sim * f_sim / 0.85
        # COP definition at max Temp
        COP_max = Q_maximum / (pumping_power * ureg.dimensionless)
        # COP definition at 60C
        COP_60 = Q_maximum60 / (pumping_power * ureg.dimensionless)
        # COP standard
        COP_normal = Q_full / (pumping_power * ureg.dimensionless)

        DP_sim = DP_sim.to(ureg.bars)
        f_sim = f_sim.to(ureg.liters / ureg.minutes)
        DT_sim = DT_sim.to(ureg.delta_degC)
        COP_max = COP_max.to(ureg.dimensionless)
        COP_60 = COP_60.to(ureg.dimensionless)
        COP_normal = COP_normal.to(ureg.dimensionless)
        pumping_power = pumping_power.to(ureg.W)

        f_sim_all.append(f_sim)
        Tout_sim_all.append(Tout_sim)
        DT_sim_all.append(DT_sim)
        R_sim_all.append(R_sim)
        Tin_sim_all.append(Tin_sim)
        Qd_maximum_all.append(Qd_maximum)
        Q_maximum_all.append(Q_maximum)
        Tout_maximum_all.append(Tout_maximum)
        every = max([int(len(DP_sim) / 10), 1])
        DP_sim_all.append(DP_sim)
        pumping_power_all.append(pumping_power)
        COP_max_all.append(COP_max)
        COP_60_all.append(COP_60)
        COP_normal_all.append(COP_normal)

        if is_chiplet_activated:
            Chiplet_DT_sim *= ureg.delta_degC
            Chiplet_DT_sim_all.append(Chiplet_DT_sim)

        labels_all.append(simulation_information["sim_label"])
        for index in range(len(DP_sim)):
            simulation_information["Power[W]"] = Q_currentsim[index]
            simulation_information["T_inlet[C]"] = Tin_sim[index].magnitude
            simulation_information["Pressure[Pa]"] = (
                DP_sim[index].to(ureg.pascal).magnitude
            )
            simulation_information["flow_rate[m^3/s]"] = (
                f_sim[index].to(ureg.meter**3 / ureg.seconds).magnitude
            )
            simulation_information["flow_rate[L/min]"] = (
                f_sim[index].to(ureg.liters / ureg.minutes).magnitude
            )
            simulation_information["Deltat[C]"] = DT_sim[index].magnitude
            simulation_information[f"Pumping power [W]"] = pumping_power[
                index
            ].magnitude
            simulation_information[f"COP[-] with power {Q_full[0].magnitude}"] = (
                COP_normal[index].magnitude
            )
            simulation_information[
                f"COP[-] with power to operate at {max_temperature_allowed.magnitude} C, Q= {Q_maximum[index].magnitude}W"
            ] = COP_max[index].magnitude
            simulation_information["Thermal resistance full chip[K/W]"] = R_sim[
                index
            ].magnitude
            simulation_information[
                f"Max power for {max_temperature_allowed.magnitude}C [W]"
            ] = Q_maximum[index].magnitude
            update_savedparams(
                simulation_information,
                excel_folder,
                f"{chip}.csv",
            )

# Plot 001 : flow rate versus pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=f_sim_all,
        xlabel=delta_p_title,
        ylabel=r"$f$ $(L/min)$",
        xunits=delta_p_units,
        yunits=ureg.liters / ureg.minutes,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot001_f_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 002 : Delta T vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=DT_sim_all,
        xlabel=delta_p_title,
        ylabel=r"$\Delta T$ $(C)$",
        xunits=delta_p_units,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        plotname=f"plot002_DT_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 003 : Real junction temperature vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=[
            Tvalue + Tin - ureg.Quantity(273.15, "kelvin")
            for Tvalue, Tin in zip(DT_sim_all, Tin_sim_all)
        ],
        xlabel=delta_p_title,
        ylabel=r"$T^{junction}$ $(C)$",
        xunits=delta_p_units,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot003_Tjunction_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 004 : Thermal resistance vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=R_sim_all,
        xlabel=delta_p_title,
        ylabel=r"$R$ $(C/W)$",
        xunits=delta_p_units,
        yunits=ureg.delta_degC / ureg.W,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot004_R_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 005 : Thermal resistance vs 1/f
makeplot(
    plotoptions=PlotOptions(
        x_array=[1.0 / flow for flow in f_sim_all],
        y_array=R_sim_all,
        xlabel=r"$1/f$ $(s/mL)$",
        ylabel=r"$R$ $(C/W)$",
        xunits=ureg.seconds / ureg.milliliters,
        yunits=ureg.delta_degC / ureg.W,
        label=labels_all,
        plotname=f"plot005_R_vs_f-1_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 006 : Thermal resistance vs flow rate
makeplot(
    plotoptions=PlotOptions(
        x_array=f_sim_all,
        y_array=R_sim_all,
        xlabel=r"$f$ $(L/min)$",
        ylabel=r"$R$ $(C/W)$",
        xunits=ureg.liters / ureg.minutes,
        yunits=ureg.delta_degC / ureg.W,
        label=labels_all,
        plotname=f"plot006_R_vs_f_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 007 : Maximum chip power coolable given the maximum allowed temperature vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=Q_maximum_all,
        xlabel=delta_p_title,
        ylabel=r"$Q^{maximum}$ $(W)$",
        xunits=delta_p_units,
        yunits=ureg.W,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot007_Qmaximum_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 008 : Maximum (average) heat flux vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=Qd_maximum_all,
        xlabel=delta_p_title,
        ylabel=r"$q^{maximum}$ $(W/cm^2)$",
        xunits=delta_p_units,
        yunits=ureg.W / ureg.centimeters**2,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot008_qd_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 009 : Output average temperature vas flow rate
makeplot(
    plotoptions=PlotOptions(
        x_array=f_sim_all,
        y_array=Tout_maximum_all,
        xlabel=r"$f$ $(L/min)$",
        ylabel=r"$T_{out}^{ T^{junction} ="
        + str(max_temperature_allowed.magnitude)
        + r"^\circ C}$ $(C)$",
        xunits=ureg.liters / ureg.minutes,
        yunits=ureg.degC,
        label=labels_all,
        plotname=f"plot009_Tout_vs_f_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 010 : Output average temperature vs power
makeplot(
    plotoptions=PlotOptions(
        x_array=Q_maximum_all,
        y_array=Tout_maximum_all,
        xlabel=r"$Q$ $(W)$",
        ylabel=r"$T_{out}^{ T^{junction} ="
        + str(max_temperature_allowed.magnitude)
        + r"^\circ C}$ $(C)$",
        xunits=ureg.W,
        yunits=ureg.degC,
        label=labels_all,
        plotname=f"plot010_Tout_vs_Q_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 011 : Delta t vs flow rate
makeplot(
    plotoptions=PlotOptions(
        x_array=f_sim_all,
        y_array=DT_sim_all,
        xlabel=r"$f$ $(L/min)$",
        ylabel=r"$\Delta T$ $(C)$",
        xunits=ureg.liters / ureg.minutes,
        yunits=ureg.delta_degC,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        label=labels_all,
        plotname=f"plot011_Deltat_vs_f_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Plot 012 : Average outlet temperature vs pressure drop
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=Tout_maximum_all,
        xlabel=delta_p_title,
        ylabel=r"$T_{out}^{ T^{junction} ="
        + str(max_temperature_allowed.magnitude)
        + r"^\circ C}$ $(C)$",
        xunits=delta_p_units,
        yunits=ureg.degC,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot012_Tout_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)
# Example of more "advanced" plots. Assume you want to keep optimized designs and straight channels in different colors. Then simply use a specific list in the plot options.
custom_markers = [
    "o",
    "s",
    "D",
    "v",
    "o",
    "s",
    "D",
    "v",
]
custom_linestyles = [
    "-",
    "--",
    "-.",
    ":",
    "-",
    "--",
    "-.",
    ":",
]
custom_colors = [
    "white" if "Corintisblack" in style_perso else "k",
    "white" if "Corintisblack" in style_perso else "k",
    "white" if "Corintisblack" in style_perso else "k",
    "white" if "Corintisblack" in style_perso else "k",
    "indianred",
    "indianred",
    "indianred",
    "indianred",
]
# plot 013 : Deltat vs Deltap, where identical design have identical color and identical temperature identical markers. In addition we want to put a horizontal greyline at DeltaT = 85C, to show that it is the limie
makeplot(
    plotoptions=PlotOptions(
        x_array=DP_sim_all,
        y_array=DT_sim_all,
        xlabel=delta_p_title,
        ylabel=r"$\Delta T$ $(C)$",
        xunits=delta_p_units,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_x_label=r"$\Delta P$ $(psi)$",
        second_x_units=ureg.psi,
        plotname=f"plot013_customfancy_DT_vs_DP_{chip}_{suffix}.png",
        color=custom_colors,
        marker=custom_markers,
        linestyle=custom_linestyles,
        markeredgecolor=custom_colors,
        markerfacecolor=custom_colors,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        hline_yvalue=85 * ureg.delta_degC,
    ),
    input_dir=plotinput.input_dir,
)

# Plot 0014 : flow rate versus pressure drop, invert axis
makeplot(
    plotoptions=PlotOptions(
        y_array=DP_sim_all,
        x_array=f_sim_all,
        ylabel=delta_p_title,
        xlabel=r"$f$ $(L/min)$",
        yunits=delta_p_units,
        xunits=ureg.liters / ureg.minutes,
        label=labels_all,
        second_y_label=r"$\Delta P$ $(psi)$",
        second_y_units=ureg.psi,
        plotname=f"plot0014_f_vs_DP_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)

# Plot 0015 : COP versus Qmax
makeplot(
    plotoptions=PlotOptions(
        x_array=Q_maximum_all,
        y_array=COP_max_all,
        xlabel=rf"Maximum Power at $T_j = {max_temperature_allowed.magnitude}C, $"
        + r"$Q^{maximum}$ $(W)$",
        ylabel=r"$COP$",
        xunits=ureg.W,
        yunits=ureg.dimensionless,
        label=labels_all,
        plotname=f"plot0015_COP_vs_Qmax-1_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)

# Plot 0016 : COPmax versus Qmax, invert axis
if is_chiplet_activated:
    makeplot(
        plotoptions=PlotOptions(
            x_array=Chiplet_DT_sim_all,
            y_array=COP_max_all,
            xlabel=r"Chiplet Temperature Difference $\Delta T$ $(C)$",
            ylabel=rf"$COP maximum obtained for T={max_temperature_allowed.magnitude}C$",
            xunits=ureg.delta_degC,
            yunits=ureg.dimensionless,
            label=labels_all,
            plotname=f"plot0016_COPmax_vs_ChipletDT-1_{chip}_{suffix}.png",
        ),
        input_dir=plotinput.input_dir,
    )

# Plot 0017 : COPmax vs flow rate with junction
makeplot(
    plotoptions=PlotOptions(
        x_array=f_sim_all,
        y_array=COP_max_all,
        xlabel=r"$f$ $(L/min)$",
        ylabel=rf"$COP$ maximum obtained for T={max_temperature_allowed.magnitude}$C$",
        xunits=ureg.liters / ureg.minutes,
        yunits=ureg.dimensionless,
        label=labels_all,
        plotname=f"plot017_COPmax_vs_flowrate_{chip}_{suffix}.png",
        y_log_scale=True,
    ),
    input_dir=plotinput.input_dir,
)

# Plot 018 : Delta T vs COPmax
makeplot(
    plotoptions=PlotOptions(
        x_array=COP_max_all,
        y_array=DT_sim_all,
        xlabel=rf"$COP$ maximum obtained for T={max_temperature_allowed.magnitude}$C$",
        ylabel=r"$\Delta T$ $(C)$",
        xunits=ureg.dimensionless,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_x_label=rf"$COP$ maximum obtained for T={max_temperature_allowed.magnitude}$C$",
        second_x_units=ureg.dimensionless,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        plotname=f"plot018_DT_vs_COPmax_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)

# Plot 0019 : COP normal vs flow rate with junction
makeplot(
    plotoptions=PlotOptions(
        x_array=f_sim_all,
        y_array=COP_normal_all,
        xlabel=r"$f$ $(L/min)$",
        ylabel=rf"$COP$ obtained with Q={Q_full[0].magnitude}$W$",
        xunits=ureg.liters / ureg.minutes,
        yunits=ureg.dimensionless,
        label=labels_all,
        plotname=f"plot019_COP_vs_flowrate_{chip}_{suffix}.png",
        y_log_scale=True,
    ),
    input_dir=plotinput.input_dir,
)

# Plot 020 : Delta T vs COP normal
makeplot(
    plotoptions=PlotOptions(
        x_array=COP_normal_all,
        y_array=DT_sim_all,
        xlabel=rf"$COP$ obtained with Q={Q_full[0].magnitude}$W$",
        ylabel=r"$\Delta T$ $(C)$",
        xunits=ureg.dimensionless,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_x_label=rf"$COP$ normal obtained with Q={Q_full[0].magnitude}$W$",
        second_x_units=ureg.dimensionless,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        plotname=f"plot020_DT_vs_COPmax_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)

# Plot 021 : Delta T vs pumping power
makeplot(
    plotoptions=PlotOptions(
        x_array=pumping_power_all,
        y_array=DT_sim_all,
        xlabel=r"Pumping Power $(W)$",
        ylabel=r"$\Delta T$ $(C)$",
        xunits=ureg.W,
        yunits=ureg.delta_degC,
        label=labels_all,
        second_y_shift=Tin_sim_all,
        second_y_label=r"$T_{junction}$ $(C)$",
        second_y_units=ureg.degC,
        plotname=f"plot021_DT_vs_PumpPower_{chip}_{suffix}.png",
    ),
    input_dir=plotinput.input_dir,
)

DP_sim = DP_sim.to_base_units()


# Save Output
for i in range(len(f_sim_all)):
    jsonname = f"DP_sweep_{prefix[i]}_{chip}.json"

    data = {
        "pressure_drop": {
            "title": "Pressure Drop",
            "unit": "(Pa)",
            "array": DP_sim_all[i].to_base_units().magnitude,
        },
        "inlet_temperature": {
            "title": "Inlet Temperature",
            "unit": "(C)",
            "array": Tin_sim_all[i].magnitude,
        },
        "flow_rate": {
            "title": "Flow Rate",
            "unit": "(m^3/s)",
            "array": f_sim_all[i].magnitude,
        },
        "junction_temperature_increase": {
            "title": "Junction Temperature Increase",
            "unit": "(C)",
            "array": DT_sim_all[i].magnitude,
        },
        "copmax": {
            "title": "COP factor at maximum temperature",
            "unit": "(-)",
            "array": COP_max_all[i].magnitude,
        },
        "cop": {
            "title": f"COP factor for power {Q_full}",
            "unit": "(-)",
            "array": COP_normal_all[i].magnitude,
        },
        "average_outlet_temperature": {
            "title": "Average Outlet Temperature",
            "unit": "(C)",
            "array": Tout_sim_all[i].magnitude,
        },
        "thermal_resistance": {
            "title": "Thermal Resistance",
            "unit": "(C/W)",
            "array": R_sim_all[i].magnitude,
        },
        "max_velocity": {
            "title": "Max Velocity",
            "unit": "(m/s)",
            "array": np.array([]),
        },
        "dissipated_power_maximum": {
            "title": "Dissipated Power (DT=maximum)",
            "unit": "(W)",
            "array": Q_maximum_all[i].magnitude,
        },
        "dissipated_power_density_maximum": {
            "title": "Dissipated Power Density (DT=maximum)",
            "unit": "(W/cm^2)",
            "array": Qd_maximum_all[i].magnitude,
        },
        "outlet_temperature_70C": {
            "title": "Average Outlet Temperature (DT=maximum)",
            "unit": "(C)",
            "array": Tout_maximum_all[i].magnitude,
        },
    }

    if not os.path.exists(plotinput.input_dir + plotinput.jsondir):
        # If the folder doesn't exist, create it
        os.makedirs(plotinput.input_dir + plotinput.jsondir)
        print(
            f"{Fore.GREEN}Folder '{plotinput.input_dir + plotinput.jsondir}' created.{Fore.RESET}"
        )
    with open(plotinput.input_dir + plotinput.jsondir + jsonname, "w") as json_file:
        json.dump(data, json_file, indent=4, cls=NumpyEncoder)

    print(
        f"{Fore.YELLOW}{plotinput.input_dir + plotinput.jsondir + jsonname} JSON file created{Fore.RESET}",
    )
