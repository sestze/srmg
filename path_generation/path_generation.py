#path_generation.py
#author: Sestze
#
#Creates a set of paths and fills in the gaps between with unbuildable highground

#How does this work, step by step?
#   - Paths are formed by cubic splines from positions on the map to center points
#   - Anything not within a set radius of the spline points are considered oob
#   - Height of in-path areas are defined by a spline
#   - Height of out-of-path areas are defined by height and summated periodic function and distance from threshold

#Issues:
#   - we're always in a hole
#   - quads are close to 100% fucked 100% of the time
#   - We need to add fliptype 2 and 3, and reset fliptype 2 to be for 4 and 5.

import random
import struct
import zlib
import math
import os

from PIL import Image

def generate_map_using_paths (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = 30 + random.randint(1, 2) * 10 * pow(-1, random.randint(0, 1))
    endheight = 60 - startheight
    startspline = random.uniform(3/32, 7/32)
    endspline = random.uniform(9/32, 15/32)

    if(fliptype == 0):
        startspline = int(startspline * width)
    if(fliptype == 1):
        endspline = int(endspline * width)

    numpaths = random.randint(4, 7)
    thresh = 65
    thresh = thresh - (numpaths - 3) * 10
    thresh = (thresh * (int(map_properties["mapsizex"]) + int(map_properties["mapsizey"]))) // 24

    print("Map Statistics: ")
    print("\tSeed: " + str(map_properties["seed"]))
    print("\twidth: " + str(map_properties["mapsizex"]))
    print("\theight: " + str(map_properties["mapsizey"]))
    print("\tstartheight: " + str(startheight))
    print("\tendheight: " + str(endheight))
    print("\tthresh: " + str(thresh))
    print("\tnumpaths: " + str(numpaths))

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
    path_points = []
    
    n = 0
    while(n < len(start_positions)):
        xvar = start_positions[n][0] * width
        yvar = start_positions[n][1] * height
        path_points.append([xvar, yvar])
        n = n + 1
    #defining the splines
    spline_startpoints = []
    spline_endpoints = []
    if(fliptype == 0):
        n = 0
        while(n < numpaths):
            wiggle = int((height / (2 * (numpaths + 1))) * 0.8)
            #starting position
            yset = int(height * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            xset = 0
            spline_startpoints.append([xset, yset])
            #end position
            wiggle = int((height / (2 * (numpaths + 1))) * 0.8)
            yset = int(height * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            xset = width // 2
            spline_endpoints.append([xset, yset])
            n = n + 1
    if(fliptype == 1):
        n = 0
        while(n < numpaths):
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            #starting position
            xset = int(width * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            yset = 0
            spline_startpoints.append([xset, yset])
            #ending position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            yset = height // 2
            spline_endpoints.append([xset, yset])
            n = n + 1
    if(fliptype == 2):
        n = 0
        while(n < numpaths):
            wiggle = math.pi / (4 * numpaths + 1) * random.uniform(-1, 1)
            #starting position
            radius = 3 * max(int(min(width, height) / (min(map_properties["mapsizex"], map_properties["mapsizey"]) * 2)), int(min(width, height) / 16))
            xset = int(radius * math.cos(wiggle + (math.pi / 2) * (n + 1) / (numpaths + 1)))
            yset = int(radius * math.sin(wiggle + (math.pi / 2) * (n + 1) / (numpaths + 1)))
            spline_startpoints.append([xset, yset])
            
            wiggle = math.pi / (4 * numpaths + 1) * random.uniform(-1, 1)
            #ending position
            radius = pow(pow(width // 2, 2) + pow(height // 2, 2), 0.5)
            xset = int(radius * math.cos(wiggle + (math.pi / 2) * (n + 1) / (numpaths + 1)))
            yset = int(radius * math.sin(wiggle + (math.pi / 2) * (n + 1) / (numpaths + 1)))
            spline_endpoints.append([xset, yset])
            n = n + 1
    #shuffle endpoints
    random.shuffle(spline_endpoints)
    #generating points via splines
    subsections = 50
    if(fliptype == 0):
        n = 0
        while(n < numpaths):
            m = 0
            while(m <= subsections):
                displacement = (width // 2) + thresh - spline_startpoints[n][0]
                dx = (displacement) // subsections
                varx = dx * m + spline_startpoints[n][0]

                vary = cubic(varx, spline_startpoints[n][0], spline_startpoints[n][1], spline_endpoints[n][0], spline_endpoints[n][1])
                path_points.append([varx, vary])
                m = m + 1
            path_points.append([spline_endpoints[n][0] + thresh / 2, spline_endpoints[n][1]])
            path_points.append([spline_endpoints[n][0] + thresh, spline_endpoints[n][1]])
            n = n + 1
    if(fliptype == 1):
        n = 0
        while(n < numpaths):
            m = 0
            while(m <= subsections):
                displacement = (height // 2) + thresh - spline_startpoints[n][1]
                dy = (displacement) // subsections
                vary = dy * m + spline_startpoints[n][1]

                varx = cubic(vary, spline_startpoints[n][1], spline_startpoints[n][0], spline_endpoints[n][1], spline_endpoints[n][0])
                path_points.append([varx, vary])
                m = m + 1
            path_points.append([spline_endpoints[n][0], spline_endpoints[n][1] + thresh / 2])
            path_points.append([spline_endpoints[n][0], spline_endpoints[n][1] + thresh])
            n = n + 1
    if(fliptype == 2):
        n = 0
        while(n < numpaths):
            m = 0
            while(m <= subsections):
                varx = cubic(m, 0, spline_startpoints[n][0], 50, spline_endpoints[n][0])
                vary = cubic(m, 0, spline_startpoints[n][1], 50, spline_endpoints[n][1])
                path_points.append([varx, vary])
                m = m + 1
            n = n + 1
    #flood the map portions
    cossum = random.randint(3, 10)
    cosvars = []
    sinvars = []
    cosstrtot = 0
    sinstrtot = 0
    n = 0
    while(n < cossum):
        disp = random.randint(-9, 9) * 10
        pchange = random.randint(-10, 10)
        strength = random.randint(1, 5) * 5
        cosvars.append([disp, pchange, strength])
        
        disps = random.randint(-9, 9) * 10
        pchanges = random.randint(-10, 10)
        strengths = random.randint(1, 5) * 5
        sinvars.append([disps, pchanges, strengths])
        cosstrtot = cosstrtot + strength
        sinstrtot = sinstrtot + strength
        n = n + 1
    cosstrtot = (cosstrtot + sinstrtot) / 2

    tv = thresh * random.randint(1, 3) / 10
    bv = random.randint(1, 5) * 3

    heightdiff = 10 + random.randint(0, 6) * 5
    heightbythresh = random.randint(0, 10) * 5
    print("\ttv: " + str(tv))
    print("\tbv: " + str(bv))
    print("\theightdiff: " + str(heightdiff))
    print("\theightbythresh: " + str(heightbythresh))
    n = 0
    while(n < height):
        row = []
        m = 0
        while(m < width):
            #spline for overall map heights
            threshvariance = 0
            bumpvariance = 0
            threshvar = 0
            htemp = 50
            if(fliptype == 0):
                threshvar = m
                if(m < startspline):
                    htemp = startheight
                elif(m > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(m, startspline, startheight, endspline, endheight)
            if(fliptype == 1):
                threshvar = n
                if(n < startspline):
                    htemp = startheight
                elif(n > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(n, startspline, startheight, endspline, endheight)
            if(fliptype == 2):
                tdst = pow(pow(m, 2) + pow(n, 2), 0.5)
                threshvar = tdst
                if(tdst < startspline):
                    htemp = startheight
                elif(tdst > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(tdst, startspline, startheight, endspline, endheight)
            #adding thresh variance for more interesting path generation
            r = 0
            while(r < cossum):
                tvdiv = 270 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
                bvdiv = 540 * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
                threshvariance = threshvariance + math.cos(math.pi * (cosvars[r][1] * m + cosvars[r][0]) / tvdiv) * cosvars[r][2]
                threshvariance = threshvariance + math.sin(math.pi * (sinvars[r][1] * n + sinvars[r][0]) / tvdiv) * sinvars[r][2]
                bumpvariance = bumpvariance + math.cos(math.pi * (sinvars[r][1] * n + sinvars[r][0]) / bvdiv) * sinvars[r][2]
                bumpvariance = bumpvariance + math.sin(math.pi * (cosvars[r][1] * m + cosvars[r][0]) / bvdiv) * cosvars[r][2]
                r = r + 1
            threshvariance = threshvariance / cosstrtot * tv
            bumpvariance = bumpvariance / cosstrtot * bv
            #scan paths
            r = 0
            isinpath = False
            if(fliptype == 0) and (m > width // 2):
                r = len(path_points)
                isinpath = True
            if(fliptype == 1) and (n > height // 2):
                r = len(path_points)
                isinpath = True
            if(fliptype == 2):
                if(n > height // 2) or (m > width // 2):
                    r = len(path_points)
                    isinpath = True
            mindist = 999999
            while((r < len(path_points)) and (isinpath == False)):
                tdst = pow(pow(m - path_points[r][0], 2) + pow(n - path_points[r][1], 2), 0.5)
                if(tdst < (thresh + threshvariance)):
                    isinpath = True
                if(tdst < mindist):
                    mindist = tdst
                r = r + 1
            #if successfully within radius, set to max(htemp + 20 + (mindist - thresh)/20, 90) + random.randint(0, 10)
            if(isinpath == False):
                moddedthresh = thresh + threshvariance
                htemp = htemp + heightdiff + heightbythresh * (mindist - moddedthresh)/(moddedthresh) + bumpvariance
            row.append(htemp)
            m = m + 1
        genmap.append(row)
        n = n + 1
    print("path generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("Too many inputs, really. Need to run srmg_1.py")
    #genmap = generate_map_using_paths(map_properties)
    #print(str(genmap))
    print("finished")
