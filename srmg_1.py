#srmg_1.py
#author: Sestze
#
#Currently does the following:
#   - Generates a heightmap as a 16bit greyscale png
#   - Generates a metalmap as an 8bit rgb bmp
#   - Generates a texmap as an 8bit rgb bmp
#   - Generates the mapinfo.lua file
#   - Generates the mapconfig/map_startboxes.lua file
#       - Doesn't currently work (at least, not as far as I can tell)
#   - Runs map converter, doing a full conversion of the map
#   - Runs 7zip, putting all the requisite bits of the map into a mapfile.

#TODO:
#   - Heightmaps
#       - Offer a different generation method that uses a premade heightmap
#   - Metalmap
#       - Make the mex placement a big smarter - stop placing them on top of areas with significant slopes
#           - Still trying on this, it's failing though.
#           - We may have too many mexes on the map.
#   - Texturemap



import random
import struct
import zlib
import math
import png
import os
import subprocess
import py7zr

import prefab_generation.prefab_generation

import voronoi_generation.voronoi_generation

#from typing import BinaryIO, List, Tuple
from PIL import Image

def generate_heightmap(genmap, mult, minh):
    out = []
    # here's where we'd have to take the genmap and turn it into pixels.
    # (Number) * 2 + 25 is the pixel value for RGB.
    width = len(genmap[0])
    height = len(genmap)
    n = 0
    while n < height:
        m = 0
        row = []
        while m < width:
            cellval = (genmap[n][m] - minh) * mult
            row.append(int(max(min((cellval*2 + 25)*256, 256*200), 25*256)))
            m = m + 1
        out.append(row)
        n = n + 1
    return out

def generate_map_using_prefabs (map_properties):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = random.randint(0, 10) * 10
    endheight = random.randint(0, 10) * 10
    
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
    print("\tendheight: " + str(endheight))

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

    n = 0
    while n < height:
        m = 0
        row = []
        while m < width:
            inval = clamp(m, 1/8 * width, 3/8 * width)
            height = cubic(inval, 1/8 * width, startheight, 3/8 * width, endheight) #defaults to horizontal fliptype
            if(fliptype == 1):
                inval = clamp(n, 1/8 * height, 3/8 * height)
                height = cubic(inval, 1/8 * height, startheight, 3/8 * height, endheight)
            if(fliptype == 2):
                dst = pow(pow(n,2) + pow(m,2), 0.5)
                inval = clamp(dst, 1/8 * (width + height) / 2, 3/8 * (width + height) / 2)
                height = cubic(inval, 1/8 * (width + height) / 2, startheight, 3/8 * (width + height) / 2, endheight)
            row.append(height)
            m = m + 1
        genmap.append(row)
        n = n + 1

    #load prefabs
        
    #add in prefabs

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

    return genmap, fliptype

def generate_map (map_properties):
    #blots didn't work, trying something simpler than splines but more complicated than blots
    width = map_properties["mapsizex"] * 64 + 1
    height = map_properties["mapsizey"] * 64 + 1
    
    maxflats = 128    #For now, I think 8 is fine.
    blots = random.randint(14, 24) - 4
    blotleast = random.randint(1, 2) * 20
    blotmost = random.randint(3, 6) * 20
    blotbuild = random.randint(0, 2)    #0 - build up, 1 - scoop, 2 - break down.
    #hdiv = random.randint(1,2) * 5       #Height division, multiply by. Makes it in chunks of hdiv.
    bmul = 1
    if(blotbuild != 1):
        bmul = 2
    blurradius = random.randint(1, 3) * 16 * bmul
    #divby = int((random.randint(1, 4) * 128) / maxflats)       #divby adjusts coordinate neighbors
    
    #percellchange = random.randint(1, 4)    #per cell, how much can height change
    #steepmultiplier = 4  #how brutal is the logistics curve? Deprecated, using cubic splines

    fliptype = random.randint(0, 2) #0 is horizontal, 1 is vertical, 2 is quads
    if(width > height):
        fliptype = random.choice([0, 2])
    elif(height > width):
        fliptype = random.choice([1, 2])

    if(fliptype == 2):
        blots = blots - 4

    FlipName = ["Horizontal", "Vertical", "Quad"]
    BlotName = ["Build-Up", "Scoop", "Break-Down"]

    print("Map Statistics: ")
    print("\tSeed: " + str(map_properties["seed"]))
    print("\twidth: " + str(map_properties["mapsizex"]))
    print("\theight: " + str(map_properties["mapsizey"]))
    print("\tfliptype: " + FlipName[fliptype])
    print("\tblottype: " + BlotName[blotbuild])
    print("\tblots: " + str(blots))
    print("\tblotleast: " + str(blotleast))
    print("\tblotmost: " + str(blotmost))
    print("\tblurradius: " + str(blurradius))
    print("\tmaxflats = " + str(maxflats))
    #print("\thdiv = " + str(hdiv))
    #print("\tdivby = " + str(divby))
    #print("\tpercellchange = " + str(percellchange))
    #print("\tsteepmultiplier = " + str(steepmultiplier))

    genmap = []
    clampw = width - 64
    clamph = height - 64

    coords = []

    def hdivs(num):
        retval = random.randint(0, int(100 / num)) * num
        return retval

    def makeoval ( density, xm, ym, xc, yc, xs, ys ):
        oval = []
        xdiv = int(xm / density)
        ydiv = int(ym / density)
        n = 0
        while n < ym:
            m = 0
            while m < xm:
                ovalfunc = pow(m - xc, 2) / pow(xs, 2) + pow(n - yc, 2) / pow(ys, 2)
                if (ovalfunc <= 1):
                    oval.append([m, n])
                m = m + xdiv
            n = n + ydiv

        return oval

    #blotorder
    blotorder = [0, 50, 100]
    if(blotbuild == 1):
        blotorder = [50, 0, 100]
    elif(blotbuild == 2):
        blotorder = [100, 50, 0]

    #necessary to prevent errors from edge values.
    xdivval = int(width/maxflats)
    ydivval = int(height/maxflats)

    #it's harder to mirror if we're starting at 0,0 and using non-flush divs
    starth = int(height/2)
    while(starth > ydivval):
        starth = starth - ydivval
    startw = int(width/2)
    while(startw > xdivval):
        startw = startw - xdivval

    print("startw: " + str(startw) + " starth: " + str(starth))    
    n = starth
    while n < height:
        m = startw
        row = []
        while m < width:
            row.append([m, n, blotorder[0]])
            m = m + xdivval
        #row.append([width, n, blotorder[0]])
        coords.append(row)
        n = n + ydivval

    n = 1
    while n < 3:
        m = 0
        while m < blots:
            xc = startw + int(random.randint(0, int(width/2)) / xdivval) * xdivval
            yc = starth + int(random.randint(0, height) / ydivval) * ydivval
            incby = 1
            if(fliptype == 1):
                xc = startw + int(random.randint(0, width) / xdivval) * xdivval
                yc = starth + int(random.randint(0, int(height / 2)) / ydivval) * ydivval
            if(fliptype == 2):
                yc = starth + int(random.randint(0, int(height / 2)) / ydivval) * ydivval
                incby = 2

            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            #oval = makeoval ( maxflats, width, height, xc, yc, xs, ys)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xc, 2) / pow(xs, 2) + pow(coords[p][q][1] - yc, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[n]]
                    q = q + 1
                p = p + 1
            m = m + incby
        n = n + 1

    #jimmy startpositions
    xcoord = width
    ycoord = height
        
    backline = min(4, map_properties["numplayers"])
    frontline = map_properties["numplayers"] - backline

    if(fliptype == 0):
        xset = min(int(xcoord / (map_properties["mapsizex"] * 2)), int(xcoord / 16))
        n = 0
        while n < backline:
            yset = int(ycoord * (n + 1) / (backline + 1))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1
        xset = min(int(4 * xcoord / (map_properties["mapsizex"] * 2)), int(4 * xcoord / 16))
        n = 0
        while n < frontline:
            yset = int(ycoord * (n + 1) / (frontline + 1))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1
    elif(fliptype == 1):
        yset = min(int(ycoord / (map_properties["mapsizey"] * 2)), int(ycoord / 16))
        n = 0
        while n < backline:
            xset = int(xcoord * (n + 1) / (backline + 1))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1
        yset = min(int(4 * ycoord / (map_properties["mapsizey"] * 2)), int(4 * ycoord / 16))
        n = 0
        while n < frontline:
            xset = int(xcoord * (n + 1) / (frontline + 1))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1
    elif(fliptype == 2):
        radius = 4 * min(int(min(xcoord, ycoord) / (min(map_properties["mapsizex"], map_properties["mapsizey"]) * 2)), int(min(xcoord, ycoord) / 16))
        n = 0
        while n < backline:
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1
        radius = int(1.5 * min(4 * int(min(xcoord, ycoord) / (2 * min(map_properties["mapsizex"], map_properties["mapsizey"]))), int(4 * min(xcoord, ycoord) / 16)))
        n = 0
        while n < frontline:
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            xs = random.randint(blotleast, blotmost)
            ys = random.randint(blotleast, blotmost)
            p = 0
            while p < len(coords):
                q = 0
                while q < len(coords[p]):
                    ovalfunc = pow(coords[p][q][0] - xset, 2) / pow(xs, 2) + pow(coords[p][q][1] - yset, 2) / pow(ys, 2)
                    if(ovalfunc <= 1):
                        xval = coords[p][q][0]
                        yval = coords[p][q][1]
                        coords[p][q] = [xval, yval, blotorder[0]]
                    q = q + 1
                p = p + 1
            n = n + 1

    combinecoord = []
    n = 0
    while n < len(coords):
        #row = []
        ndivs = 0
        m = 0
        oskip = False
        if((fliptype == 1) or (fliptype == 2)):
            if (n >= int((len(coords) - 1)/2)):
                q = n
                while q < len(coords):
                    p = 0
                    while (p < len(coords[0])):
                        xvar = coords[q][p][0]
                        yvar = coords[q][p][1]
                        zvar = coords[n][p][2]
                        #tagrow.append([xvar, yvar, zvar])
                        coords[q][p] = [xvar, yvar, zvar]
                        p = p + 1
                    #combinecoord.append(tagrow)
                    q = q + 1
                    n = n - 1
                oskip = True
        if(oskip == False):
            while m < len(coords[0]):
                skip = False
                if((fliptype == 0) or (fliptype == 2)):
                    if (m >= int((len(coords[0])-1) / 2)):
                        q = m
                        while m < len(coords[0]):
                            xvar = coords[n][m][0]
                            yvar = coords[n][m][1]
                            zvar = coords[n][q][2]
                            #row.append([xvar, yvar, zvar])
                            coords[n][m] = [xvar, yvar, zvar]
                            q = q - 1
                            m = m + 1
                        skip = True
                if(skip == False):
    ##                if((n == 0) and (m == 0)):
    ##                    ndivs = hdivs(hdiv)
    ##                    row.append([coordx[m], coordy[n], ndivs])
    ##                elif((n == 0) and (m > 0)):
    ##                    ndivs = min(max(row[m-1][2] + random.randint(-1 * percellchange, 1 * percellchange) * hdiv, 0), 100)
    ##                    row.append([coordx[m], coordy[n], ndivs])
    ##                elif((n > 0) and (m == 0)):
    ##                    ndivs = min(max(combinecoord[n-1][m][2] + random.randint(-1 * percellchange, 1 * percellchange) * hdiv, 0), 100)
    ##                    row.append([coordx[m], coordy[n], ndivs])
    ##                else:
    ##                    ndivs = min(max((row[m-1][2]+combinecoord[n-1][m][2]) / 2 + random.randint(-1 * percellchange, 1 * percellchange) * hdiv, 0), 100)
    ##                    row.append([coordx[m], coordy[n], int(ndivs)])
                    m = m + 1
                else:
                    m = len(coords[0])
            #combinecoord.append(row)
            n = n + 1
        else:
            n = len(coords)

    #this fixes the right side - not sure why
    n = int(len(coords)/2)-1
    m = int(len(coords[n])/2)
    q = m
    while(m < len(coords[n])):
        xvar = coords[n][m][0]
        yvar = coords[n][m][1]
        zvar = coords[n][q][2]
        
        coords[n][m] = [xvar, yvar, zvar]
        m = m + 1
        q = q - 1

    combinecoord = coords.copy()

    def AverageCoordsInCircle(keyx, keyy, coords, blurradius):
        boundx = int(blurradius / xdivval) + 1
        boundy = int(blurradius / ydivval) + 1
        n = keyy - boundy
        totval = 0
        cnt = 0
        while (n < (keyy + boundy)):
            m = keyx - boundx
            while (m < (keyx + boundx)):
                distval = 0
                hgval = 0
                if((m < len(coords[0])) and (m >= 0)) and ((n < len(coords)) and (n >= 0)):
                    distval = pow(pow(coords[keyy][keyx][0] - coords[n][m][0], 2) + pow(coords[keyy][keyx][1] - coords[n][m][1], 2), 0.5)
                    hgval = coords[n][m][2]
                else:
                    nux = coords[keyy][keyx][0] + m * xdivval
                    nuy = coords[keyy][keyx][1] + n * ydivval
                    distval = pow(pow(coords[keyy][keyx][0] - nux, 2) + pow(coords[keyy][keyx][1] - nuy, 2), 0.5)
                    hgval = blotorder[0]
                if(distval <= blurradius):
                    totval = totval + hgval
                    cnt = cnt + 1
                m = m + 1
            n = n +1
        if(cnt > 0):
            totval = totval / cnt
        else:
            totval = coords[keyx][keyy][2]
        return totval
        
    #blurring
    n = 0
    while (n < len(coords)):
        m = 0
        while (m < len(coords[n])):
            combinecoord[n][m][2] = AverageCoordsInCircle(m, n, coords, blurradius)
            #combinecoord[n][m][2] = coords[n][m][2]
            m = m + 1
        n = n + 1

    #basically, rebuild the post-blur combinecoord to give it edge values. mostly to make sure the interpolation function doesn't shit a brick.
    #funnily enough, didn't make a difference.
    combinecoord2 = []
    row1 = []
    row1.append([0, 0, combinecoord[0][0][2]])
    n = 0
    m = 0

    while (m < len(combinecoord[0])):
        row1.append([combinecoord[0][m][0], 0, combinecoord[0][m][2]])
        m = m + 1

    row1.append([width, 0, combinecoord[0][m-1][2]])
    combinecoord2.append(row1)
    n = 0
    while(n < len(combinecoord)):
        m = 0
        row = []
        row.append([0, combinecoord[n][m][1], combinecoord[n][m][2]])
        while(m < len(combinecoord[n])):
            row.append([combinecoord[n][m][0], combinecoord[n][m][1], combinecoord[n][m][2]])
            m = m + 1
        m = m - 1
        row.append([width, combinecoord[n][m][1], combinecoord[n][m][2]])
        combinecoord2.append(row)
        n = n + 1

    n = n - 1
    m = 0
    rowlast = []
    rowlast.append([0, height, combinecoord[n][m][2]])
    while m < len(combinecoord[n]):
        rowlast.append([combinecoord[n][m][0], height, combinecoord[n][m][2]])
        m = m + 1
    m = m - 1
    rowlast.append([width, height, combinecoord[n][m][2]])

    combinecoord2.append(rowlast)

    #print(str(combinecoord))

    #This part is fine, actually, imho.
    #oh god it's not fine
    #1/17/2024 - Adjusting things to try to fix edges
    #   - Replacing with Cubic Splines
    #ok cubic splines fixed it.

    #logistic function interpolation
##    def logi(val, xo, yo, xt, yt, dbg=0):
##        if(dbg != 0):
##            print("Logi function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))
##        steep = -1 * steepmultiplier / ((xt - xo))#
##        retval = yo + (yt - yo) * (1 / (1 + pow(math.e, steep * (val - (xo + xt)/2))))
##        retval = int(retval)
##        if(dbg != 0):
##            print("Output: " + str(retval))
##        return retval
    #cubic spline interpolation
##    def logi(val, xo, yo, xt, yt, dbg=0):
##        if(dbg != 0):
##            print("cubic spline function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))
##        #steep = -1 * steepmultiplier / ((xt - xo))#
##        #retval = yo + (yt - yo) * (1 / (1 + pow(math.e, steep * (val - (xo + xt)/2))))
##        #retval = int(retval)
##        A = (-2 * (yt - yo)) / pow((xt - xo), 3)
##        B = 3 * (yt - yo) / pow((xt - xo), 2)
##        C = 0
##        D = yo
##        xin = val - xo
##
##        retval = A * pow(xin, 3) + B * pow(xin, 2) + C * xin + D
##        #retval = retval
##        if(dbg != 0):
##            print("Output: " + str(retval))
##        return retval
    #linear interpolation
    def logi(val, xo, yo, xt, yt, dbg=0):
        if(dbg != 0):
            print("linear interp function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))
        #steep = -1 * steepmultiplier / ((xt - xo))#
        #retval = yo + (yt - yo) * (1 / (1 + pow(math.e, steep * (val - (xo + xt)/2))))
        #retval = int(retval)
        retval = ((yt - yo) / (xt - xo)) * (val - xo) + yo
        #retval = retval
        if(dbg != 0):
            print("Output: " + str(retval))
        return retval

    n = 0
    while (n < height):
        m = 0
        row = []
        while (m < width):
            #behold the greasiest mathematics you'll ever see in your life.
            hght = 0
            #1/17/2024 - first pass at improving this to make it less likely to give ground spikes
            #   - Reducing number of logi calls to 3 (top, bottom, top to bottom.
            #       - Still getting those edge pops.
            #1/19/2024 - We're now using closest coordinates by distance for corners.
            keyx = 0
            keyy = 0

            while((combinecoord2[keyy][keyx][0] <= m) and (keyx < len(combinecoord2[0]) - 1)):
                keyx = keyx + 1

            while((combinecoord2[keyy][keyx][1] <= n) and (keyy < len(combinecoord2) - 1)):
                keyy = keyy + 1
            #logi - top
            logit = logi(m, combinecoord2[keyy - 1][keyx - 1][0], combinecoord2[keyy - 1][keyx - 1][2], combinecoord2[keyy - 1][keyx][0], combinecoord2[keyy - 1][keyx][2])
            #logi - bot
            logib = logi(m, combinecoord2[keyy][keyx - 1][0], combinecoord2[keyy][keyx - 1][2], combinecoord2[keyy][keyx][0], combinecoord2[keyy][keyx][2])
            #logi - left
            logil = logi(n, combinecoord2[keyy - 1][keyx - 1][1], combinecoord2[keyy - 1][keyx - 1][2], combinecoord2[keyy][keyx - 1][1], combinecoord2[keyy][keyx - 1][2])
            #logi - right
            logir = logi(n, combinecoord2[keyy - 1][keyx][1], combinecoord2[keyy - 1][keyx][2], combinecoord2[keyy][keyx][1], combinecoord2[keyy][keyx][2])
            #logi - horiz
            logih = logi(n, combinecoord2[keyy - 1][keyx][1], logit, combinecoord2[keyy][keyx][1], logib)
            #logi - verti
            logiv = logi(m, combinecoord2[keyy][keyx - 1][0], logil, combinecoord2[keyy][keyx][0], logir)
            #logi - total
            #logitotal = int((logih + logiv) / 2)
            logitotal = (logih + logiv) / 2
            #print(str(logitotal))

            #q = input("waiting")

            hght = logitotal
            row.append(hght)
            m = m + 1

        genmap.append(row)
        n = n + 1

    return genmap, fliptype

def generate_condensemap ( genmap ):
    #renders map from heightmap to metalmap size
    condensemap = []
    n = 0
    while n < (len(genmap) - 1):
        m = 0
        row = []
        while m < (len(genmap[n]) - 1):
            row.append((genmap[n][m] + genmap[n][m+1] + genmap[n+1][m] + genmap[n+1][m+1]) / 4)
            m = m + 1
        condensemap.append(row)
        n = n + 1
    quartermap = []
    n = 0
    while n < len(condensemap):
        m = 0
        row = []
        while m < len(condensemap[n]):
            combine = 0
            q = 0
            while q < 2:
                r = 0
                while r < 2:
                    combine = combine + condensemap[n+q][m+r]
                    r = r + 1
                q = q + 1
            combine = combine / 4
            row.append(combine)
            m = m + 2
        quartermap.append(row)
        n = n + 2
    return quartermap

def generate_expandmap ( genmap ):
    #takes map from heightmap to texmap size
    flattened = []
    #first remove that pesky extra pixel
    n = 0
    while n < (len(genmap) - 1):
        m = 0
        row = []
        while m < (len(genmap[n]) - 1):
            row.append((genmap[n][m] + genmap[n][m+1] + genmap[n+1][m] + genmap[n+1][m+1]) / 4)
            m = m + 1
        flattened.append(row)
        n = n + 1
    #now multiply it by 8. we'll just duplicate the heightmap. Later we can investigate smoothing.
    heightmap_expanded = []
    n = 0
    while n < (len(flattened)):
        m = 0
        row = []
        while m < (len(flattened)):
            r = 0
            while r < 8:
                row.append(flattened[n][m])
                r = r + 1
            m = m + 1
        r = 0
        while r < 8:
            heightmap_expanded.append(row)
            r = r + 1
        n = n + 1
    return heightmap_expanded

def generate_gradient ( genmap ):
    #outputs a [x,y] list that states the averaged secant approximation.
    flattened = []
    #We're going to use the heightmap for this, and just duplicate the output by 8.
    #first remove that pesky extra pixel
    n = 0
    while n < (len(genmap) - 1):
        m = 0
        row = []
        while m < (len(genmap[n]) - 1):
            row.append((genmap[n][m] + genmap[n][m+1] + genmap[n+1][m] + genmap[n+1][m+1]) / 4)
            m = m + 1
        flattened.append(row)
        n = n + 1
    #find gradient, outputx8
    gradient = []
    n = 0
    while n < (len(flattened)):
        m = 0
        row = []
        while m < (len(flattened[n])):
            gradlx = 0
            gradrx = 0
            graduy = 0
            gradly = 0

            gradx = 0
            grady = 0
            if(m > 0):
                gradlx = (flattened[n][m-1] - flattened[n][m])
            if(m < (len(flattened[n]) - 1)):
                gradrx = (flattened[n][m] - flattened[n][m+1])
            if(n > 0):
                graduy = (flattened[n-1][m] - flattened[n][m])
            if(n < (len(flattened) - 1)):
                gradly = (flattened[n][m] - flattened[n+1][m])

            if(m == 0):
                gradx = gradrx
            elif(m == (len(flattened[n]) - 1)):
                gradx = gradlx
            else:
                gradx = (gradlx + gradrx) / 2
                
            if(n == 0):
                grady = gradly
            elif(n == (len(flattened) - 1)):
                grady = graduy
            else:
                grady = (gradly + graduy) / 2

            r = 0
            while r < 8:
                row.append([gradx,grady])
                r = r + 1
                
            m = m + 1
        r = 0
        while r < 8:
            gradient.append(row)
            r = r + 1
        n = n + 1
    return gradient

def generate_metalmap( genmap, start_positions, fliptype, map_properties ):
    metalmap = []
    metalpoints = []
    #condense...
    condensemap = generate_condensemap( genmap )
    xcoord = len(condensemap[0])
    ycoord = len(condensemap)
    #start positions...
    n = 0
    while (n < len(start_positions)):
        if((fliptype == 0) and start_positions[n][0] < (xcoord/2)) or ((fliptype == 1) and start_positions[n][1] < (ycoord/2)) or ((fliptype == 2) and start_positions[n][0] < (xcoord / 2)):
            rad = min(max(3, int((map_properties["mapsizex"]+map_properties["mapsizey"])/2)), 6)
            rnd = random.randint(-60, 60)
            tri1 = [int(start_positions[n][0] + rad * math.cos((math.pi / 180) * rnd)), int(start_positions[n][1] + rad * math.sin((math.pi / 180) * rnd))]
            tri2 = [int(start_positions[n][0] + rad * math.cos((2 * math.pi / 3) + (math.pi / 180) * rnd)), int(start_positions[n][1] + rad * math.sin((2 * math.pi / 3) + (math.pi / 180) * rnd))]
            tri3 = [int(start_positions[n][0] + rad * math.cos((4 * math.pi / 3) + (math.pi / 180) * rnd)), int(start_positions[n][1] + rad * math.sin((4 * math.pi / 3) + (math.pi / 180) * rnd))]
            metalpoints.append(tri1)
            metalpoints.append(tri2)
            metalpoints.append(tri3)
        n = n + 1
    #other points of interest...
    #currently just even spread + noise, later we can analyze the condensemap to do something more clever
    mexcount = max(int(((map_properties["mapsizex"] * map_properties["mapsizey"]) - map_properties["numplayers"] * 3) / 3.5), 2)
    mexcount = int(mexcount / 2)
    print("\tmexcount: " + str(mexcount * 2 + map_properties["numplayers"] * 6))

    def distfrom (xo, yo, xt, yt):
        distsq = pow(pow((xt - xo), 2) + pow((yt - yo), 2), 0.5)
        return distsq

    mexchk = 4 #checks this many pixels left/right of the mex possiblepoint
    mexdst = 32 * (map_properties["mapsizex"] + map_properties["mapsizey"]) // 24
    mexthresh = 0.01 #slope across mexchk up/down needs to be less than this
    
    if(fliptype == 0):
        n = 0
        while n < mexcount:
            #lbound = min(int(4 * xcoord / (2 * map_properties["mapsizex"])), int(4 * xcoord / 16))
            lbound = mexchk
            rbound = int(xcoord / 2) - mexdst // 2
            ubound = mexchk
            bbound = ycoord - mexchk
            
            possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
            m = 0
            r = 5000
            while((m < len(metalpoints)) and (r > 0)):
                dst = distfrom(possiblepoint[0], possiblepoint[1], metalpoints[m][0], metalpoints[m][1])
                #mex sanity check
                xl = max(possiblepoint[0] - mexchk, 0)
                xm = min(possiblepoint[0] + mexchk, xcoord - 1)
                yu = max(possiblepoint[1] - mexchk, 0)
                yl = min(possiblepoint[1] + mexchk, ycoord - 1)

                xs = abs(condensemap[possiblepoint[1]][xm] - condensemap[possiblepoint[1]][xl]) / (2 * mexchk)
                ys = abs(condensemap[yu][possiblepoint[0]] - condensemap[yl][possiblepoint[0]]) / (2 * mexchk)

                #print("xs: " + str(xs) + " / ys: " + str(ys))

                Skip = False
                if(xs > mexthresh) or (ys > mexthresh):
                    Skip = True

                if(dst < mexdst) or (Skip == True):
                    possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
                    m = 0
                    r = r - 1
                else:
                    m = m + 1
                    r = 5000
                
            if(r == 0):
                n = mexcount
                print("too cramped, couldn't find places to put additional mexes")
            else:
                metalpoints.append(possiblepoint)
            n = n + 1
    elif(fliptype == 1):
        n = 0
        while n < mexcount:
            ubound = mexchk
            bbound = int(ycoord / 2) - mexdst // 2
            lbound = mexchk
            rbound = xcoord - mexchk
            
            possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
            m = 0
            r = 5000
            while((m < len(metalpoints)) and (r > 0)):
                dst = distfrom(possiblepoint[0], possiblepoint[1], metalpoints[m][0], metalpoints[m][1])
                xl = max(possiblepoint[0] - mexchk, 0)
                xm = min(possiblepoint[0] + mexchk, xcoord - 1)
                yu = max(possiblepoint[1] - mexchk, 0)
                yl = min(possiblepoint[1] + mexchk, ycoord - 1)

                xs = abs(condensemap[possiblepoint[1]][xm] - condensemap[possiblepoint[1]][xl]) / (2 * mexchk)
                ys = abs(condensemap[yu][possiblepoint[0]] - condensemap[yl][possiblepoint[0]]) / (2 * mexchk)

                #print("xs: " + str(xs) + " / ys: " + str(ys))

                Skip = False
                if(xs > mexthresh) or (ys > mexthresh):
                    Skip = True

                if(dst < mexdst) or (Skip == True):
                    possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
                    m = 0
                    r = r - 1
                else:
                    m = m + 1
                    r = 5000
            if(r == 0):
                n = mexcount
                print("too cramped, couldn't find places to put additional mexes")
            else:
                metalpoints.append(possiblepoint)
            n = n + 1
    elif(fliptype == 2):    #i'm lazy, we'll just make this identical to flipcount 0, but then rotate it by 180 to place the mexes on the other half
        n = 0
        while n < mexcount:
            lbound = mexchk
            rbound = int(xcoord / 2) - mexdst // 2
            ubound = mexchk
            bbound = ycoord - mexchk

            possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
            m = 0
            r = 5000
            while((m < len(metalpoints)) and (r > 0)):
                dst = distfrom(possiblepoint[0], possiblepoint[1], metalpoints[m][0], metalpoints[m][1])
                xl = max(possiblepoint[0] - mexchk, 0)
                xm = min(possiblepoint[0] + mexchk, xcoord - 1)
                yu = max(possiblepoint[1] - mexchk, 0)
                yl = min(possiblepoint[1] + mexchk, ycoord - 1)

                xs = abs(condensemap[possiblepoint[1]][xm] - condensemap[possiblepoint[1]][xl]) / (2 * mexchk)
                ys = abs(condensemap[yu][possiblepoint[0]] - condensemap[yl][possiblepoint[0]]) / (2 * mexchk)

                #print("xs: " + str(xs) + " / ys: " + str(ys))

                Skip = False
                if(xs > mexthresh) or (ys > mexthresh):
                    Skip = True

                if(dst < mexdst) or (Skip == True):
                    possiblepoint = [random.randint(lbound, rbound), random.randint(ubound, bbound)]
                    m = 0
                    r = r - 1
                else:
                    m = m + 1
                    r = 5000
                
            if(r == 0):
                n = mexcount
                print("too cramped, couldn't find places to put additional mexes")
            else:
                metalpoints.append(possiblepoint)
            n = n + 1
            
    #spread... (have to make it a 2x2 red dot to count as a mex)
    metalpix = []
    n = 0
    while n < len(metalpoints):
        pxr = [metalpoints[n][0]+1, metalpoints[n][1]]
        pxb = [metalpoints[n][0], metalpoints[n][1]+1]
        pxrb = [metalpoints[n][0]+1, metalpoints[n][1]+1]
        
        metalpix.append(metalpoints[n])
        metalpix.append(pxr)
        metalpix.append(pxb)
        metalpix.append(pxrb)
        n = n + 1
    
    #mirror...
    mirrorpix = []
    n = 0
    while n < len(metalpix):
        ditto = [metalpix[n][0], metalpix[n][1]]
        if(fliptype == 0):
            ditto[0] = (xcoord - 1) - metalpix[n][0]
        elif(fliptype == 1):
            ditto[1] = (ycoord - 1) - metalpix[n][1]
        elif(fliptype == 2):
            ditto[0] = (xcoord - 1) - metalpix[n][0]
            ditto[1] = (ycoord - 1) - metalpix[n][1]
        mirrorpix.append(metalpix[n])
        mirrorpix.append(ditto)
        n = n + 1
    #make as rgb array...
    pixelarray = []
    n = 0
    while n < ycoord:
        m = 0
        row = []
        while m < xcoord:
            row.append((0, 0, 0))
            m = m + 1
        pixelarray.append(row)
        n = n + 1

    metaltype = random.randint(0, 1)
    if(metaltype == 0):
        print("\tMetaltype: Constant")
    if(metaltype == 1):
        print("\tMetaltype: Scaling-Up")

    def GetMetal( xp, yp, xc, yc, fliptype):
        retval = 255
        if(fliptype == 0):
            p = min(max(-1 * abs(xp - xc) * 2 / xc + 1.25, 0.5), 1)
            retval = 255 * p
        if(fliptype == 1):
            p = min(max(-1 * abs(yp - yc) * 2 / yc + 1.25, 0.5), 1)
            retval = 255 * p
        if(fliptype == 2):
            dst = pow(pow((xp - xc),2) + pow((yp-yc), 2), 0.5)
            mxdst = pow(pow(xc,2) + pow(yc, 2), 0.5)
            p = min(max(-1 * abs(dst - mxdst) * 2 / mxdst + 1.25, 0.5), 1)
            retval = 255 * p

        return int(retval)
        
    n = 0
    while n < len(mirrorpix):
        if (mirrorpix[n][0] < xcoord) and (mirrorpix[n][1] < ycoord):
            if(metaltype == 0):
                pixelarray[mirrorpix[n][0]][mirrorpix[n][1]] = (255, 0, 0) #currently only max or nil for metal, will adjust later
            elif(metaltype == 1):
                pixelarray[mirrorpix[n][0]][mirrorpix[n][1]] = (GetMetal(mirrorpix[n][0], mirrorpix[n][1], xcoord/2, ycoord/2, fliptype), 0, 0)
        else:
            print("mex out of bounds at: " + str(mirrorpix[n]))
        n = n + 1
    return pixelarray

def generate_texmap ( genmap, texture_family, mult, minh ):
    texmap = []
    #pull textures from texture family.
    pulldir = "textures/families/" + texture_family + "/"
    #   open texture list
    textureinfo = open(pulldir + "texturelist.txt", 'r')
    textureinfo_text = textureinfo.read()
    textureinfo.close()
    #   split by '\n'
    ti_byrow = textureinfo_text.split('\n')
    texturepack = []
    infopack = []
    n = 0
    while n < len(ti_byrow):
        commasep = ti_byrow[n].split(',')
        if(len(commasep) == 3):
            texturepack.append(commasep[0])
            infopack.append([int(commasep[1]), int(commasep[2])])
            print(str(commasep[0]) + ": " + str(commasep[1]) + ", " + str(commasep[2]))
        n = n + 1
    
    #expand...
    expanded_heightmap = generate_expandmap( genmap )
    gradient_heightmap = generate_gradient ( genmap )
    #load textures...
    #   - 0 : lowground (0-20 clean, 21-40 merged)
    #   - 1 : midground (41-60 clean, 61-80 merged)
    #   - 2 : highground (81-100 clean)
    texar = []
    texseq = []
    n = 0
    while n < len(texturepack):
        ts = []
        with Image.open(pulldir + texturepack[n]) as tex:
            ts = list(tex.getdata())
            tex.close()
            
        w = infopack[n][0]
        h = infopack[n][1]

        ta=[]
        m = 0
        while m < h:
            l = 0
            row = []
            while (l < w):
                row.append(ts[m * w + l])
                l = l + 1
            ta.append(row)
            m = m + 1
        texseq.append(ta)
        #print("added: " + pulldir + texturepack[n])
        n = n + 1

    #merge textures...
    total_width = len(expanded_heightmap[0])
    total_height = len(expanded_heightmap)

    def merge_function( x, y, tex, ip, height ):
        #tupa/tupb/tupc tuples from pixels
        r = 0
        g = 0
        b = 0

        if(len(tex) > 1):
            key = 0
            n = len(tex) - 1
            while(height > ((100/n) * key)):
                key = key + 1
            key = key - 1
            while(key+1 > (len(ip) - 1)):
                print("key oob, height is: " + str(height))
                print(str(len(ip)))
                key = key - 1
            
            lw = ip[key][0]
            lh = ip[key][1]
            lr = tex[key][y%lh][x%lw][0]
            lg = tex[key][y%lh][x%lw][1]
            lb = tex[key][y%lh][x%lw][2]

            rw = ip[key+1][0]
            rh = ip[key+1][1]
            rr = tex[key+1][y%rh][x%rw][0]
            rg = tex[key+1][y%rh][x%rw][1]
            rb = tex[key+1][y%rh][x%rw][2]

            p = n * height / 100 - key
            q = 1 - p

            r = lr * q + rr * p
            g = lg * q + rg * p
            b = lb * q + rb * p
            #print("height: " + str(height) + "/ key: " + str(key) + "/ p: " + str(p))
        elif(len(tex) > 0):
            #Shouldn't happen, but if there's only one texture, output that texture, merged with heightmap
            lw = ip[0][0]
            lh = ip[0][1]

            hmod = 25 + height * 2
            r = (tex[0][y%lh][x%lw][0] * 0.5 + hmod * 0.5)
            g = (tex[0][y%lh][x%lw][1] * 0.5 + hmod * 0.5)
            b = (tex[0][y%lh][x%lw][2] * 0.5 + hmod * 0.5)
        else:
            #No found texture? (somehow something went very wrong) - just output expanded_heightmap
            hmod = 25 + height * 2

            r = hmod
            g = hmod
            b = hmod
        return (int(r), int(g), int(b))

    def gradient_merge(m, n, gradient, curpixel):
        r = curpixel[0]
        g = curpixel[1]
        b = curpixel[2]

        gradmag = pow(pow(gradient[n][m][0],2) + pow(gradient[n][m][1], 2),0.5)
        p = max(gradmag / 1, 1)
        q = 1-p
        nr = r * q
        ng = g * q
        nb = b * q

        return (int(r), int(g), int(b))

    n = 0
    while (n < total_height):
        m = 0
        row = []
        while (m < total_width):
            ah = (expanded_heightmap[n][m] - minh) * mult
            merge_pixel = merge_function(m, n, texseq, infopack, ah)
            gradpix = gradient_merge(m, n, gradient_heightmap, merge_pixel)
            row.append(gradpix)
            m = m + 1
        texmap.append(row)
        n = n + 1
    #place metal patches...

    
    return texmap

def generate_startpositions ( genmap, fliptype, map_properties ):
    start_positions = []
    #condense...
    condensemap = generate_condensemap ( genmap )
    #with fliptype. 0 is left/right. 1 is top/bottom. 2 is bottom left/top right or bottom right/top left
    #currently just an even spread, later on we can analyze the condensemap to make this a bit smarter.
    xcoord = len(condensemap[0])
    ycoord = len(condensemap)

    backline = min(4, map_properties["numplayers"])
    frontline = map_properties["numplayers"] - backline
    choice = 0
    if(fliptype == 0):
        xset = max(int(xcoord / (map_properties["mapsizex"] * 2)), int(xcoord / 16))
        xset2 = xcoord - xset
        n = 0
        while n < backline:
            yset = int(ycoord * (n + 1) / (backline + 1))
            start_positions.append([xset, yset])
            start_positions.append([xset2, yset])
            n = n + 1
        xset = max(int(3 * xcoord / (map_properties["mapsizex"] * 2)), int(3 * xcoord / 16))
        xset2 = xcoord - xset
        n = 0
        while n < frontline:
            yset = int(ycoord * (n + 1) / (frontline + 1))
            start_positions.append([xset, yset])
            start_positions.append([xset2, yset])
            n = n + 1
    elif(fliptype == 1):
        yset = max(int(ycoord / (map_properties["mapsizey"] * 2)), int(ycoord / 16))
        yset2 = ycoord - yset
        n = 0
        while n < backline:
            xset = int(xcoord * (n + 1) / (backline + 1))
            start_positions.append([xset, yset])
            start_positions.append([xset, yset2])
            n = n + 1
        yset = max(int(3 * ycoord / (map_properties["mapsizey"] * 2)), int(3 * ycoord / 16))
        yset2 = ycoord - yset
        n = 0
        while n < frontline:
            xset = int(xcoord * (n + 1) / (frontline + 1))
            start_positions.append([xset, yset])
            start_positions.append([xset, yset2])
            n = n + 1
    elif(fliptype == 2):
        choice = random.randint(0, 1)
        radius = 3 * max(int(min(xcoord, ycoord) / (min(map_properties["mapsizex"], map_properties["mapsizey"]) * 2)), int(min(xcoord, ycoord) / 16))
        n = 0
        while n < backline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = ycoord * choice + math.pow(-1, choice) * int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            start_positions.append([xset, yset])
            #bottom right/top right
            xset = xcoord - int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = ycoord * (1 - choice) + math.pow(-1, (1 - choice)) * int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            start_positions.append([xset, yset])
            n = n + 1
        radius = int(1.5 * max(3 * int(min(xcoord, ycoord) / (2 * min(map_properties["mapsizex"], map_properties["mapsizey"]))), int(3 * min(xcoord, ycoord) / 16)))
        n = 0
        while n < frontline:
            #top left/bottom left
            xset = int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = ycoord * choice + math.pow(-1, choice) * int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            start_positions.append([xset, yset])
            #bottom right/top right
            xset = xcoord - int(radius * math.cos((math.pi / 2) * (n + 1) / (backline + 1)))
            yset = ycoord * (1 - choice) + math.pow(-1, (1 - choice)) * int(radius * math.sin((math.pi / 2) * (n + 1) / (backline + 1)))
            start_positions.append([xset, yset])
            #bottom right/top right
            n = n + 1
    return start_positions, choice

def GetTextureFamilies():
    retval = []
    textfam = "textures/families/"

    scanned = os.scandir(textfam)

    for objs in scanned:
        if objs.is_dir():
            retval.append(objs.name)
    return retval

def normalize_height( genmap ):
    maxh = 0
    minh = 0
    n = 0
    while n < len(genmap):
        m = 0
        while m < len(genmap[n]):
            if(genmap[n][m] > maxh):
                maxh = genmap[n][m]
            if(genmap[n][m] < minh):
                minh = genmap[n][m]
            m = m + 1
        n = n + 1

    mult = 100 / (maxh - minh)
    return mult, minh

def main( map_properties ):
    texture_families = []
    texture_families = GetTextureFamilies()

    curdir = os.getcwd()
    
    random.seed(a=map_properties["seed"], version=2)
    
    texture_picked = random.choice(texture_families)
    
    genmap = []

    mapname = 'srmg_' + str(map_properties["seed"])
    dirname = 'maps/' + mapname + '/'

    os.makedirs(dirname, exist_ok=True)
    os.makedirs(dirname+'maps/', exist_ok=True)
    
    print("Map: " + mapname)
    print("\tTextures Used: " + str(texture_picked))

    #generate map
    genmap = []
    fliptype = 0
    if(map_properties["generation_type"] == "prefab"):
        print("Using Prefabs.")
        os.chdir(curdir + '/prefab_generation')
        genmap, fliptype = prefab_generation.prefab_generation.generate_map_using_prefabs(map_properties)
        os.chdir(curdir)
    elif(map_properties["generation_type"] == "voronoi"):
        print("Using Voronoi.")
        os.chdir(curdir + '/voronoi_generation')
        genmap, fliptype = voronoi_generation.voronoi_generation.generate_map_using_voronoi(map_properties)
        os.chdir(curdir)
    else:
        print("Using Default.")
        genmap, fliptype = generate_map(map_properties)
    #normalize height
    mult, minh = normalize_height(genmap)
    #start positions
    start_positions, choice = generate_startpositions(genmap, fliptype, map_properties)

    #Heightmap
    heightmap_img = generate_heightmap(genmap, mult, minh)
    
    heightmap_width = map_properties["mapsizex"] * 64 + 1
    heightmap_height = map_properties["mapsizey"] * 64 + 1
    
    heightmap_png_file = open(dirname + mapname + '_height.png', 'wb')
    heightmap_png_writer = png.Writer(heightmap_width, heightmap_height, greyscale=True, bitdepth=16)
    heightmap_png_writer.write(heightmap_png_file, heightmap_img)
    heightmap_png_file.close()

    heightmap_filename = dirname + mapname + '_height.png'
    #Metalmap
    metmap = generate_metalmap(genmap, start_positions, fliptype, map_properties)

    metmap_img = Image.new('RGB', (map_properties["mapsizex"] * 32, map_properties["mapsizey"] * 32), 'black')
    metmap_img_pixels = metmap_img.load()
    n = 0
    while n < len(metmap):
        m = 0
        while(m < len(metmap[n])):
            metmap_img_pixels[n, m] = metmap[n][m]
            m = m + 1
        n = n + 1
    metmap_img.save(dirname + mapname + '_metal.bmp')

    metmap_filename = dirname + mapname + '_metal.bmp'
    #TextureMap
    texmap = generate_texmap(genmap, texture_picked, mult, minh)

    texmap_img = Image.new('RGB', (map_properties["mapsizex"] * 512, map_properties["mapsizey"] * 512), 'black')
    texmap_img_pixels = texmap_img.load()
    n = 0
    while n < len(texmap):
        m = 0
        while(m < len(texmap[0])):
            texmap_img_pixels[m, n] = texmap[n][m]
            m = m + 1
        n = n + 1
    texmap_img.save(dirname + mapname + '_texture.bmp')

    texmap_filename = dirname + mapname + '_texture.bmp'
    #mapinfo.lua
    mapinfo_template = open('backup_info/mapinfo_template.lua', 'r', encoding="utf8")
    mapinfo_template_text = mapinfo_template.read()
    mapinfo_template.close()

    #things to replace:
    #   -[NAME]
    #   -[MAXMETAL] (0.8 standard)
    #   -[MINHEIGHT] (50 standard)
    #   -[MAXHEIGHT] (1250 standard)
    #   -[MINWIND]
    #   -[MAXWIND]
    #Add different fog colors, sun colors, cloud colors - I can define this based on the texture pack
    metaltype = [1.6, 2.4, 3.2]
    metalchoice = random.choice(metaltype)
    print("\tmetaldensity: " + str(metalchoice))
    minheight = 50
    print("\tminheight: " + str(minheight))
    maxheight = random.randint(2, 4) * 300 + minheight
    print("\tmaxheight: " + str(maxheight))
    minwind = int(metalchoice * 10 / 3)
    print("\tminwind: " + str(minwind))
    maxwind = int(metalchoice * 25 / 3)
    print("\tmaxwind: " + str(maxwind))
    mapinfo_vars = {"[NAME]": mapname,
                    "[MAXMETAL]": metalchoice,
                    "[MINHEIGHT]": minheight,
                    "[MAXHEIGHT]": maxheight,
                    "[MINWIND]": minwind,
                    "[MAXWIND]": maxwind,
                    "[FOGR]": 0.8,
                    "[FOGG]": 0.8,
                    "[FOGB]": 0.8,
                    "[SKYR]": 0.8,
                    "[SKYG]": 0.8,
                    "[SKYB]": 0.8,
                    "[WATR]": 0.67,
                    "[WATG]": 0.8,
                    "[WATB]": 1.0}

    #Set texture family based map settings.
    ti_text = ""
    try:
        texture_info = open("textures/families/" + texture_picked + "/mapinfo.txt", 'r')
        ti_text = texture_info.read()
        texture_info.close()
    except:
        print("texture mapinfo.txt not found. proceeding with blank mapinfo.txt")
        ti_text = ""

    ti_text_split = ti_text.split('\n')

    for n in ti_text_split:
        ti_text_split_split = n.split(',')
        if(len(ti_text_split_split) == 2):
            mapinfo_vars[ti_text_split_split[0]] = ti_text_split_split[1]
            print("Replaced " + ti_text_split_split[0] + " value with " + ti_text_split_split[1])

    mapinfo_vars["[MAXHEIGHT]"] = int(int(mapinfo_vars["[MAXHEIGHT]"]) + minh) / mult
    mapinfo_vars["[MINHEIGHT]"] = int(int(mapinfo_vars["[MINHEIGHT]"]) + minh) / mult
    print("Updated [MAXHEIGHT] to: " + str(mapinfo_vars["[MAXHEIGHT]"]))
    print("Updated [MINHEIGHT] to: " + str(mapinfo_vars["[MINHEIGHT]"]))

    for key in mapinfo_vars:
        mapinfo_template_text = mapinfo_template_text.replace(key, str(mapinfo_vars[key]))

    mapinfo_out = open(dirname + 'mapinfo.lua', 'w')
    mapinfo_out.write(mapinfo_template_text)
    mapinfo_out.close()

    print("Written to: " + dirname + "mapinfo.lua")

    #creating map_startboxes.lua

    msb_file = open('backup_info/map_startboxes_template.lua', 'r')
    msb_file_text = msb_file.read()
    msb_file.close()

    #defaults to horizontal
    msb_config = {"[STARTPOINT-1-TL]": "{0, 0}",
                  "[STARTPOINT-1-TR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", 0}",
                  "[STARTPOINT-1-BL]": "{0, " + str(int(map_properties["mapsizey"] * 512)) + "}",
                  "[STARTPOINT-1-BR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                  "[STARTPOINT-1-NAME]": "Left Side",
                  "[STARTPOINT-1-SHORT]": "LS",
                  "[STARTPOINT-2-TL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", 0}",
                  "[STARTPOINT-2-TR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", 0}",
                  "[STARTPOINT-2-BL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                  "[STARTPOINT-2-BR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                  "[STARTPOINT-2-NAME]": "Right Side",
                  "[STARTPOINT-2-NAME]": "RS"}

    if(fliptype == 1):      #vertical
        msb_config = {"[STARTPOINT-1-TL]": "{0, 0}",
                      "[STARTPOINT-1-TR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", 0}",
                      "[STARTPOINT-1-BL]": "{0, " + str(int(map_properties["mapsizey"] * 512/8)) + "}",
                      "[STARTPOINT-1-BR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 512/8)) + "}",
                      "[STARTPOINT-1-NAME]": "Top Side",
                      "[STARTPOINT-1-SHORT]": "TS",
                      "[STARTPOINT-2-TL]": "{0, " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-2-TR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-2-BL]": "{0, " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-BR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-NAME]": "Bottom Side",
                      "[STARTPOINT-2-NAME]": "BS"}
    if(fliptype == 2):      #quads
        if(choice == 0):    # Top left/bottom Right
            msb_config = {"[STARTPOINT-1-TL]": "{0, 0}",
                      "[STARTPOINT-1-TR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", 0}",
                      "[STARTPOINT-1-BL]": "{0, " + str(int(map_properties["mapsizey"] * 512/8)) + "}",
                      "[STARTPOINT-1-BR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512/8)) + "}",
                      "[STARTPOINT-1-NAME]": "Top Left",
                      "[STARTPOINT-1-SHORT]": "TL",
                      "[STARTPOINT-2-TL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-2-TR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-2-BL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-BR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-NAME]": "Bottom Right",
                      "[STARTPOINT-2-NAME]": "BR"}
        if(choice == 1):    # Bottom left/top right
            msb_config = {"[STARTPOINT-1-TL]": "{0, " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-1-TR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 7 * 512/8)) + "}",
                      "[STARTPOINT-1-BL]": "{0, " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-1-BR]": "{" + str(int(map_properties["mapsizex"] * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-1-NAME]": "Bottom Left",
                      "[STARTPOINT-1-SHORT]": "BL",
                      "[STARTPOINT-2-TL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", 0}",
                      "[STARTPOINT-2-TR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", 0}",
                      "[STARTPOINT-2-BL]": "{" + str(int(map_properties["mapsizex"] * 7 * 512/8)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-BR]": "{" + str(int(map_properties["mapsizex"] * 512)) + ", " + str(int(map_properties["mapsizey"] * 512)) + "}",
                      "[STARTPOINT-2-NAME]": "Top Right",
                      "[STARTPOINT-2-NAME]": "TR"}

    for key in msb_config:
        msb_file_text = msb_file_text.replace(key, str(msb_config[key]))

    os.makedirs(dirname + 'mapconfig', exist_ok=True)

    msb_out = open(dirname + 'mapconfig/' + 'map_startboxes.lua', 'w')
    msb_out.write(msb_file_text)
    msb_out.close()

    #mapconv execution
    def QuoteWrap ( istr ):
    #    ostr = "\'" + istr + "\'"
        ostr = istr
        return ostr
    mapfile_filename = dirname + 'maps/' + mapname + '.smf'
    mapfile_filename2 = dirname + 'maps/' + mapname + '.smt'
    #pymapconv.exe -t texmap_filename -a heightmap_filename -m metmap_filename -x maxheight -n minheight -o 
    pymapconv_location = "pymapconv.exe"
    #pymapconv_args = "-o" + QuoteWrap(mapfile_filename) + " -t " + QuoteWrap(texmap_filename) + " -a " + QuoteWrap(heightmap_filename) + " -m " + metmap_filename# + " -x " + str(maxheight) + " -n " + str(minheight)
    #pymapconv_args = "-t " + texmap_filename + " -a " + heightmap_filename + " -m " + metmap_filename + " -x " + str(maxheight) + " -n " + str(minheight) + " -o " + mapfile_filename
    #pymapconv_args = pymapconv_args + ' -k None ' + ' -j None ' + ' -f None ' + ' -r 0 ' + ' -e None ' + ' -g None ' + ' -y None '
    pymapconv_args_out = "-o" + QuoteWrap(mapfile_filename)
    pymapconv_args_tex = "-t" + QuoteWrap(texmap_filename)
    pymapconv_args_hgt = "-a" + QuoteWrap(heightmap_filename)
    pymapconv_args_met = "-m" + QuoteWrap(metmap_filename)
    subprocess.run([pymapconv_location, pymapconv_args_out, pymapconv_args_tex, pymapconv_args_hgt, pymapconv_args_met])

    #archive listing:
    listfile = open(dirname + 'listfile.txt', 'w')
    mf_fn = "maps/" + mapname + ".smf"
    mf_fn2 = "maps/" + mapname + ".smt"
    tm_fn = mapname + "_texture.bmp"
    hm_fn = mapname + "_height.png"
    mm_fn = mapname + "_metal.bmp"
    msb_fn = "mapconfig/map_startboxes.lua"
    listfile_text = "mapinfo.lua\n" + mf_fn + "\n" + mf_fn2 + "\n" + tm_fn + "\n" + hm_fn + "\n" + mm_fn + "\n" + msb_fn
    listfile.write(listfile_text)
    listfile.close()
    
    #7zip execution
    os.chdir(dirname)
    archive_filename = mapname + '.sd7'

    with py7zr.SevenZipFile(archive_filename, 'w') as archive:
        archive.write("mapinfo.lua")
        archive.write(mf_fn)
        archive.write(mf_fn2)
        archive.write(tm_fn)
        archive.write(hm_fn)
        archive.write(mm_fn)
        archive.write(msb_fn)

    os.chdir(curdir)
    

if __name__ == "__main__":
    map_properties = {
        "mapsizex": 12,
        "mapsizey": 12,
        "seed": 66251,
        "numplayers": 8,
        "generation_type": "voronoi"     #normal, prefab, voronoi
        }
    main(map_properties)
    
    print("finished")
