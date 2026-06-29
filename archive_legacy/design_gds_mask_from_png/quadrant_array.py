###############################################
# Author: Timothée Frei pour Corintis
# Version: 0.0.1
# Date: 18.08.2022
# copyright: Not made for distribution
###############################################

import gdstk
import math


def quadrantintegration (usedcell, targetcell, pos_x = 0, pos_y = 0):

    ## Args:
    #   - usedcell: cell to be arrayed
    #   - targetcell: cell containing the array of cell
    ##

    try:
        bbox = usedcell.bounding_box()
        dX = abs(bbox[0][0]-bbox[1][0])
        dY = abs(bbox[0][1]-bbox[1][1])
        # Top Left
        c_factor = 16
        ref1 = gdstk.Reference(usedcell, (pos_x-bbox[1][0]+c_factor,pos_y-bbox[0][1]), columns = 1, rows =1, x_reflection=False, rotation=0, spacing=(dX,dY))
        # Bottom Left
        ref2 = gdstk.Reference(usedcell, (pos_x-bbox[1][0]+c_factor,pos_y+bbox[0][1]), columns = 1, rows =1, x_reflection=True, rotation=0, spacing=(dX,dY))
        # Bottom Right
        ref3 = gdstk.Reference(usedcell, (pos_x+bbox[1][0]-c_factor,pos_y+bbox[0][1]), columns = 1, rows =1, x_reflection=False, rotation=math.pi, spacing=(dX,dY))
        # Top Right
        ref4 = gdstk.Reference(usedcell, (pos_x+bbox[1][0]-c_factor,pos_y-bbox[0][1]), columns = 1, rows =1, x_reflection=True, rotation=math.pi, spacing=(dX,dY))
        targetcell.add(ref1,ref2, ref3, ref4)
    except Exception as e:
        print("Error in quadrant_integration:") 
        None  