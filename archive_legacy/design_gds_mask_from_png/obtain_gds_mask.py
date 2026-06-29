###############################################
# Author: Timothée Frei pour Corintis
# Version: 0.0.1
# Date: 18.08.2022
# copyright: Not made for distribution
###############################################


import numpy as np
import gdstk
import img2gds
import quadrant_array
import sys
import pathlib
from colorama import Fore

if __name__ == "__main__":
    # Creating the library of cells
    path2file = f"{sys.argv[1]}"
    chip_dimensions = 224e2, 314e2
    print(
        f"{Fore.RED} ATTENTION! Be careful as for now the chip dimensions are hard-coded!!!! Specify the dimensions of the full chip manually. In the present case, the chip is {chip_dimensions[0]} micrometers x {chip_dimensions[1]} micrometers. {Fore.RESET} "
    )
    lib = gdstk.Library()
    main = lib.new_cell("Main")
    firstcell = lib.new_cell("First")

    # Layer/datatype definitions for each step in the fabrication
    ld = {
        "full etch": {"layer": 1, "datatype": 1},
        "partial etch": {"layer": 2, "datatype": 2},
        "lift-off": {"layer": 0, "datatype": 0},
        "kambucha": {"layer": 4, "datatype": 4},
    }
    path = pathlib.Path(__file__).parent.absolute()

    # inserting references to cells in the main cell
    main.add(gdstk.Reference(firstcell, (0, 0), x_reflection=True, rotation=0))
    # Add in fourthcell polygones from the targeted image > See img2gds.py for details
    datatype = 2
    layer = 1
    imageimported = img2gds.img2gds(
        path2file, chip_dimensions[0], chip_dimensions[1], datatype, layer, 119
    )
    firstcell.add(imageimported[0])
    for polygon in imageimported[1:]:
        firstcell.add(polygon)

    # add a bounding boy to the imported image
    polygon_bb = gdstk.rectangle((0, 0), chip_dimensions, layer=2)
    firstcell.add(polygon_bb)

    lib.write_gds(path / f"{path2file[:-4]}.gds")
    print("GDS written")
