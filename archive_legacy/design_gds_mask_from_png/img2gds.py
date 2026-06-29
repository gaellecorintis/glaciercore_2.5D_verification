###############################################
# Author: Timothée Frei pour Corintis
# Version: 0.0.1
# Date: 18.08.2022
# copyright: Not made for distribution
###############################################

from unittest import result
from xml.sax.handler import property_xml_string
import cv2 as cv
import numpy as np
import gdstk
import pathlib


def moving_average(array, window_size):
    """
    Average the array using a moving window to smooth the array
    Args:
        array (_type_): Array to be smoothed
        window_size (_type_): Window size for the moving average
    Returns:
        _type_: Smoothed array
    """
    window = np.ones(int(window_size)) / float(window_size)
    n = array.shape[0]
    return np.convolve(np.tile(array, 2), window)[n : 2 * n]  # noqa E203


def img2gds(path2file, i_w, i_h, lay, datatype, blackthreshold):
    # Args:
    #       pathtofile: A string refering to the file location of the BMP file
    #       i_w: Output Physical Width (X) of the bmp image specified in micrometers
    #       i_h: Output Physical Height (Y) of the bmp image specified in micrometers ** NOT USED IN THIS VERSION **
    #       lay: Layer the bmp file should be placed in the GDS file
    #       datatype: datatype of the layer
    #       blackthreshold: Pixel value that refers to black, all other pixel values are rendered white
    #
    #       smoothing: if smoothing is required or not
    #       inv: inverted = 0 for BW inversion

    # Returns:
    #     polygones based on the image
    #
    ## Opening RGB image and convestion in greysclae
    origin_image = cv.imread(path2file)
    origin_image_grey = cv.cvtColor(origin_image, cv.COLOR_BGR2GRAY)
    print("Image grey")

    ## Def of empty arrays for image conversion in polygone
    origin_array = np.asarray(origin_image)
    print("Empty array ok")

    ## Thresholding BW image
    (ret, BW_image) = cv.threshold(
        origin_image_grey, blackthreshold, 255, cv.THRESH_BINARY
    )
    print("Image BW converted")

    ## Reading image as an array
    BW_array = np.asarray(BW_image)
    print("BW array")

    ## Find contours of the BW image

    BW_contour, hierarchy = cv.findContours(
        BW_image, cv.RETR_TREE, cv.CHAIN_APPROX_NONE
    )

    ## Converting array into gds
    gdspolygones = GDSimageconversion(
        i_w, i_h, BW_array, BW_contour, lay, datatype, blackthreshold
    )
    print("Image succesfully converted")
    return gdspolygones


## Decomposition of iamge into small rectangle based on the final width, image dimensions
def GDSimageconversion(i_w, i_h, BW_array, BW_contour, lay, datatype, blackthreshold):
    resolution_X = BW_array.shape[1]
    resolution_Y = BW_array.shape[0]
    ppX = i_w / resolution_X
    ppY = i_h / resolution_Y

    polygons = []
    for contour in BW_contour:
        down_sample = 4
        # Smooth and downsample
        x = moving_average(contour[:, 0, 0], window_size=8)[:-1:down_sample] * ppX
        y = moving_average(contour[:, 0, 1], window_size=8)[:-1:down_sample] * ppY
        polygon_points = [(xp, yp) for xp, yp in zip(x, y)]
        if polygon_points:
            polygons.append(gdstk.Polygon(polygon_points, layer=lay, datatype=datatype))

    return polygons

    try:
        return gdstk.contour(
            BW_array,
            blackthreshold / 255,
            ppX,
            precision=0.1,
            layer=lay,
            datatype=datatype,
        )
    except Exception as e:
        print("Error in gdstk.contour:" + e)
        None
    # resulting_pattern = None
    try:
        print("Start polygon merging")
        # return resulting_pattern
    except:
        print("Polygon merging has issues")
        None
