#blot_generation.py
#author: Sestze
#
#creates a randomized heightmap using "blots"

import random
import struct
import zlib
import math
import os

import copy

from PIL import Image

def clampit(v, l, u):
    if(v < l):
        return l
    if(v > u):
        return u
    return v

def interpolate(val, l, u):
    p = val
    #smoothstep
    ret = (u - l) * (3 - p * 2) * p * p + l
    return ret

def findkey(var, maxvar, sd):
    ret = int(var * sd / maxvar)

    return ret

def generate_map_using_blots (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1

    edgeheight = random.uniform(-1, 1)
    #startheight = random.uniform(-1, 1)
    startheight = 0

    heights = []
    #build the edges first
    edges = 32
    n = 0
    while n < edges:
        tht = (n / edges) * 2 * math.pi
        xv = math.cos(tht) * width / pow(2, 0.5) + width / 2
        yv = math.sin(tht) * height / pow(2, 0.5) + height / 2
        hght = edgeheight
        heights.append([xv, yv, hght, 1])
        n = n + 1

    n = 0
    while n < len(start_positions):
        xv = start_positions[n][0] * width
        yv = start_positions[n][1] * height
        heights.append([xv, yv, startheight, 4, 8])
        n = n + 1

    blots = 64
    if(fliptype == 4) or (fliptype == 5):
        blots = blots / 2
    n = 0
    while n < blots:
        xv = random.uniform(0, 1) * width
        yv = random.uniform(0, 1) * height
        if(fliptype == 0) or (fliptype == 4):
            xv = xv / 2
        if(fliptype == 1) or (fliptype == 4):
            yv = yv / 2
        if(fliptype == 2):
            ym = (height - xv) / height
            yv = random.uniform(0, ym) * height
        if(fliptype == 3):
            ym = xv / height
            yv = random.uniform(ym, 1) * height
        if(fliptype == 5):
            xm = (-1 * abs(yv - height / 2) + width / 2) / width
            xv = random.uniform(0, xm) * width
        hght = random.uniform(-1, 1)
        lum = random.uniform(0, 4)
        focus = random.uniform(2, 4)
        heights.append([xv, yv, hght, lum, focus])
        #print(str(xv) + ", " + str(yv))
        n = n + 1

    along = 16

    if(fliptype == 0) or (fliptype == 4):
        n = 0
        while n <= along:
            xv = width / 2
            yv = n / along * height
            hght = random.uniform(-0.5, 0.5)
            lum = random.uniform(0.5, 1)
            focus = random.uniform(2, 3)
            heights.append([xv, yv, hght, lum, focus])
            n = n + 1
    if(fliptype == 1) or (fliptype == 4):
        n = 0
        while n <= along:
            xv = n / along * width
            yv = height / 2
            hght = random.uniform(-0.5, 0.5)
            lum = random.uniform(0.5, 1)
            focus = random.uniform(2, 3)
            heights.append([xv, yv, hght, lum, focus])
            n = n + 1
    if(fliptype == 2):
        n = 0
        while n <= along:
            xv = n / along * width
            yv = height - n / along * height
            hght = random.uniform(-0.5, 0.5)
            lum = random.uniform(0.5, 1)
            focus = random.uniform(2, 3)
            heights.append([xv, yv, hght, lum, focus])
            n = n + 1
    if(fliptype == 3):
        n = 0
        while n <= along:
            xv = n / along * width
            yv = n / along * height
            hght = random.uniform(-0.5, 0.5)
            lum = random.uniform(0.5, 1)
            focus = random.uniform(2, 3)
            heights.append([xv, yv, hght, lum, focus])
            n = n + 1
    if(fliptype == 5):
        n = 0
        while n <= along:
            yv = n / along * height
            xv = -1 * abs(yv - height / 2) + width / 2
            hght = random.uniform(-0.5, 0.5)
            lum = random.uniform(0.5, 1)
            focus = random.uniform(2, 3)
            heights.append([xv, yv, hght, lum, focus])
            n = n + 1
    subdiv = 128 * max(map_properties["mapsizex"], map_properties["mapsizey"]) / 12

    subdivs = []

    fuz = -0.05
    mindst = 0

    n = 0
    while n < subdiv + 1:
        row = []
        m = 0
        while m < subdiv + 1:
            xv = width * m / subdiv
            yv = height * n / subdiv

            dsts = [*range(len(heights))]
            sod = 0
            hght = 0
            r = 0
            while(r < len(heights)):
                dsts[r] = pow(pow(xv - heights[r][0], 2) + pow(yv - heights[r][1], 2), 0.5)
                wght = 1
                exp = 2
                if(len(heights[r]) > 3):
                    wght = heights[r][3]
                if(len(heights[r]) > 4):
                    exp = heights[r][4]
                hght = hght + pow(exp, fuz * dsts[r]) * heights[r][2] * wght
                sod = sod + pow(exp, fuz * dsts[r]) * wght
                r = r + 1
            hght = hght / sod
            row.append(hght)
            m = m + 1
        subdivs.append(row)
        n = n + 1

    heightmap = []
    n = 0
    while n < height:
        row = []
        m = 0
        while m < width:
            hght = 0
            keyh = findkey(n, height, subdiv)
            keyw = findkey(m, width, subdiv)

            am = (m * subdiv / width - keyw)
            an = (n * subdiv / height - keyh)

            ith1 = interpolate(am, subdivs[keyh][keyw], subdivs[keyh][keyw+1])
            ith2 = interpolate(am, subdivs[keyh+1][keyw], subdivs[keyh+1][keyw+1])
            itv = interpolate(an, ith1, ith2)

            hght = 100 * (itv + 1) / 2
            
            row.append(hght)
            m = m + 1
        heightmap.append(row)
        n = n + 1    

    print("blot generation finished")
    return heightmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("We need too many external arguments to run from this script now. Run srmg_1.py")
    print("finished")
