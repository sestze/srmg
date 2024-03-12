#path_generation.py
#author: Sestze
#
#Creates a set of paths and fills in the gaps between with unbuildable highground

#How does this work, step by step?
#   - Paths are formed by cubic splines from positions on the map to center points
#   - Anything not within a set radius of the spline points are considered oob
#   - We place contour hills in these places to act as obstacles

#Issues:


import random
import struct
import zlib
import math
import os

import copy

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
        endspline = int(endspline * width)
    if(fliptype == 1):
        startspline = int(startspline * height)
        endspline = int(endspline * height)
    if(fliptype == 2) or (fliptype == 3) or (fliptype == 4) or (fliptype == 5):
        startspline = int(startspline * (height + width) / 2)
        endspline = int(endspline * (height + width) / 2)

    numpaths = random.randint(2, 4)
    if(fliptype == 4) or (fliptype == 5):
        numpaths = numpaths // 2
    thresh = 6
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
        path_points.append([xvar, yvar, 24])
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
            #starting position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) - width // 2 + random.randint(-1 * wiggle, wiggle)
            yset = 0
            if(xset < 0):
                yset = xset * -1
                xset = 0
            spline_startpoints.append([xset, yset])
            #ending position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            yset = height - xset
            spline_endpoints.append([xset, yset])
            n = n + 1
    if(fliptype == 3):
        n = 0
        while(n < numpaths):
            #starting position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) - width // 2 + random.randint(-1 * wiggle, wiggle)
            yset = height
            if(xset < 0):
                yset = height - xset
                xset = 0
            spline_startpoints.append([xset, yset])
            #ending position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            yset = xset
            spline_endpoints.append([xset, yset])
            n = n + 1
    if(fliptype == 4):
        n = 0
        while(n < numpaths):
            #starting position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) - width // 2 + random.randint(-1 * wiggle, wiggle)
            yset = 0
            if(xset < 0):
                yset = xset * -1
                xset = 0
            spline_startpoints.append([xset, yset])
            #ending position
            wiggle = int((width / (2 * (numpaths + 1))) * 0.8)
            xset = int(width * (n + 1) / (numpaths + 1)) + random.randint(-1 * wiggle, wiggle)
            yset = width // 2
            if(xset > width // 2):
                yset = width // 2 - abs(width // 2 - xset)
                xset = width // 2
            spline_endpoints.append([xset, yset])
            n = n + 1
    if(fliptype == 5):
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
            xset = -1 * abs(yset - height // 2) + width // 2
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
    if(fliptype == 3):
        n = 0
        while(n < numpaths):
            m = 0
            while(m <= subsections):
                varx = cubic(m, 0, spline_startpoints[n][0], 50, spline_endpoints[n][0])
                vary = cubic(m, 0, spline_startpoints[n][1], 50, spline_endpoints[n][1])
                path_points.append([varx, vary])
                m = m + 1
            n = n + 1
    if(fliptype == 4) or (fliptype == 5):
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
    heightdiff = 0
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
                threshvar = n * pow(2, 0.5) / 2 + m * pow(2, 0.5) / 2
                if(n < startspline):
                    htemp = startheight
                elif(n > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(n, startspline, startheight, endspline, endheight)
            if(fliptype == 3):
                threshvar = (height - n) * pow(2, 0.5) / 2 + m * pow(2, 0.5) / 2
                if(n < startspline):
                    htemp = startheight
                elif(n > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(n, startspline, startheight, endspline, endheight)
            if(fliptype == 4) or (fliptype == 5):
                tdst = pow(pow(m, 2) + pow(n, 2), 0.5)
                threshvar = tdst
                if(tdst < startspline):
                    htemp = startheight
                elif(tdst > endspline):
                    htemp = endheight
                else:
                    htemp = cubic(tdst, startspline, startheight, endspline, endheight)
            #scan paths
            #kept for debugging
##            r = 0
##            isinpath = False
##            if(fliptype == 0) and (m > width // 2):
##                r = len(path_points)
##                isinpath = True
##            if(fliptype == 1) and (n > height // 2):
##                r = len(path_points)
##                isinpath = True
##            if(fliptype == 4):
##                if(n > height // 2) or (m > width // 2):
##                    r = len(path_points)
##                    isinpath = True
##            mindist = 999999
##            while((r < len(path_points)) and (isinpath == False)):
##                tdst = pow(pow(m - path_points[r][0], 2) + pow(n - path_points[r][1], 2), 0.5)
##                if(tdst < (thresh + threshvariance)):
##                    isinpath = True
##                if(tdst < mindist):
##                    mindist = tdst
##                r = r + 1
##            #if successfully within radius, set to max(htemp + 20 + (mindist - thresh)/20, 90) + random.randint(0, 10)
##            if(isinpath == False):
##                htemp = htemp + heightdiff
            row.append(htemp)
            m = m + 1
        genmap.append(row)
        n = n + 1

    def hill_func( var, xo, yo, xt, yt, hilltype, debug=0):
        if(var < xo):
            var = xo
        if (var > xt):
            var = xt

        #hill_funcs should go from radius 0 (center) to maxradius (furthest slope)
        #hill_funcs output go from maxheight to 0
        outval = 0
        #0 - decelerate (humps)
        if(hilltype == 0):
            outval = (yt - yo) * (1 - pow(20, ((var - xt) / (xt - xo)))) + yo
        #1 - accelerate (mesa)
        if(hilltype == 1):
            halfway = (xo + xt) / 2
            outval = 0
            if(var < halfway):
                outval = yt
            else:
                outval = (yt - yo) * (1 - pow(1 - pow((var - xt) / (xt - halfway),2),0.5)) + yo
        #2 - constant
        if(hilltype == 2):
            outval = yt - (var - xo) / (xt - xo) * (yt - yo)

        if(debug == 1):
            print("For hilltype " + str(hilltype))
            print(str(var) + ", (" + str(xo) + ", " + str(yo) + "), (" + str(xt) + ", " + str(yt) + ")")
            print("\tyields: " + str(outval))
        return outval

    def make_contour_hill( xplace, yplace, radius, genmap, wobble, hilltype ):
        primes = [1, 2, 3, 5, 7]
        hill_wobstr = wobble
        hill_start = 0
        
        hill_maxh = random.randint(2, 5) * 10

        print("hill: " + str(xplace) + ", " + str(yplace) + ", " + str(radius))
        print("hillstr: " + str(hill_wobstr))
        print("hillmax, hilltype: " + str(hill_maxh) + ", " + str(hilltype))

        genmap_output = copy.deepcopy(genmap)

        sinstr = []
        n = 0
        while n < len(primes):
            sinstr.append(random.uniform(0, 1) / primes[n])
            n = n + 1

        maxpos = 0
        minpos = 0
        n = -180
        while n < 180:
            func_out = 0
            m = 0
            while m < len(primes):
                func_out = func_out + math.sin(math.pi * 2 * primes[m] * n / 180) * sinstr[m]
                m = m + 1
            if func_out > maxpos:
                maxpos = func_out
            if func_out < minpos:
                minpos = func_out
            n = n + 1

        width = len(genmap[0])
        height = len(genmap)
        home = radius - hill_wobstr
        stored = 0
        while ((home - (minpos / maxpos) * hill_wobstr) > 0):
            n = int(max(yplace - radius, 0))
            while n < int(min(yplace + radius, height)):
                m = int(max(xplace - radius, 0))
                while m < int(min(xplace + radius, width)):
                    xdisp = m - xplace
                    ydisp = n - yplace

                    dst = pow(pow(xdisp, 2) + pow(ydisp, 2), 0.5)
                    ang = 0
                    if(xdisp == 0):
                        if(ydisp > 0):
                            ang = math.pi / 2
                        else:
                            ang = math.pi / -2
                    else:
                        ang = math.atan2(ydisp,xdisp)

                    func_out = 0
                    r = 0
                    while r < len(primes):
                        func_out = func_out + math.sin(primes[r] * ang) * sinstr[r]
                        r = r + 1
                    func_out = func_out / maxpos

                    curverad = home + hill_wobstr * func_out
                    if(curverad > dst):
                        genmap_output[n][m] = genmap[yplace][xplace] + hill_func(home, 0, hill_start, radius, hill_maxh, hilltype)
                    m = m + 1
                n = n + 1
            home = home - hill_wobstr / 2
            
        return genmap_output

    wobble = random.randint(3,7) * 3
    hilltype = random.randint(0, 2)
    #placing hill
    print("placing hills")
    numhills = random.uniform(1.0, 1.6) * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 2
    if(fliptype == 4) or (fliptype == 5):
        numhills = numhills / 2
    n = 0
    while n < numhills:
        xm = 0
        ym = 0
        xtot = width
        ytot = height

        if(fliptype == 0):
            xtot = width // 2
        if(fliptype == 1):
            ytot = height // 2
        if(fliptype == 4):
            xtot = width // 2
            ytot = width // 2

        xpos = random.randint(xm, xtot)
        if(fliptype == 2):
            ytot = height - xpos
        ypos = random.randint(ym, ytot)
        if(fliptype == 3):
            xtot = ypos
            xpos = random.randint(xm, xtot)
        if(fliptype == 5):
            xtot = max(-1 * abs(ypos - height // 2) + width // 2, xm) + 1
            xpos = random.randint(xm, xtot)
        maxr = 120
        r = 500
        m = 0
        while((m < len(path_points)) and r > 0):
            dstthresh = thresh
            if(len(path_points[m]) == 3):
                dstthresh = path_points[m][2]
            dstto = pow(pow(xpos - path_points[m][0], 2) + pow(ypos - path_points[m][1], 2), 0.5)
            if((dstto - dstthresh) < maxr):
                maxr = dstto - dstthresh
            if(dstto < dstthresh) or (maxr < 40):
                xpos = random.randint(xm, xtot)
                if(fliptype == 2):
                    ytot = height - xpos
                ypos = random.randint(ym, ytot)
                if(fliptype == 3):
                    xtot = ypos
                    xpos = random.randint(xm, xtot)                
                if(fliptype == 5):
                    xtot = min(-1 * abs(ypos - height // 2) + width // 2, xm) + 1
                    xpos = random.randint(xm, xtot)
                maxr = 120
                r = r - 1
                m = -1
            m = m + 1
        if(r == 0):
            print("failed to find a hill position in 500 checks ending hills at " + str(n) + " hills")
            n = numhills
        else:
            print("maxr eventually was: " + str(maxr))
            useradius = random.uniform(40, maxr)
            print("using radius: " + str(useradius))
            genmap = make_contour_hill(xpos, ypos, useradius, genmap, wobble, hilltype)
            path_points.append([xpos, ypos, useradius])
        n = n + 1
    print("path generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("Too many inputs, really. Need to run srmg_1.py")
    #genmap = generate_map_using_paths(map_properties)
    #print(str(genmap))
    print("finished")
