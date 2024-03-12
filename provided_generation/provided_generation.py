#provided_generation.py
#author: Sestze
#
#imports a heightmap file (.bmp) and outputs a generated heightmap.

import random
import struct
import zlib
import math
import os

from PIL import Image

def generate_map_using_provided (map_properties):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    img_input_filename = map_properties["provided_filename"]

    ts = []
    with Image.open(img_input_filename) as tex:
        tex = tex.resize((width, height))
        ts = list(tex.getdata())
        tex.close()

    n = 0
    while n < height:
        m = 0
        row = []
        while m < width:
            index = n * width + m
            #convert to grayscale, then scale from 0-100
            gry = (ts[index][0] + ts[index][1] + ts[index][2]) / 3
            gry = gry * 100 / 255
            row.append(gry)
            m = m + 1
        genmap.append(row)
        n = n + 1

    print("provided generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("There's too many inputs required for this script, run srmg_1.py")
    #print(str(genmap))
    print("finished")
