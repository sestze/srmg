#voronoi_generation.py
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

#Issues:
#   - Need to add fliptype 2, 3 and move 2 to 4 and 5.
#   - Adding wobble to edges could allow more "natural" terrain
#       - As a bool (wobble = true) could allow for a swap between the harsh lines of the generator and more natural generation output

import random
import struct
import zlib
import math
import os

from PIL import Image

def generate_map_using_voronoi (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = random.randint(4, 6) * 10
    frontheight = 100 - startheight

    print("Map Statistics: ")
    print("\tSeed: " + str(map_properties["seed"]))
    print("\twidth: " + str(map_properties["mapsizex"]))
    print("\theight: " + str(map_properties["mapsizey"]))
    print("\tstartheight: " + str(startheight))
    
    #build the basic map:
    #cubic spline for edges
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
    #start points
    voronoi_max = (random.randint(4, 8) * (map_properties["mapsizex"] + map_properties["mapsizey"])) // 24
    voronoi_points = []
    n = 0
    while n < len(start_positions):
        voronoi_points.append([int(start_positions[n][0] * width), int(start_positions[n][1] * height), random.choice([startheight, frontheight]), 0])
        n = n + 1

    #external points
    #as a circle, not a square
    external = 100
    extdiff = 20
    extsprd = 16
    if(random.uniform(0, 1) < 0.5):
        external = 0
    rad = max(width, height) / pow(2, 0.5)
    cx = width / 2
    cy = height / 2
    n = 0
    while n < 8:
        px = cx + rad * math.cos(n * 2 * math.pi / 8)
        py = cy + rad * math.sin(n * 2 * math.pi / 8)
        voronoi_points.append([int(px), int(py), external, 1])
        n = n + 1
        
    #if corners or crosses, nix the middle.
    if(fliptype == 4) or (fliptype == 5):
        voronoi_points.append([int(cx), int(cy), external, 1])
    if(fliptype == 2) or (fliptype == 3):
        if(random.uniform(0, 1) < 0.5):
            voronoi_points.append([int(cx), int(cy), external, 1])
        
    #other generated points
    mindist = 100 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
    #mindist = 100
    n = 0
    while (n < voronoi_max):
        xtot = width - mindist
        ytot = height - mindist
        xs = mindist
        ys = mindist

        if(fliptype == 0) or (fliptype == 4):
            xtot = (15 * width) // 32
            xs = (5 * width) // 32
        if(fliptype == 1) or (fliptype == 4):
            ytot = (15 * height) // 32
            ys = (5 * height) // 32
            
        xpos = 0
        ypos = 0
        if(fliptype == 0) or (fliptype == 1) or (fliptype == 4):
            xpos = random.randint(int(xs), int(xtot))
            ypos = random.randint(int(ys), int(ytot))
        elif(fliptype == 2):
            xpos = random.randint(xs, xtot)
            ymax = int(height - height / width * xpos - mindist)
            ypos = random.randint(int(ys), int(ymax))
        elif(fliptype == 3):
            xpos = random.randint(xs, xtot)
            ymax = int(height/width * xpos - mindist)
            ypos = random.randint(int(ymax), int(ytot))
        elif(fliptype == 5):
            ypos = random.randint(ys, ytot)
            xmax = int(-1 * (width/height) * (ypos - height / 2) + width / 2)
            xpos = random.randint(int(xs), xmax)
            

        setheight = random.randint(1, 4) * 20
        r = 5000
        m = 0
        while (m < len(voronoi_points)) and (r > 0):
            dst = pow(pow((voronoi_points[m][0] - xpos), 2) + pow((voronoi_points[m][1] - ypos), 2), 0.5)
            if(dst < mindist):
                m = -1
                xpos = 0
                ypos = 0
                if(fliptype == 0) or (fliptype == 1) or (fliptype == 4):
                    xpos = random.randint(int(xs), int(xtot))
                    ypos = random.randint(int(ys), int(ytot))
                elif(fliptype == 2):
                    xpos = random.randint(xs, xtot)
                    ymax = int(height - height / width * xpos - mindist)
                    ypos = random.randint(int(ys), int(ymax))
                elif(fliptype == 3):
                    xpos = random.randint(xs, xtot)
                    ymax = int(height/width * xpos - mindist)
                    ypos = random.randint(int(ymax), int(ytot))
                elif(fliptype == 5):
                    ypos = random.randint(ys, ytot)
                    xmax = int(-1 * (width/height) * abs(ypos - height / 2) + width / 2)
                    xpos = random.randint(int(xs), xmax)
            r = r - 1
            m = m + 1
        if (r > 0):
            voronoi_points.append([xpos, ypos, setheight, 0])
            if(fliptype == 0):
                voronoi_points.append([width - 1 - xpos, ypos, setheight, 1])
            if(fliptype == 1):
                voronoi_points.append([xpos, height - 1 - ypos, setheight, 1])
            if(fliptype == 2):
                voronoi_points.append([height - 1 - ypos, width - 1 - xpos, setheight, 1])
            if(fliptype == 3):
                voronoi_points.append([ypos, xpos, setheight, 1])
            if(fliptype == 4):
                voronoi_points.append([xpos, height - 1 - ypos, setheight, 1])
                voronoi_points.append([width - 1 - xpos, ypos, setheight, 1])
                voronoi_points.append([width - 1 - xpos, height - 1 - ypos, setheight, 1])
            if(fliptype == 5):
                voronoi_points.append([ypos, xpos, setheight, 1])
                voronoi_points.append([width - 1 - xpos, height - 1 - ypos, setheight, 1])
                voronoi_points.append([width - 1 - ypos, height - 1 - xpos, setheight, 1])
            n = n + 1
        else:
            print("bailed at " + str(n) + " voronoi placements - ran out of space.")
            n = voronoi_max
        
    #set heights based on voronoi
    voronoi_type = random.randint(0, 3)
    if(voronoi_type == 0):
        print("\tvoronoi_type: Euclid")
    if(voronoi_type == 1):
        print("\tvoronoi_type: Manhattan")
    if(voronoi_type == 2):
        print("\tvoronoi_type: Fuzzy Euclid")
    if(voronoi_type == 3):
        print("\tvoronoi_type: Fuzzy Manhattan")

    voronoi_fuzzy_min = 50
    voronoi_fuzzy_max = 400
    fuzzy_pow = 6
    
    n = 0
    while (n < height):
        row = []
        m = 0
        while (m < width):
            dstmin = 999999
            vn_height = startheight
            alldst = [*range(len(voronoi_points))]
            r = 0
            while (r < len(voronoi_points)):
                dst = 0
                if(voronoi_type == 0) or (voronoi_type == 2):
                    #euclid or fuzzy euclid
                    dst = pow(pow(m - voronoi_points[r][0], 2) + pow(n - voronoi_points[r][1], 2), 0.5)
                if(voronoi_type == 1) or (voronoi_type == 3):
                    #manhattan or fuzzy manhattan
                    dst = abs(m - voronoi_points[r][0]) + abs(n - voronoi_points[r][1])
                alldst[r] = dst
                if(dst < dstmin):
                    dstmin = dst
                    vn_height = voronoi_points[r][2]
                    #used for making terrain unusable - currently looks a bit too wonky.
##                    if(voronoi_points[r][3] == 1):
##                        cm = (m // extsprd) % 2
##                        cn = (n // extsprd) % 2
##                        if(cm == cn):
##                            vn_height = voronoi_points[r][2]
##                        else:
##                            if(voronoi_points[r][2] > 50):
##                                vn_height = voronoi_points[r][2] - extdiff
##                            else:
##                                vn_height = voronoi_points[r][2] + extdiff
                r = r + 1
            if(dstmin > voronoi_fuzzy_min) and ((voronoi_type == 2) or (voronoi_type == 3)):
                r = 0
                totdst = 0
                avg = 0
                while r < len(voronoi_points):
                    if(alldst[r] < dstmin + voronoi_fuzzy_max):
                       avg = avg + voronoi_points[r][2] * (1 / pow(alldst[r] - voronoi_fuzzy_min, fuzzy_pow))
                       totdst = totdst + (1 / pow((alldst[r] - voronoi_fuzzy_min), fuzzy_pow))
                    r = r + 1
                avg = avg / totdst
                vn_height = avg
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

        n = 0
        while n < len(pointinfo):
            if(n != start) and (n != end):
                if(pointinfo[n][1] < lower and pointinfo[n][1] > upper):
                    if(pointinfo[n][0] > left and pointinfo[n][0] < right):
                        print("ramp intersects with another voronoi point - halting")
                        return genmap
            n = n + 1

        n = upper
        while(n < lower):
            m = left
            while(m < right):
                ax = m - pointinfo[start][0]
                ay = n - pointinfo[start][1]
                apx = ax * ux + ay * uy
                apy = ax * px + ay * py
                
                p = (max(min(apx / dst, 0.75), 0.25) - 0.25) * 2
                q = 1 - p
                rwc = p * rw * 0.75 + q * rw * 1.25
                if(pointinfo[start][2] > pointinfo[end][2]):
                    rwc = q * rw * 0.75 + p * rw * 1.25
                if((apx >= 0) and (apx <= dst) and abs(apy) < (rwc / 2)):
                    #hght = q * pointinfo[start][2] + p * pointinfo[end][2]
                    hght = cubic(p, 0, pointinfo[start][2], 1, pointinfo[end][2])
                    genmap[n][m] = hght
                m = m + 1
            n = n + 1

        return genmap
        

    #ramps
    rampwidth = 40
    dstmin = 120 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
    startfrom = 0
    slopetolerance = 0.25
    slopelastresort = 0.5
    n = startfrom
    while (n < len(voronoi_points) - 1):
        m = startfrom
        ldst = 999999
        key = n
        rcnt = 0
        while(m < len(voronoi_points)) and (voronoi_points[n][3] != 1):
            dst = 0
            if(voronoi_type == 0) or (voronoi_type == 2):
                #euclid
                dst = pow(pow(voronoi_points[m][0] - voronoi_points[n][0], 2) + pow(voronoi_points[m][1] - voronoi_points[n][1], 2), 0.5)
            if(voronoi_type == 1) or (voronoi_type == 3):
                #manhattan
                dst = abs(voronoi_points[m][0] - voronoi_points[n][0]) + abs(voronoi_points[m][1] - voronoi_points[n][1])
            if(dst < dstmin) and (voronoi_points[m][3] != 1):
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
                            if(fliptype == 2) or (fliptype == 3) or (fliptype == 4) or (fliptype == 5):
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
            if(dst < ldst) and (voronoi_points[m][3] != 1):
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
                            if(fliptype == 2) or (fliptype == 3) or (fliptype == 4) or (fliptype == 5):
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
        if(rcnt == 0) and (key != n) and (voronoi_points[n][3] != 1) and (voronoi_points[key][3] != 1):
            genmap = make_ramp(genmap, voronoi_points, n, key, rampwidth)
            print("last ditch ramp formed between points " + str(n) + " and " + str(key))
        n = n + 1

    print("voronoi generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    #print("Running to debug")
    print("We need too many external arguments to run from this script now. Run srmg_1.py")
    map_properties = {
        "mapsizex": 12,
        "mapsizey": 12,
        "seed": 333666999,
        "numplayers": 8,
        "generation_type": "voronoi"     #normal, prefab, voronoi
        }
    #genmap = generate_map_using_voronoi(map_properties)
    #print(str(genmap))
    print("finished")
