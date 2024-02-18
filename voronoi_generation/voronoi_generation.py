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

    startheight = random.randint(4, 6) * 10
    frontheight = random.randint(3, 7) * 10

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
    voronoi_max = random.randint(4, 8)
    voronoi_points = []
    
    backline = min(4, map_properties["numplayers"])
    frontline = max(map_properties["numplayers"] - backline, 0)
    
    if(fliptype == 0):
        xset = max(int(width / (map_properties["mapsizex"] * 2)), int(width / 16))
        n = 0
        while n < backline:
            yset = int(height * (n + 1) / (backline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        n = 0
        xset = max(int(3 * width / (map_properties["mapsizex"] * 2)), int(3 * width / 16))
        while n < frontline:
            yset = int(height * (n + 1) / (frontline + 1))
            voronoi_points.append([xset, yset, frontheight])
            n = n + 1
    elif(fliptype == 1):
        yset = max(int(height / (map_properties["mapsizey"] * 2)), int(height / 16))
        n = 0
        while n < backline:
            xset = int(width * (n + 1) / (backline + 1))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        n = 0
        yset = max(int(3 * height / (map_properties["mapsizex"] * 2)), int(3 * height / 16))
        while n < frontline:
            xset = int(width * (n + 1) / (frontline + 1))
            voronoi_points.append([xset, yset, frontheight])
            n = n + 1
    elif(fliptype == 2):
        radius = 3 * max(int(min(width, height) / (min(map_properties["mapsizex"], map_properties["mapsizey"]) * 2)), int(min(width, height) / 16))
        n = 0
        while n < backline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            voronoi_points.append([xset, yset, startheight])
            n = n + 1
        radius = int(1.5 * max(3 * int(min(width, height) / (2 * min(map_properties["mapsizex"], map_properties["mapsizey"]))), int(3 * min(width, height) / 16)))
        n = 0
        while n < frontline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            voronoi_points.append([xset, yset, frontheight])
            n = n + 1
    #other generated points
    mindist = 100 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
    n = 0
    while (n < voronoi_max):
        xtot = width - mindist
        ytot = height - mindist
        xs = mindist
        ys = mindist

        if(fliptype == 0) or (fliptype == 2):
            xtot = width // 2
            xs = max(int(5 * width / (map_properties["mapsizex"] * 2)), int(5 * width / 16))
        if(fliptype == 1) or (fliptype == 2):
            ytot = height // 2
            xy = max(int(5 * height / (map_properties["mapsizey"] * 2)), int(5 * height / 16))

        xpos = random.randint(xs, xtot)
        ypos = random.randint(ys, ytot)

        setheight = random.randint(0, 10) * 10
        r = 5000
        m = 0
        while (m < len(voronoi_points)) and (r > 0):
            dst = pow(pow((voronoi_points[m][0] - xpos), 2) + pow((voronoi_points[m][1] - ypos), 2), 0.5)
            if(dst < mindist):
                m = -1
                xpos = random.randint(xs, xtot)
                ypos = random.randint(ys, ytot)
            r = r - 1
            m = m + 1
        if (r > 0):
            voronoi_points.append([xpos, ypos, setheight])
            n = n + 1
        else:
            print("bailed at " + str(n) + " voronoi placements - ran out of space.")
            n = voronoi_max
        
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

    def make_ramp( mapinfo, pointinfo, start, end, rw ):
        genmap = mapinfo.copy()
        h = len(genmap)
        w = len(genmap[0])

        upper = max(min(pointinfo[start][1], pointinfo[end][1]) - rw // 2, 0)
        lower = min(max(pointinfo[start][1], pointinfo[end][1]) + rw // 2, h)
        left = max(min(pointinfo[start][0], pointinfo[end][0]) - rw // 2, 0)
        right = min(max(pointinfo[start][0], pointinfo[end][0]) + rw // 2, w)

        dst = pow(pow(pointinfo[start][1] - pointinfo[end][1], 2) + pow(pointinfo[start][0] - pointinfo[end][0], 2), 0.5)

        ux = (pointinfo[end][0] - pointinfo[start][0]) / dst
        uy = (pointinfo[end][1] - pointinfo[start][1]) / dst
        px = -1 * uy
        py = ux

        n = upper
        while(n < lower):
            m = left
            while(m < right):
                ax = m - pointinfo[start][0]
                ay = n - pointinfo[start][1]
                apx = ax * ux + ay * uy
                apy = ax * px + ay * py
                if((apx >= 0) and (apx <= dst) and abs(apy) < (rw / 2)):
                    p = (max(min(apx / dst, 0.75), 0.25) - 0.25) * 2
                    q = 1 - p
                    hght = q * pointinfo[start][2] + p * pointinfo[end][2]
                    genmap[n][m] = hght
                m = m + 1
            n = n + 1

        return genmap
        

    #ramps
    rampwidth = 40
    dstmin = 120 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
    startfrom = 0
    if(map_properties["numplayers"] > 4) and (voronoi_points[4][2] == voronoi_points[0][2]):
        startfrom = 4
    slopetolerance = 0.25
    slopelastresort = 0.5
    n = startfrom
    while (n < len(voronoi_points) - 1):
        m = startfrom
        ldst = 999999
        key = n
        rcnt = 0
        while(m < len(voronoi_points)):
            dst = 0
            if(voronoi_type == 0):
                #euclid
                dst = pow(pow(voronoi_points[m][0] - voronoi_points[n][0], 2) + pow(voronoi_points[m][1] - voronoi_points[n][1], 2), 0.5)
            if(voronoi_type == 1):
                #manhattan
                dst = abs(voronoi_points[m][0] - voronoi_points[n][0]) + abs(voronoi_points[m][1] - voronoi_points[n][1])
            if(dst < dstmin):
                if(n != m):
                    if(voronoi_points[m][2] != voronoi_points[n][2]):
                        if((abs(voronoi_points[n][2] - voronoi_points[m][2])) / dst < slopetolerance):
                            if(fliptype == 0):
                                if(voronoi_points[m][0] > voronoi_points[n][0]):
                                    genmap = make_ramp(genmap, voronoi_points, n, m, rampwidth)
                                    print("ramp formed between points " + str(n) + " and " + str(m))
                                    rcnt = rcnt + 1
                            if(fliptype == 1):
                                if(voronoi_points[m][1] > voronoi_points[n][1]):
                                    genmap = make_ramp(genmap, voronoi_points, n, m, rampwidth)
                                    print("ramp formed between points " + str(n) + " and " + str(m))
                                    rcnt = rcnt + 1
                            if(fliptype == 2):
                                vpd = pow(pow(voronoi_points[m][0] - voronoi_points[n][0], 2) + pow(voronoi_points[m][1] - voronoi_points[m][1], 2), 0.5)
                                vecx = (voronoi_points[m][0] - voronoi_points[n][0]) / vpd
                                vecy = (voronoi_points[m][1] - voronoi_points[m][1]) / vpd

                                tox = width // 2 - voronoi_points[n][0]
                                toy = width // 2 - voronoi_points[n][1]

                                dot = tox * vecx + toy * vecy
                                if(dot > 0):
                                    genmap = make_ramp(genmap, voronoi_points, n, m, rampwidth)
                                    print("ramp formed between points " + str(n) + " and " + str(m))
                                    rcnt = rcnt + 1
            if(dst < ldst):
                if(n != m):
                    if(voronoi_points[m][2] != voronoi_points[n][2]):
                        if((abs(voronoi_points[n][2] - voronoi_points[m][2])) / dst < slopelastresort):
                            if(fliptype == 0):
                                if(voronoi_points[m][0] > voronoi_points[n][0]):
                                    ldst = dst
                                    key = m
                            if(fliptype == 1):
                                if(voronoi_points[m][1] > voronoi_points[n][1]):
                                    ldst = dst
                                    key = m
                            if(fliptype == 2):
                                vpd = pow(pow(voronoi_points[m][0] - voronoi_points[n][0], 2) + pow(voronoi_points[m][1] - voronoi_points[m][1], 2), 0.5)
                                vecx = (voronoi_points[m][0] - voronoi_points[n][0]) / vpd
                                vecy = (voronoi_points[m][1] - voronoi_points[m][1]) / vpd

                                tox = width // 2 - voronoi_points[n][0]
                                toy = width // 2 - voronoi_points[n][1]

                                dot = tox * vecx + toy * vecy
                                if(dot > 0):
                                    ldst = dst
                                    key = m
            m = m + 1
        if(rcnt == 0) and (key != n):
            genmap = make_ramp(genmap, voronoi_points, n, key, rampwidth)
            print("last ditch ramp formed between points " + str(n) + " and " + str(key))
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
    #not really necessary, so we're just setting it to zero right now
    scaleblur = 0
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
    blurrad = 3 #blurs all pix around 10 units of the pixel
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
    genmap = generate_map_using_voronoi(map_properties)
    #print(str(genmap))
    print("finished")
