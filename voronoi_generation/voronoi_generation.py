#prefab_generation.py
#author: Sestze
#
#Creates a voronoi diagram with a set of different heightmap points.

#How does this work, step by step?
#   - Randomly select number of voronoi points in area
#   - Assign voronoi points
#       - Startpos points at a fixed starting height
#       - All remaining voronoi points must be placed at least (mapsizex + mapsizey) / 2 * 2 radius away from other points
#   - Generate voronoi 
#   - once fodder is placed, we mirror the pixels accordingly.
#   - once mirrored, we blur the mirrored portion, as well as blur the entire map slightly.
#   - ship back the generated map and fliptype.

import random
import struct
import zlib
import math
import os

from PIL import Image

def generate_map_using_voronoi (map_properties):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = random.randint(3, 7) * 10

    fliptype = random.randint(0, 2)
    if(width > height):
        fliptype = random.choice([0, 2])
    if(height > width):
        fliptype = random.choice([1, 2])

    FlipName = ["Horizontal", "Vertical", "Quad"]

    print("Map Statistics: ")
    print("\tSeed: " + str(map_properties["seed"]))
    print("\twidth: " + str(map_properties["mapsizex"]))
    print("\theight: " + str(map_properties["mapsizey"]))
    print("\tstartheight: " + str(startheight))
    print("\tfliptype: " + FlipName[fliptype])

    #build the basic map:
    #cubic spline for edges
    def cubic(val, xo, yo, xt, yt, dbg=0):
        if(dbg != 0):
            print("cubic spline function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))
        A = (-2 * (yt - yo)) / pow((xt - xo), 3)
        B = 3 * (yt - yo) / pow((xt - xo), 2)
        C = 0
        D = yo
        xin = val - xo

        retval = A * pow(xin, 3) + B * pow(xin, 2) + C * xin + D
        if(dbg != 0):
            print("Output: " + str(retval))
        return retval

    def clamp(val, l, u):
        if l > val:
            return l
        if u < val:
            return u
        return val
    #start points
    voronoi_max = random.randint(8, 12)
    if(fliptype == 2):
        voronoi_max = voronoi_max // 2
    voronoi_points = []
    
    backline = min(4, map_properties["numplayers"])
    frontline = map_properties["numplayers"] - backline
    
    if(fliptype == 0):
        xset = min(int(width / (map_properties["mapsizex"] * 2)), int(width / 16))
        n = 0
        while n < backline:
            yset = int(height * (n + 1) / (backline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        xset = min(int(4 * width / (map_properties["mapsizex"] * 2)), int(4 * width / 16))
        while n < frontline:
            yset = int(height * (n + 1) / (frontline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
    elif(fliptype == 1):
        yset = min(int(height / (map_properties["mapsizey"] * 2)), int(height / 16))
        n = 0
        while n < backline:
            xset = int(width * (n + 1) / (backline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        yset = min(int(4 * height / (map_properties["mapsizex"] * 2)), int(4 * height / 16))
        while n < frontline:
            xset = int(width * (n + 1) / (frontline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
    elif(fliptype == 2):
        radius = 4 * min(int(min(width, height) / (min(map_properties["mapsizex"], map_properties["mapsizey"]) * 2)), int(min(width, height) / 16))
        n = 0
        while n < backline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        radius = int(1.5 * min(4 * int(min(width, height) / (2 * min(map_properties["mapsizex"], map_properties["mapsizey"]))), int(4 * min(width, height) / 16)))
        n = 0
        while n < frontline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1

    #other generated points
    mindist = (map_properties["mapsizex"] + map_properties["mapsizey"]) / 2 * 2

    n = 0
    while (n < voronoi_max):
        xs = 0
        ys = 0
        xtot = width
        ytot = height

        if(fliptype == 0) or (fliptype == 2):
            xs = 4 * width // (map_properties["mapsizex"] * 2)
        if(fliptype == 1) or (fliptype == 2):
            ys = 4 * height // (map_properties["mapsizey"] * 2)

        xpos = random.randint(xs, xtot)
        ypos = random.randint(ys, ytot)

        setheight = random.randint(2, 8) * 10
        m = 0
        while (m < len(voronoi_points)):
            dst = pow(pow((voronoi_points[m][0] - xpos), 2) + pow((voronoi_points[m][1] - ypos), 2), 0.5)
            if(dst < mindist):
                m = -1
                xpos = random.randint(xs, xtot)
                ypos = random.randint(ys, ytot)
            m = m + 1
        voronoi_points.append([xpos, ypos, setheight])
        n = n + 1
        
    #set heights based on voronoi
    voronoi_type = random.randint(0, 1)
    if(voronoi_type == 0):
        print("\tvoronoi_type: Euclid")
    if(voronoi_type == 1):
        print("\tvoronoi_type: Manhattan")
    
    n = 0
    while (n < height):
        row = []
        m = 0
        while (m < width):
            dstmin = 999999
            vn_height = startheight
            r = 0
            while (r < len(voronoi_points)):
                dst = 0
                if(voronoi_type == 0):
                    #euclid
                    dst = pow(pow(m - voronoi_points[r][0], 2) + pow(n - voronoi_points[r][1], 2), 0.5)
                    if(dst < dstmin):
                        dstmin = dst
                        vn_height = voronoi_points[r][2]
                    
                if(voronoi_type == 1):
                    #manhattan
                    dst = abs(m - voronoi_points[r][0]) + abs(n - voronoi_points[r][1])
                    if(dst < dstmin):
                        dstmin = dst
                        vn_height = voronoi_points[r][2]
                    
                r = r + 1
            row.append(vn_height)
            m = m + 1
        genmap.append(row)
        n = n + 1

    #flip the map
    if(fliptype == 0):
        n = 0
        while n < height:
            m = 0
            while m < (width / 2):
                genmap[n][(width - 1) - m] = genmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 1):
        n = 0
        while n < (height / 2):
            m = 0
            while m < width:
                genmap[(height - 1) - n][m] = genmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 2):
        n = 0
        while n < (height / 2):
            m = 0
            while m < (width / 2):
                genmap[(height - 1) - n][m] = genmap[n][m]
                genmap[n][(width - 1) - m] = genmap[n][m]
                genmap[(height - 1) - n][(width - 1) - m] = genmap[n][m]
                m = m + 1
            n = n + 1

    #blur based on fliptype to make edges a bit nicer

    def AverageCoordsInCircle(keyx, keyy, coords, blurradius):
        boundy = blurradius
        boundx = blurradius
        n = keyy - boundy
        totval = 0
        cnt = 0
        while (n < (keyy + boundy)):
            m = keyx - boundx
            while (m < (keyx + boundx)):
                distval = 0
                hgval = 0
                nux = clamp(m, 0, len(coords[0]) - 1)
                nuy = clamp(n, 0, len(coords) - 1)
                distval = pow(pow(keyx - m, 2) + pow(keyy - n, 2), 0.5)
                hgval = coords[nuy][nux]
                if(distval <= blurradius):
                    totval = totval + hgval
                    cnt = cnt + 1
                m = m + 1
            n = n + 1
        if(cnt > 0):
            totval = totval / cnt
        else:
            nux = clamp(keyx, 0, len(coords[0]) - 1)
            nuy = clamp(keyy, 0, len(coords) - 1)
            totval = coords[nuy][nux]
        return totval
    print("blurring")
    #going to clamp this
    scaleblur = 20
    if(fliptype == 0) or (fliptype == 2):
        n = 0
        while (n < height):
            m = width // 2 - scaleblur
            while(m < (width // 2 + scaleblur)):
                dst = max(-1 * abs(m - width // 2) + 20, 0)
                genmap[n][m] = AverageCoordsInCircle(m, n, genmap, dst)
                m = m + 1
            n = n + 1
    if(fliptype == 1) or (fliptype == 2):
        n = height // 2 - scaleblur
        while (n < (height // 2 + scaleblur)):
            m = 0
            while(m < width):
                dst = max(-1 * abs(n - height // 2) + 20, 0)
                genmap[n][m] = AverageCoordsInCircle(m, n, genmap, dst)
                m = m + 1
            n = n + 1

    #Global blur.
    blurrad = 10 #blurs all pix around 10 units of the pixel
    n = 0
    while(n < height):
        m = 0
        while (m < width):
            genmap[n][m] = AverageCoordsInCircle(m, n, genmap, blurrad)
            m = m + 1
        n = n + 1

    print("voronoi generation finished")

    return genmap, fliptype

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("Running to debug")
    map_properties = {
        "mapsizex": 12,
        "mapsizey": 12,
        "seed": 333666999,
        "numplayers": 8,
        "generation_type": "voronoi"     #normal, prefab, voronoi
        }
    genmap = generate_map_using_prefabs(map_properties)
    #print(str(genmap))
    print("finished")
