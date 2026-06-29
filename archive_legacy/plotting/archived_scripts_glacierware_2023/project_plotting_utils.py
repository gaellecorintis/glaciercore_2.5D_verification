"""General functions and input parameters that are project specifics.
"""
import csv
import json
import os
import platform
import subprocess

import numpy as np
from pint import UnitRegistry

ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
ureg.setup_matplotlib(True)
import matplotlib.pyplot as plt
from attrs import define, field, validators
from colorama import Fore
from pylab import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__name__))
full_abs_path_utils = os.path.join(os.path.dirname(SCRIPT_DIR), "utils")
style_perso = os.path.join(
    full_abs_path_utils, "plotting_styles", "Corintis.mplstyle"
)  # alternatively use Corintisblack.mplstyle
# ====================
# Project specific :
# ====================
chip = "Tutorial_example"
powermap_path = "../powermap/powermap_v1/powermap_example.csv"
txtname_chip = f"pressure_sweep_{chip}.txt"
delta_p_title = r"$\Delta P$ $(mbar)$"
delta_p_units = ureg.millibar
# These are all the default options for the lines and markers they can be customized in the makeplot sections be editing a specific array.
sizes = [14, 14, 14, 14, 14, 14, 14, 14]
markers = ["o", "s", "D", "v", "^", "h", "<", ">", "p", "d", "x", "*"]
linestyles = ["-", "--", "-.", ":", "solid", "dotted", "dashed", "--"]
markeredgecolors = [
    "white" if "Corintisblack" in style_perso else "k",
    "red",
    "indianred",
    "blue",
    "magenta",
    "orange",
    "cyan",
    "green",
    "gray",
]
fills = ["none", "none", "none", "none", "none", "none", "none", "none"]
colors = [
    "white" if "Corintisblack" in style_perso else "k",
    "red",
    "indianred",
    "blue",
    "magenta",
    "orange",
    "cyan",
    "green",
    "gray",
]


def read_power_map_file(power_map_file):
    """Equivalent of glaciercore function of the same name, returning only the dimensions of the power map.

    Args:
        power_map_file (string): path to the power map file

    Returns:
        floats: width and length of the power map in meters
    """
    # Clean file
    if platform.system() == "Darwin":
        subprocess.call(["sed", "-i", "", "-e", "s/\r//", power_map_file])
    else:
        subprocess.call(["sed", "-i", "-e", "s/\r//", power_map_file])
    with open(power_map_file, encoding="utf-8-sig", newline="") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", lineterminator="\n")
        first_line = next(csv_reader)
        cell_width, cell_length = map(float, first_line[:2])
        power_map = [list(map(float, row)) for row in csv_reader]
        power_array = np.flip(np.flip(np.array(power_map, dtype=float)), axis=1)
        chip_width, chip_length = (
            power_array.shape[1] * cell_width,
            power_array.shape[0] * cell_length,
        )

    return (chip_width, chip_length)


def extract_source_directory(indir):
    """Extract the source directory in which indir is located.

    Args:
        indir (string): the path to a directory or file.

    Returns:
        string: the folder one level above.
    """
    split_string = indir.split("/")
    source_directory = split_string[0]
    return source_directory


def extract_substring(input_dir):
    """Given a directory absolute path, extract the last substring and the source directory.

    Args:
        input_dir (string): The full path to a directory or file.

    Returns:
        strings: the directory alone, and the source directory in which it is.
    """
    split_string = input_dir.strip("/").split("/")
    extracted_substring = split_string[-1]
    source_directory = "/".join(split_string[:-1]) + "/"
    return extracted_substring, source_directory


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


@define
class DataPlotInput:
    """Class that contains the input data for the plotting script."""

    input_dir = field(default="", validator=[validators.instance_of(str)])
    jsondir = field(default="", validator=[validators.instance_of(str)])
    suffix = field(default="", validator=[validators.instance_of(str)])
    chip = field(default="", validator=[validators.instance_of(str)])
    power_map_width = field(default=25.0 / 2.0 * ureg.millimeters)
    power_map_length = field(default=32.5 / 2.0 * ureg.millimeters)
    max_temperature_allowed = field(default=105 * ureg.degC)


@define
class PlotOptions:
    """Class that contains the options for the plot, figure considered."""

    x_array = field(default=[])
    y_array = field(default=[])
    xlabel = field(
        default=r"$\Delta P$ $(psi)$", validator=[validators.instance_of(str)]
    )
    ylabel = field(default=r"$f$ $(L/min)$", validator=[validators.instance_of(str)])
    xunits = field(default=ureg.liters / ureg.minutes)
    yunits = field(default=ureg.millibar)
    second_x_label = field(default=None)
    second_x_units = field(default=None)
    second_y_label = field(default=None)
    second_y_units = field(default=None)
    second_y_shift = field(default=[])
    markersize = field(default=sizes)
    marker = field(default=markers)
    linestyle = field(default=linestyles)
    markeredgecolor = field(default=markeredgecolors)
    markerfacecolor = field(default=colors)
    fillstyle = field(default=fills)
    color = field(default=colors)
    linewidth = field(default=3)
    label = field(default="")
    markevery = field(default=1)
    x_lower_bound = field(default=None)
    x_upper_bound = field(default=None)
    y_lower_bound = field(default=None)
    y_upper_bound = field(default=None)
    legendloc = field(default="best")
    legendsize = field(default=14)
    frameon = field(default=False)
    plotname = field(default="plot", validator=[validators.instance_of(str)])
    bbox_inches = field(default="tight")
    hline_yvalue = field(default=None)
    hline_xmin = field(default=None)
    hline_xmax = field(default=None)
    hline_color = field(default="gray")
    hline_linestyle = field(default=":")
    hline_linewidth = field(default=2.0)
    x_log_scale:bool = field(default=False)
    y_log_scale:bool = field(default=False)

    def initialise_second_shift(self):
        self.second_y_shift = [[0.0, 0.0] * self.yunits]


def get_plot_bounds(plotoptions: PlotOptions, axis):
    """Get the plot bounds, based on the given axis.

    Args:
        plotoptions (PlotOptions): the current plotoptions settings
        axis (matplotlib.axes._axes.Axes): the current axis

    Returns:
        floats: bounds for x and y axis: x_lower_bound, x_upper_bound, y_lower_bound, y_upper_bound
    """
    x_lower_bound = (
        1.05 * axis.get_xlim()[0] - 0.05 * (axis.get_xlim()[1])
        if plotoptions.x_lower_bound is None
        else plotoptions.x_lower_bound
    )
    x_upper_bound = (
        1.05 * axis.get_xlim()[1]
        if plotoptions.x_upper_bound is None
        else plotoptions.x_upper_bound
    )
    y_lower_bound = (
        1.05 * axis.get_ylim()[0] - 0.05 * (axis.get_ylim()[1])
        if plotoptions.y_lower_bound is None
        else plotoptions.y_lower_bound
    )
    y_upper_bound = (
        1.05 * axis.get_ylim()[1]
        if plotoptions.y_upper_bound is None
        else plotoptions.y_upper_bound
    )
    return x_lower_bound, x_upper_bound, y_lower_bound, y_upper_bound


def add_horizontal_line_to_plot(plotoptions: PlotOptions, axis):
    """Add an horizontal line to a plot.

    Args:
        plotoptions (PlotOptions): the plot options
        axis (matplotlib.axes._axes.Axes): the current axis
    """
    x_lower_bound, x_upper_bound, _, _ = get_plot_bounds(plotoptions, axis)
    hline_x_lower_bound = (
        x_lower_bound if plotoptions.hline_xmin is None else plotoptions.hline_xmin
    )
    hline_x_upper_bound = (
        x_upper_bound if plotoptions.hline_xmax is None else plotoptions.hline_xmax
    )
    axis.hlines(
        y=plotoptions.hline_yvalue,
        xmin=hline_x_lower_bound,
        xmax=hline_x_upper_bound,
        colors=plotoptions.hline_color,
        linestyle=plotoptions.hline_linestyle,
        linewidth=plotoptions.linewidth,
    )


def makeplot(plotoptions: PlotOptions, input_dir):
    """Function that follows the full process of making a plot and saving it as a png.

    Args:
        plotoptions (PlotOptions): the plotoptions
        input_dir (string): the path to the folder where we want to save the plot
    """
    figure, axis = plt.subplots()  # create a new figure
    axis.set_xlabel(plotoptions.xlabel)
    axis.xaxis.set_units(plotoptions.xunits)
    axis.set_ylabel(plotoptions.ylabel)
    axis.yaxis.set_units(plotoptions.yunits)
    axis_2=None
    axis_3=None
    if plotoptions.second_x_label is not None:
        axis_2 = axis.twiny()
        axis_2.set_xlabel(plotoptions.second_x_label)
        axis_2.xaxis.set_units(plotoptions.second_x_units)
    if plotoptions.second_y_label is not None:
        axis_3 = axis.twinx()
        axis_3.set_ylabel(plotoptions.second_y_label)
        axis_3.yaxis.set_units(plotoptions.second_y_units)
        if len(plotoptions.second_y_shift) == 0:
            plotoptions.initialise_second_shift()
    for index in range(len(plotoptions.x_array)):
        axis.plot(
            plotoptions.x_array[index],
            plotoptions.y_array[index],
            markersize=plotoptions.markersize[index],
            markerfacecolor=plotoptions.markerfacecolor[index],
            c=plotoptions.color[index],
            marker=plotoptions.marker[index],
            markeredgecolor=plotoptions.markeredgecolor[index],
            markevery=plotoptions.markevery,
            linestyle=plotoptions.linestyle[index],
            linewidth=plotoptions.linewidth,
            fillstyle=plotoptions.fillstyle[index],
            label=plotoptions.label[index],
        )
        if plotoptions.second_x_label is not None:
            axis_2.plot(
                plotoptions.x_array[index].to(plotoptions.second_x_units),
                plotoptions.y_array[index],
                markersize=plotoptions.markersize[index],
                markerfacecolor=plotoptions.markerfacecolor[index],
                c=plotoptions.color[index],
                marker=plotoptions.marker[index],
                markeredgecolor=plotoptions.markeredgecolor[index],
                markevery=plotoptions.markevery,
                linestyle=plotoptions.linestyle[index],
                linewidth=plotoptions.linewidth,
                fillstyle=plotoptions.fillstyle[index],
                label=plotoptions.label[index],
            )
    x_lower_bound, x_upper_bound, y_lower_bound, y_upper_bound = get_plot_bounds(
        plotoptions, axis
    )
    axis.set_xlim([x_lower_bound, x_upper_bound])
    axis.set_ylim([y_lower_bound, y_upper_bound])
    if plotoptions.second_x_label is not None:
        axis_2.set_xlim(
            [
                (x_lower_bound * plotoptions.xunits)
                .to(plotoptions.second_x_units)
                .magnitude,
                (x_upper_bound * plotoptions.xunits)
                .to(plotoptions.second_x_units)
                .magnitude,
            ]
        )
        axis_2.set_ylim([y_lower_bound, y_upper_bound])
    if plotoptions.second_y_label is not None:
        axis_3.set_ylim(
            [
                (
                    (y_lower_bound * plotoptions.yunits).to_base_units()
                    + plotoptions.second_y_shift[0][0].to_base_units()
                )
                .to(plotoptions.second_y_units)
                .magnitude,
                (
                    (y_upper_bound * plotoptions.yunits).to_base_units()
                    + plotoptions.second_y_shift[0][0].to_base_units()
                )
                .to(plotoptions.second_y_units)
                .magnitude,
            ]
        )
        axis_3.set_xlim([x_lower_bound, x_upper_bound])
    if plotoptions.hline_yvalue is not None:
        add_horizontal_line_to_plot(plotoptions, axis)
    if plotoptions.x_log_scale:
        axis.set_xscale("log")
        axis.autoscale()
    if plotoptions.y_log_scale:
        axis.set_yscale("log")
        axis.autoscale()
    axis.legend(
        loc=plotoptions.legendloc,
        frameon=plotoptions.frameon,
        fontsize=plotoptions.legendsize,
    )
    # saving the plot
    figure.savefig(
        input_dir + plotoptions.plotname, bbox_inches=plotoptions.bbox_inches
    )
    plt.close(figure)
    print(f"{plotoptions.plotname} created")


def get_problem_data(json_path, field="problem_data"):
    """Get the field of a json file.

    Args:
        json_path (string): path to the json file
        field (string, optional): field to extract. Defaults to "problem_data".

    Returns:
        dictionary: the value of the field
    """
    print(f"opening {json_path}")
    with open(json_path) as sim_data:
        json_data = json.load(sim_data)
        try:
            return json_data.pop(field)
        except KeyError as e:
            raise RuntimeError(f"Geometry data not specified in {json_path}") from e


def update_savedparams(param_dict, folder=None, file: str = "result_param.csv"):
    """Function that makes the file if it exists, and updates it if it does not. Made for csv format, in python3

    Args:
        param_dict (_type_): an input dictionary
        folder (_type_, optional): path to the folder. Defaults to None.
        file (str, optional): name of the file. Defaults to None.
    """
    if folder is None:
        folder = os.getcwd()
    if not (os.path.exists(folder)):
        os.makedirs(folder)
    dict_info = list(param_dict.keys())
    if os.path.exists(folder + file):
        update_file(folder, file, dict_info, param_dict)
    else:
        with open(folder + file, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=dict_info)
            writer.writeheader()
            writer.writerows([param_dict])


def update_file(folder, file: str, dict_info, param_dict):
    """Update a dictionary in a csv file.

    Args:
        folder (_type_): path to the folder
        file (str): file name
        dict_info (_type_): dictionary to update
        param_dict (_type_): specific dictionary parameter
    """
    with open(folder + file, newline="") as f:
        reader = csv.reader(f)
        final_dict = next(reader)
        _ = next(reader)
    counter = 0
    for key in dict_info:
        if key not in final_dict:
            final_dict.append(key)
            counter += 1
    for key in final_dict:
        if key not in dict_info:
            param_dict[key] = "not defined"
    source = folder + file
    target = folder + file[:-4] + "new" + file[-4:]
    with open(source, newline="") as inFile, open(target, "w", newline="") as outfile:
        r = csv.reader(inFile)
        w = csv.writer(outfile)
        next(r, None)
        w.writerow(final_dict)
        for row in r:
            for _ in range(counter):
                row.append("not defined")
            w.writerow(row)
    os.rename(target, source)
    with open(folder + file, "a") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=final_dict)
        writer.writerows([param_dict])
        csvfile.close()
