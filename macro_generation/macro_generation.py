#macro_generation.py
#author: Sestze
#
#In other scripts (path generation, prefab generation) we had a cubic spline
#that applied across the terrain to give us a gradual hill or valley to fight
#into, in addition to the other generated greebles.
#
#however, we can probably just make that as a standalone generation type
#and add whatever other generation type we'd like on top of it.

#in addition, we can use a single fliptype method (horizontal) and then
#make that apply to all other fliptypes using some basic math.

import random
import struct
import zlib
import math
import os

import copy

def cubic(val, xo, yo, xt, yt, dbg=0):
    if(dbg != 0):
        print("cubic spline function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))
    if(val < xo):
        val = xo
    if(val > xt):
        val = xt
    A = (-2 * (yt - yo)) / pow((xt - xo), 3)
    B = 3 * (yt - yo) / pow((xt - xo), 2)
    C = 0
    D = yo
    xin = val - xo

    retval = A * pow(xin, 3) + B * pow(xin, 2) + C * xin + D
    if(dbg != 0):
        print("Output: " + str(retval))
    return retval

def generate_map_using_macros (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1

    hspline = (random.uniform(1/32, 7/32), random.uniform(9/32, 15/32))
    hset = (random.uniform(-1, 1), random.uniform(-1, 1))
    hspline2 = (random.uniform(1/32, 7/32), random.uniform(9/32, 15/32))
    hset2 = (random.uniform(-1, 1), random.uniform(-1, 1))
    hspline3 = (random.uniform(1/32, 7/32), random.uniform(9/32, 15/32))
    hset3 = (random.uniform(-1, 1), random.uniform(-1, 1))

    vspline = (random.uniform(1/32, 7/32), random.uniform(9/32, 15/32))
    vspline2 = (random.uniform(17/32, 23/32), random.uniform(25/32, 31/32))

    if(fliptype == 4) or (fliptype == 5):
        vspline2 = (1 - vspline[1], 1 - vspline[0])
        hset2 = (hset[0], hset2[1])
        hset3 = hset

    basemap = []

    n = 0
    while n < height:
        m = 0
        row = []
        while m < width:
            cub1 = cubic(m, hspline[0]*width, hset[0], hspline[1]*width, hset[1])
            cub2 = cubic(m, hspline2[0]*width, hset2[0], hspline2[1]*width, hset2[1])
            cub3 = cubic(m, hspline3[0]*width, hset3[0], hspline3[1]*width, hset3[1])
            hght = 0
            if n < height * vspline[0]:
                hght = cub1
            elif n >= height * vspline[0] and n < height * vspline[1]:
                hght = cubic(n, vspline[0] * height, cub1, vspline[1] * height, cub2)
            elif n >= height * vspline[1] and n < height * vspline2[0]:
                hght = cub2
            elif n >= height * vspline2[0] and n < height * vspline2[1]:
                hght = cubic(n, vspline2[0] * height, cub2, vspline2[1] * height, cub3)
            else:
                hght = cub3
            hght = 100 * (hght + 1) / 2
            row.append(hght)
            m = m + 1
        basemap.append(row)
        n = n + 1

    genmap = copy.deepcopy(basemap)
    n = 0
    while n < height:
        m = 0
        while m < width:
            if(m > width / 2):
                genmap[n][m] = basemap[n][width - 1 - m]
            m = m + 1
        n = n + 1

    if(fliptype == 1):
        n = 0
        while n < height:
            m = 0
            while m < width:
                am = int(n / height * width)
                an = int(m / width * height)
                genmap[n][m] = basemap[an][am]
                m = m + 1
            n = n + 1

    if(fliptype == 2) or (fliptype == 3):
        n = 0
        while n < height:
            m = 0
            while m < width:
                r = pow(pow(m - width/2, 2) + pow(n - height/2, 2),0.5) / pow(2, 0.5)
                tht = math.atan2(n - height / 2, m - width / 2)
                sgn = 1
                if(fliptype == 2):
                    sgn = -1
                am = int(r * math.cos(tht + sgn * math.pi / 4) + width / 2)
                an = int(r * math.sin(tht + sgn * math.pi / 4) + width / 2)
                genmap[n][m] = basemap[an][am]
                m = m + 1
            n = n + 1

    if(fliptype == 4) or (fliptype == 5):
        n = 0
        while n < height:
            m = 0
            while m < width:
                r = pow(pow(m - width/2, 2) + pow(n - height/2, 2),0.5) / pow(2, 0.5)
                maxr = pow(pow(width / 2, 2) + pow(height / 2, 2), 0.5)
                disp = (r / maxr) / pow(2, 0.5)
                add = 0
                if(fliptype == 5):
                    add = math.pi / 4
                tht = 4 * (1 + (add + math.atan2(n - height / 2, m - width / 2) / math.pi)) / 2
                am = int((width * disp) % width)
                an = int((tht * height) % height)
                genmap[n][m] = basemap[an][am]
                m = m + 1
            n = n + 1

    print("macro generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("We need too many external arguments to run from this script now. Run srmg_1.py")
    print("finished")
