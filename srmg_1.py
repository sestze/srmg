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
#   - Metalmap
#   - Texturemap



import random
import struct
import zlib
import math
import png
import os
import subprocess
import py7zr

import copy

import prefab_generation.prefab_generation

import voronoi_generation.voronoi_generation

import path_generation.path_generation

import grid_generation.grid_generation

import provided_generation.provided_generation

import perlin_generation.perlin_generation

import complicated_texturing.complicated_texturing

#from typing import BinaryIO, List, Tuple
from PIL import Image

# mirror_array, takes in the genmap and fliptype and mirrors according to the fliptype
#   - 0 - Horizontal
#   - 1 - Vertical
#   - 2 - TL/BR
#   - 3 - BL/TR
#   - 4 - Quads (corners)
#   - 5 - Quads (centers)

def mirror_array ( inmap, fliptype ):
    genmap_copy = copy.deepcopy(inmap)
    height = len(inmap)
    width = len(inmap[0])
    print("mirroring...")
    if(fliptype == 0):
        #horizontal
        n = 0
        while(n < height):
            m = 0
            while (m < (width / 2)):
                genmap_copy[n][(width - 1) - m] = inmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 1):
        #vertical
        n = 0
        while n < (height / 2):
            m = 0
            while m < width:
                genmap_copy[(height - 1) - n][m] = inmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 2):
        #top left to bottom right
        n = 0
        while n < height:
            m = 0
            while n < (height - (height / width) * m):
                genmap_copy[(height - 1) - m][(width - 1) - n] = inmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 3):
        #bottom left to top right
        n = 0
        while n < height:
            m = 0
            while n > ((height / width) * m):
                genmap_copy[m][n] = inmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 4):
        #quads
        n = 0
        while n < (height / 2):
            m = 0
            while m < (width / 2):
                genmap_copy[(height - 1) - n][m] = inmap[n][m]
                genmap_copy[n][(width - 1) - m] = inmap[n][m]
                genmap_copy[(height - 1) - n][(width - 1) - m] = inmap[n][m]
                m = m + 1
            n = n + 1
    if(fliptype == 5):
        #crosses
        n = 0
        while n < (height):
            m = 0
            while m < (-1 * (width / height) * abs(n - height / 2) + width / 2) + 1:
                if( m < width ):
                    genmap_copy[m][n] = inmap[n][m]
                    genmap_copy[(height - 1) - n][(width - 1) - m] = inmap[n][m]
                    genmap_copy[(height - 1) - m][(width - 1) - n] = inmap[n][m]
                m = m + 1
            n = n + 1
    print("mirroring complete")        
    return genmap_copy

#blurs the map according to fliptype to remove "seams" from mirroring and smooth out terrain changes.
def blurmap ( genmap, general, seam, fliptype ):
    height = len(genmap)
    width = len(genmap[0])

    genmap_copy = copy.deepcopy(genmap)

    def clamp(val, l, u):
        if l > val:
            return l
        if u < val:
            return u
        return val
    
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
    
    scaleblur = seam
    if(scaleblur > 0):
        print("seam blurring")
        #horizontal or quad
        if(fliptype == 0) or (fliptype == 4):
            n = 0
            while (n < height):
                m = width // 2 - scaleblur
                while(m < (width // 2 + scaleblur)):
                    dst = max(-1 * abs(m - width // 2) + scaleblur, 0)
                    genmap_copy[n][m] = AverageCoordsInCircle(m, n, genmap, dst)
                    m = m + 1
                n = n + 1
        #vertical or quad
        if(fliptype == 1) or (fliptype == 4):
            n = height // 2 - scaleblur
            while (n < (height // 2 + scaleblur)):
                m = 0
                while(m < width):
                    dst = max(-1 * abs(n - height // 2) + scaleblur, 0)
                    genmap_copy[n][m] = AverageCoordsInCircle(m, n, genmap, dst)
                    m = m + 1
                n = n + 1
        #top left to bottom right or cross
        if(fliptype == 2) or (fliptype == 5):
            n = 0
            while (n < height):
                m = 0
                while (m < width):
                    #oh boy, time for algebra
                    #i did it on a piece of scratch paper. trust me.
                    xval = (pow(height, 2) * width + m * pow(height, 2) - n * width * height) / (pow(width, 2) + pow(height, 2))
                    yval = height - width / height * xval

                    dst = pow(pow(xval - m, 2) + pow(yval - n, 2), 0.5)
                    if(dst < scaleblur):
                        adst = int(max(-1 * dst + scaleblur, 0))
                        genmap_copy[n][m] = AverageCoordsInCircle(m, n, genmap, adst)
                    m = m + 1
                n = n + 1
        #bottom left to top right or cross
        if(fliptype == 3) or (fliptype == 5):
            n = 0
            while (n < height):
                m = 0
                while (m < width):
                    #again, more algebra
                    #i did it on a piece of scratch paper. trust me.
                    xval = (height * width * n + pow(width, 2) * m) / (pow(width, 2) + pow(height, 2))
                    yval = height / width * xval

                    dst = pow(pow(xval - m, 2) + pow(yval - n, 2), 0.5)
                    if(dst < scaleblur):
                        adst = int(max(-1 * dst + scaleblur, 0))
                        genmap_copy[n][m] = AverageCoordsInCircle(m, n, genmap, adst)
                    m = m + 1
                n = n + 1
        print("seam blurring done")
        
    second_copy = copy.deepcopy(genmap_copy)

    print("global blurring...")
    #Global blur.
    blurrad = general #blurs all pix around general units of the pixel
    count = width * height / 20
    perc = 100 * count / (width * height)
    n = 0
    while(n < height):
        m = 0
        while (m < width):
            genmap_copy[n][m] = AverageCoordsInCircle(m, n, second_copy, blurrad)
            if(n * m > count):
                print("... " + str(int(perc)) + "% done...")
                count = count + width * height / 20
                perc = 100 * count / (width * height)
            m = m + 1
        n = n + 1
    print("... global blurring done.")

    print("blurring complete")
    
    return genmap_copy

def atrophymap( genmap, iterations ):
    genmap_copy = copy.deepcopy(genmap)

    print("running atrophy")
    width = len(genmap[0])
    height = len(genmap)
    its = 0
    while its < iterations:
        #all (using copied array)
        second_copy = copy.deepcopy(genmap_copy)
        n = 0
        while n < height:
            m = 0
            while m < width:
                neighbors = ["n/a", "n/a", "n/a",
                             "n/a", "n/a", "n/a",
                             "n/a", "n/a", "n/a"]
                grid_neighbors = [[n-1, m-1], [n-1, m], [n-1, m+1],
                                  [n, m-1], [n, m], [n, m+1],
                                  [n+1, m-1], [n+1, m], [n+1, m+1]]
                share = 0
                grid_read = range(0, 9)
                p = 0
                while p < len(grid_read):
                    q = grid_read[p]
                    if(grid_neighbors[q][0] > 0) and (grid_neighbors[q][0] < height) and (grid_neighbors[q][1] > 0) and (grid_neighbors[q][1] < width):
                        if(genmap_copy[n][m] > genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]):
                            neighbors[q] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]
                            share = share + 1
                    p = p + 1
                mindisp = 999999
                tdisp = 0
                p = 0
                while p < len(grid_read):
                    q = grid_read[p]
                    if(neighbors[q] != "n/a"):
                        disp = genmap_copy[n][m] - neighbors[q]
                        if(disp < mindisp):
                            mindisp = disp
                            tdisp = tdisp + disp 
                    p = p + 1
                if(share > 0):
                    second_copy[n][m] = genmap_copy[n][m] - mindisp * (1 - 1 / (share + 1))
                p = 0
                while p < len(grid_read):
                    q = grid_read[p]
                    if(neighbors[q] != "n/a"):
                        disp = genmap_copy[n][m] - neighbors[q]
                        second_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] + disp / tdisp * (mindisp * (1 - 1 / (share + 1)))
                    p = p + 1
                m = m + 1
            n = n + 1
        del genmap_copy
        genmap_copy = copy.deepcopy(second_copy)
        del second_copy
##        n = height - 1
##        #br
##        n = 0
##        while n < height:
##            m = 0
##            while m < width:
##                neighbors = ["n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a"]
##                grid_neighbors = [[n-1, m-1], [n-1, m], [n-1, m+1],
##                                  [n, m-1], [n, m], [n, m+1],
##                                  [n+1, m-1], [n+1, m], [n+1, m+1]]
##                share = 0
##                grid_read = [0, 1, 3]
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(grid_neighbors[q][0] > 0) and (grid_neighbors[q][0] < height) and (grid_neighbors[q][1] > 0) and (grid_neighbors[q][1] < width):
##                        if(genmap_copy[n][m] > genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]):
##                            neighbors[q] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]
##                            share = share + 1
##                    p = p + 1
##                mindisp = 999999
##                tdisp = 0
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        if(disp < mindisp):
##                            mindisp = disp
##                            tdisp = tdisp + disp 
##                    p = p + 1
##                genmap_copy[n][m] = genmap_copy[n][m] - mindisp * (1 - 1 / (share + 1))
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] + disp / tdisp * (mindisp * (1 - 1 / (share + 1)))
##                    p = p + 1
##                m = m + 1
##            n = n + 1
##        n = height - 1
        #tl
##        while n >= 0:
##            m = width - 1
##            while m >= 0:
##                neighbors = ["n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a"]
##                grid_neighbors = [[n-1, m-1], [n-1, m], [n-1, m+1],
##                                  [n, m-1], [n, m], [n, m+1],
##                                  [n+1, m-1], [n+1, m], [n+1, m+1]]
##                share = 0
##                grid_read = [5, 7, 8]
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(grid_neighbors[q][0] > 0) and (grid_neighbors[q][0] < height) and (grid_neighbors[q][1] > 0) and (grid_neighbors[q][1] < width):
##                        if(genmap_copy[n][m] > genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]):
##                            neighbors[q] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]
##                            share = share + 1
##                    p = p + 1
##                mindisp = 999999
##                tdisp = 0
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        if(disp < mindisp):
##                            mindisp = disp
##                            tdisp = tdisp + disp 
##                    p = p + 1
##                genmap_copy[n][m] = genmap_copy[n][m] - mindisp * (1 - 1 / (share + 1))
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] + disp / tdisp * (mindisp * (1 - 1 / (share + 1)))
##                    p = p + 1
##                m = m - 1
##            n = n - 1
##        #tr
##        n = height - 1
##        while n >= 0:
##            m = 0
##            while m < width:
##                neighbors = ["n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a"]
##                grid_neighbors = [[n-1, m-1], [n-1, m], [n-1, m+1],
##                                  [n, m-1], [n, m], [n, m+1],
##                                  [n+1, m-1], [n+1, m], [n+1, m+1]]
##                share = 0
##                grid_read = [3, 6, 7]
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(grid_neighbors[q][0] > 0) and (grid_neighbors[q][0] < height) and (grid_neighbors[q][1] > 0) and (grid_neighbors[q][1] < width):
##                        if(genmap_copy[n][m] > genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]):
##                            neighbors[q] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]
##                            share = share + 1
##                    p = p + 1
##                mindisp = 999999
##                tdisp = 0
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        if(disp < mindisp):
##                            mindisp = disp
##                            tdisp = tdisp + disp 
##                    p = p + 1
##                genmap_copy[n][m] = genmap_copy[n][m] - mindisp * (1 - 1 / (share + 1))
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] + disp / tdisp * (mindisp * (1 - 1 / (share + 1)))
##                    p = p + 1
##                m = m + 1
##            n = n - 1
##        #bl
##        n = 0
##        while n < height:
##            m = width - 1
##            while m >= 0:
##                neighbors = ["n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a",
##                             "n/a", "n/a", "n/a"]
##                grid_neighbors = [[n-1, m-1], [n-1, m], [n-1, m+1],
##                                  [n, m-1], [n, m], [n, m+1],
##                                  [n+1, m-1], [n+1, m], [n+1, m+1]]
##                share = 0
##                grid_read = [1, 2, 5]
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(grid_neighbors[q][0] > 0) and (grid_neighbors[q][0] < height) and (grid_neighbors[q][1] > 0) and (grid_neighbors[q][1] < width):
##                        if(genmap_copy[n][m] > genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]):
##                            neighbors[q] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]]
##                            share = share + 1
##                    p = p + 1
##                mindisp = 999999
##                tdisp = 0
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        if(disp < mindisp):
##                            mindisp = disp
##                            tdisp = tdisp + disp 
##                    p = p + 1
##                genmap_copy[n][m] = genmap_copy[n][m] - mindisp * (1 - 1 / (share + 1))
##                p = 0
##                while p < len(grid_read):
##                    q = grid_read[p]
##                    if(neighbors[q] != "n/a"):
##                        disp = genmap_copy[n][m] - neighbors[q]
##                        genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] = genmap_copy[grid_neighbors[q][0]][grid_neighbors[q][1]] + disp / tdisp * (mindisp * (1 - 1 / (share + 1)))
##                    p = p + 1
##                m = m - 1
##            n = n + 1
        its = its + 1
        
    print("atrophy complete")
    return genmap_copy

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
        rad = min(max(3, int((map_properties["mapsizex"]+map_properties["mapsizey"])/2)), 6)
        rnd = random.randint(-60, 60)
        tri1 = [int(start_positions[n][0] * xcoord + rad * math.cos((math.pi / 180) * rnd)), int(start_positions[n][1] * ycoord + rad * math.sin((math.pi / 180) * rnd))]
        tri2 = [int(start_positions[n][0] * xcoord + rad * math.cos((2 * math.pi / 3) + (math.pi / 180) * rnd)), int(start_positions[n][1] * ycoord + rad * math.sin((2 * math.pi / 3) + (math.pi / 180) * rnd))]
        tri3 = [int(start_positions[n][0] * xcoord + rad * math.cos((4 * math.pi / 3) + (math.pi / 180) * rnd)), int(start_positions[n][1] * ycoord + rad * math.sin((4 * math.pi / 3) + (math.pi / 180) * rnd))]
        metalpoints.append(tri1)
        metalpoints.append(tri2)
        metalpoints.append(tri3)
        n = n + 1
    #other points of interest...
    #currently just even spread + noise, later we can analyze the condensemap to do something more clever
    #mexcount = max(int(((map_properties["mapsizex"] * map_properties["mapsizey"]) - map_properties["numplayers"] * 3) / 3.5), 2)
    mexcount = map_properties["numplayers"] * 4 * (map_properties["mapsizex"] + map_properties["mapsizey"]) // 24
    basemexcount = mexcount + map_properties["numplayers"] * random.randint(3, 6)
    mexcount = int(mexcount / 2)
    if(fliptype == 4) or (fliptype == 5):
        mexcount = mexcount // 2
    print("\tmexcount: " + str(basemexcount))

    def distfrom (xo, yo, xt, yt):
        distsq = pow(pow((xt - xo), 2) + pow((yt - yo), 2), 0.5)
        return distsq

    mexchk = 4 #checks this many pixels left/right of the mex possiblepoint
    mexdst = 24 #* (map_properties["mapsizex"] + map_properties["mapsizey"]) // 24
    mexthresh = 0.32 #slope across mexchk up/down needs to be less than this

    if(map_properties["generation_type"] == "provided"):
        mexcount = basemexcount
        n = 0
        while n < mexcount:
            #lbound = min(int(4 * xcoord / (2 * map_properties["mapsizex"])), int(4 * xcoord / 16))
            lbound = mexchk
            rbound = xcoord - mexchk
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
    elif(fliptype == 0):
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
    elif(fliptype == 2):
        #top left, bottom right
        n = 0
        while n < mexcount:
            ubound = mexchk
            bbound = int(ycoord / 2) - mexdst // 2
            lbound = mexchk
            rbound = int(xcoord - mexdst / pow(2, 0.5))

            xvar = random.randint(lbound, rbound)
            ymax = max(int(ycoord - ycoord/xcoord * xvar - mexdst * 4 / pow(2, 0.5)), ubound + 1)
            
            possiblepoint = [xvar, random.randint(ubound, ymax)]
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
                    xvar = random.randint(lbound, rbound)
                    ymax = max(int(ycoord - ycoord/xcoord * xvar - mexdst * 4 / pow(2, 0.5)), ubound + 1)
            
                    possiblepoint = [xvar, random.randint(ubound, ymax)]
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
    elif(fliptype == 3):
        #bottom left, top right
        n = 0
        while n < mexcount:
            ubound = mexchk
            bbound = int(ycoord - mexdst / pow(2, 0.5))
            lbound = mexchk
            rbound = int(xcoord - mexdst / pow(2, 0.5))

            xvar = random.randint(lbound, rbound)
            ymax = min(int(ycoord/xcoord * xvar + mexdst * 4 / pow(2, 0.5)), bbound) - 1
            
            possiblepoint = [xvar, random.randint(ymax, bbound)]
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
                    xvar = random.randint(lbound, rbound)
                    ymax = min(int(ycoord/xcoord * xvar + mexdst * 4 / pow(2, 0.5)), bbound) - 1
            
                    possiblepoint = [xvar, random.randint(ymax, bbound)]
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
    elif(fliptype == 4):
        #quad
        n = 0
        while n < mexcount:
            #lbound = min(int(4 * xcoord / (2 * map_properties["mapsizex"])), int(4 * xcoord / 16))
            lbound = mexchk
            rbound = int(xcoord / 2) - mexdst // 2
            ubound = mexchk
            bbound = int(ycoord / 2) - mexdst // 2
            
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
    elif(fliptype == 5):
        #cross
        n = 0
        while n < mexcount:
            ubound = int(mexdst / pow(2, 0.5))
            bbound = int(ycoord - mexdst / pow(2, 0.5))
            lbound = int(mexdst / pow(2, 0.5))
            rbound = int(xcoord - mexdst / pow(2, 0.5))

            yvar = random.randint(ubound, bbound)
            xmax = max(int(-1 * (xcoord/ycoord) * abs(yvar - ycoord / 2) + xcoord / 2 - mexdst), lbound) + 1
            
            possiblepoint = [random.randint(lbound, xmax), yvar]
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
                    yvar = random.randint(ubound, bbound)
                    xmax = max(int(-1 * (xcoord/ycoord) * abs(yvar - ycoord / 2) + xcoord / 2 - mexdst), lbound) + 1
            
                    possiblepoint = [random.randint(lbound, xmax), yvar]
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
        
    #make a regular array...
    #This does not work, and nothing I've seen up to this point
    #makes sense as to why.
    reg = []
    n = 0
    while n < ycoord:
        m = 0
        row = []
        while m < xcoord:
            row.append(0)
            m = m + 1
        reg.append(row)
        n = n + 1

    n = 0
    while n < len(metalpix):
        #print("metal at: " + str(metalpix[n][0]) + ", " + str(metalpix[n][1]))
        reg[metalpix[n][1]][metalpix[n][0]] = 1
        n = n + 1

    #so, we mirror the pixels *manually*
    mirrorpix = []
    if(map_properties["generation_type"] != "provided"):
        mirrorpix = mirror_array(reg, fliptype)
    else:
        mirrorpix = copy.deepcopy(reg)
        
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
        if(fliptype == 4) or (fliptype == 5) or (fliptype == 2) or (fliptype == 3):
            dst = pow(pow((xp - xc),2) + pow((yp-yc), 2), 0.5)
            mxdst = pow(pow(xc,2) + pow(yc, 2), 0.5)
            p = min(max(-1 * abs(dst) / mxdst + 1.25, 0.5), 1)
            retval = 255 * p

        return int(retval)

    #make as rgb array...
    pixelarray = []
    n = 0
    while n < ycoord:
        m = 0
        row = []
        while m < xcoord:
            redvalue = 0
            if(mirrorpix[n][m] == 1):
                redvalue = 255
                if(metaltype == 1):
                    redvalue = GetMetal( m, n, xcoord // 2, ycoord // 2, fliptype)
            row.append((redvalue, 0, 0))
            m = m + 1
        pixelarray.append(row)
        n = n + 1
    
    return pixelarray

def generate_texmap ( genmap, texture_family, metmap, mult, minh, pris_tht ):
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
    #decide between complementary options and single colors.
    color_types = random.randint(0, 1)
    if(pris_tht != -1):
        if(color_types == 0):
            print("... prismatic: single color")
        if(color_types == 1):
            print("... prismatic: complementary colors")
    n = 0
    while n < len(ti_byrow):
        commasep = ti_byrow[n].split(',')
        if(len(commasep) == 3):
            texturepack.append(commasep[0])
            pris_temp = pris_tht
            if(pris_tht != -1):
                pris_temp = pris_temp + random.uniform(math.pi / -12, math.pi / 12)
                if(color_types == 1):
                    pris_temp = pris_temp + random.randint(0, 1) * math.pi
            infopack.append([int(commasep[1]), int(commasep[2]), pris_temp])
            print(str(commasep[0]) + ": " + str(commasep[1]) + ", " + str(commasep[2]) + ", " + str(pris_temp))
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
                tup = ts[m * w + l]
                if(pris_tht != -1):
                    gry = (ts[m * w + l][0] + ts[m * w + l][0] + ts[m * w + l][0]) // 3
                    tup = (gry, gry, gry)
                row.append(tup)
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

        mrg = 0.8
        base = 200
        extend = 255 - base

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

            if(pris_tht != -1):
                lr = tex[key][y%lh][x%lw][0] * mrg + (base + extend * math.cos(ip[key][2])) * (1 - mrg)
                lg = tex[key][y%lh][x%lw][1] * mrg + (base + extend * math.cos(ip[key][2] + math.pi * 2 / 3)) * (1 - mrg)
                lb = tex[key][y%lh][x%lw][2] * mrg + (base + extend * math.cos(ip[key][2] + math.pi * 4 / 3)) * (1 - mrg)

            rw = ip[key+1][0]
            rh = ip[key+1][1]
            rr = tex[key+1][y%rh][x%rw][0]
            rg = tex[key+1][y%rh][x%rw][1]
            rb = tex[key+1][y%rh][x%rw][2]

            if(pris_tht != -1):
                rr = tex[key+1][y%rh][x%rw][0] * mrg + (base + extend * math.cos(ip[key+1][2])) * (1 - mrg)
                rg = tex[key+1][y%rh][x%rw][1] * mrg + (base + extend * math.cos(ip[key+1][2] + math.pi * 2 / 3)) * (1 - mrg)
                rb = tex[key+1][y%rh][x%rw][2] * mrg + (base + extend * math.cos(ip[key+1][2] + math.pi * 4 / 3)) * (1 - mrg)

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
            
            if(pris_tht != -1):
                r = (tex[0][y%lh][x%lw][0] * 0.5 + hmod * 0.5) * mrg + (base + extend * math.cos(ip[0][2])) * (1 - mrg)
                g = (tex[0][y%lh][x%lw][1] * 0.5 + hmod * 0.5) * mrg + (base + extend * math.cos(ip[0][2] + math.pi * 2 / 3)) * (1 - mrg)
                b = (tex[0][y%lh][x%lw][2] * 0.5 + hmod * 0.5) * mrg + (base + extend * math.cos(ip[0][2] + math.pi * 4 / 3)) * (1 - mrg)
        else:
            #No found texture? (somehow something went very wrong) - just output expanded_heightmap
            hmod = 25 + height * 2
            
            r = hmod
            g = hmod
            b = hmod
            if(pris_tht != -1):
                r = hmod * mrg + (base + extend * math.cos(pris_tht)) * (1 - mrg)
                g = hmod * mrg + (base + extend * math.cos(pris_tht + math.pi * 2 / 3)) * (1 - mrg)
                b = hmod * mrg + (base + extend * math.cos(pris_tht + math.pi * 4 / 3)) * (1 - mrg)
        return (int(r), int(g), int(b))

    def gradient_merge(m, n, gradient, curpixel):
        r = curpixel[0]
        g = curpixel[1]
        b = curpixel[2]

        gradmag = pow(pow(gradient[n][m][0],2) + pow(gradient[n][m][1], 2),0.5)
        p = min(gradmag / 16, 1)
        q = 1-p
        nr = r * q
        ng = g * q
        nb = b * q

        return (int(nr), int(ng), int(nb))

    def get_patch():
        patch = []
        metaldir = "textures/common/metal_patches/"
        metalinfofile = "metal_patches_info.txt"

        metalinfofileobj = open(metaldir + metalinfofile, 'r')
        metaltext = metalinfofileobj.read()
        metalinfofileobj.close()

        possible_patches = metaltext.split("\n")

        metalfilename = random.choice(possible_patches)
        
        ts = []
        with Image.open(metaldir + metalfilename) as tex:
            ts = list(tex.getdata())
            tex.close()
        hi = 0
        while hi < 32:
            wi = 0
            row = []
            while wi < 32:
                index = hi * 32 + wi
                row.append(ts[index])
                wi = wi + 1
            patch.append(row)
            hi = hi + 1

        return patch

    metimg = get_patch()

    metcoords = []

    n = 0
    while (n < len(metmap)):
        m = 0
        while (m < len(metmap[0])):
            up = 0
            if(n > 0):
                up = metmap[n-1][m][0]
            left = 0
            if(m > 0):
                left = metmap[n][m-1][0]
            if(metmap[n][m][0] != 0) and (up == 0) and (left == 0):
                metcoords.append([m * 16, n * 16])
            m = m + 1
        n = n + 1

    print("texture blend start")
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
    print("texture blend finished")
    print("placing metal textures")
    #place metal patches
    r = 0
    while (r < len(metcoords)):
        n = 0
        while n < 32:
            m = 0
            while m < 32:
                xs = metcoords[r][0] + m
                ys = metcoords[r][1] + n

                pixch = texmap[ys][xs]

                ro = pixch[0] * (255 - metimg[n % 32][m % 32][3]) / 255 + metimg[n % 32][m % 32][0] * metimg[n % 32][m % 32][3] / 255
                go = pixch[1] * (255 - metimg[n % 32][m % 32][3]) / 255 + metimg[n % 32][m % 32][1] * metimg[n % 32][m % 32][3] / 255
                bo = pixch[2] * (255 - metimg[n % 32][m % 32][3]) / 255 + metimg[n % 32][m % 32][2] * metimg[n % 32][m % 32][3] / 255
                texmap[ys][xs] = (int(ro), int(go), int(bo))
                m = m + 1
            n = n + 1
        r = r + 1
    print("metal textures finished")
   
    return texmap

def generate_startpositions ( fliptype, map_properties ):
    #I'm going to output floats here. Then from whatever function needs the startpositions
    #it'll multiply width * [0] and height by [1]
    start_positions = []
    np = map_properties["numplayers"]
    hmw = map_properties["mapsizex"] * 64 + 1
    hmh = map_properties["mapsizey"] * 64 + 1
    backline = np
    frontline = 0
    if(np > 4):
        backline = (map_properties["numplayers"] * 2) // 5
        frontline = np - backline
        
    if(fliptype == 0):
        #horizontal
        xset = random.uniform(2/32, 4/32)
        yset = random.uniform(2/32, 30/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < backline):
            xset = random.uniform(2/32, 4/32)
            yset = random.uniform(2/32, 30/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(2/32, 4/32)
                    yset = random.uniform(2/32, 30/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
        n = 0
        while n < frontline:
            xset = random.uniform(3/32, 5/32)
            yset = random.uniform(2/32, 30/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(3/32, 5/32)
                    yset = random.uniform(2/32, 30/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    if(fliptype == 1):
        #vertical
        xset = random.uniform(2/32, 30/32)
        yset = random.uniform(2/32, 4/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < backline):
            xset = random.uniform(2/32, 30/32)
            yset = random.uniform(2/32, 4/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(2/32, 30/32)
                    yset = random.uniform(2/32, 4/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
        n = 0
        while n < frontline:
            xset = random.uniform(2/32, 30/32)
            yset = random.uniform(3/32, 5/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(2/32, 30/32)
                    yset = random.uniform(3/32, 5/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    if(fliptype == 2):
        #top left, bottom right
        xset = random.uniform(1/32, 8/32)
        yset = random.uniform(1/32, 8/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < np):
            xset = random.uniform(1/32, 8/32)
            yset = random.uniform(1/32, 8/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(1/32, 8/32)
                    yset = random.uniform(1/32, 8/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    if(fliptype == 3):
        #bottom left, top right
        xset = random.uniform(1/32, 8/32)
        yset = random.uniform(24/32, 31/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < np):
            xset = random.uniform(1/32, 8/32)
            yset = random.uniform(24/32, 31/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(1/32, 8/32)
                    yset = random.uniform(24/32, 31/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    if(fliptype == 4):
        #quad
        np = np // 2
        xset = random.uniform(1/32, 8/32)
        yset = random.uniform(1/32, 8/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < np):
            xset = random.uniform(1/32, 8/32)
            yset = random.uniform(1/32, 8/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(1/32, 8/32)
                    yset = random.uniform(1/32, 8/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    if(fliptype == 5):
        #cross
        np = np // 2
        xset = random.uniform(1/32, 8/32)
        yset = random.uniform(12/32, 20/32)
        start_positions.append([xset, yset])
        n = 1
        while(n < np):
            xset = random.uniform(1/32, 8/32)
            yset = random.uniform(12/32, 20/32)
            m = 0
            while m < len(start_positions):
                dist = pow(pow((xset - start_positions[m][0]) * hmw, 2) + pow((yset - start_positions[m][1]) * hmh, 2), 0.5)
                if(dist < 48):  #2x mex radius
                    xset = random.uniform(1/32, 8/32)
                    yset = random.uniform(12/32, 20/32)
                    m = 0
                else:
                    m = m + 1
            start_positions.append([xset, yset])
            n = n + 1
    return start_positions

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
    fliptype = random.randint(0, 5)
    if(map_properties["fliptype"] != -1):
        fliptype = int(map_properties["fliptype"])
        if(fliptype < 0):
            fliptype = 0
        if(fliptype > 5):
            fliptype = 5

    ft_index = ["Horizontal", "Vertical", "TLBR", "BLTR", "Corners", "Crosses"]
    generation_types = ["prefab", "voronoi", "paths", "grid", "provided", "perlin"]
    if map_properties["generation_type"] not in generation_types:
        map_properties["generation_type"] = random.choice(generation_types)

    #locking down fliptypes for oblong maps. Optional, but I'm just being safe atm.
    if(map_properties["mapsizex"] > map_properties["mapsizey"]):
        fliptype = 0
    if(map_properties["mapsizey"] > map_properties["mapsizex"]):
        fliptype = 1

    mapname = 'srmg_' + map_properties["generation_type"] + "_" + str(fliptype) + "_" + str(map_properties["seed"])
    dirname = 'maps/' + mapname + '/'

    os.makedirs(dirname, exist_ok=True)
    os.makedirs(dirname+'maps/', exist_ok=True)
    
    print("Map: " + mapname)
    print("\tTextures Used: " + str(texture_picked))
    print("\tFliptype: " + ft_index[fliptype] + ", " + str(fliptype))

    #generate startpositions
    start_positions = generate_startpositions(fliptype, map_properties)

    #generate map
    genmap = []
    if(map_properties["generation_type"] == "prefab"):
        print("Using Prefabs.")
        os.chdir(curdir + '/prefab_generation')
        #genmap, fliptype = prefab_generation.prefab_generation.generate_map_using_prefabs(map_properties)
        genmap = prefab_generation.prefab_generation.generate_map_using_prefabs(map_properties, start_positions, fliptype)
        genmap = mirror_array(genmap, fliptype)
        genmap = blurmap(genmap, 3, 20, fliptype)
        os.chdir(curdir)
        #keep in mind:
        # - seam blur is: 20
        # - general blur is: 3
    elif(map_properties["generation_type"] == "voronoi"):
        print("Using Voronoi.")
        os.chdir(curdir + '/voronoi_generation')
        #genmap, fliptype = voronoi_generation.voronoi_generation.generate_map_using_voronoi(map_properties)
        genmap = voronoi_generation.voronoi_generation.generate_map_using_voronoi(map_properties, start_positions, fliptype)
        genmap = mirror_array(genmap, fliptype)
        genmap = blurmap(genmap, 3, 0, fliptype)
        os.chdir(curdir)
        #keep in mind:
        # - seam blur is: 0
        # - general blur is: 3
    elif(map_properties["generation_type"] == "paths"):
        print("Using Paths.")
        os.chdir(curdir + '/path_generation')
        #genmap, fliptype = path_generation.path_generation.generate_map_using_paths(map_properties)
        genmap = path_generation.path_generation.generate_map_using_paths(map_properties, start_positions, fliptype)
        genmap = mirror_array(genmap, fliptype)
        genmap = blurmap(genmap, 3, 5, fliptype)
        os.chdir(curdir)
        #keep in mind:
        # - seam blur is: 0
        # - general blur is: 3
    elif(map_properties["generation_type"] == "grid"):
        print("Using Grid.")
        os.chdir(curdir + '/path_generation')
        genmap = grid_generation.grid_generation.generate_map_using_grid(map_properties, start_positions, fliptype)
        genmap = mirror_array(genmap, fliptype)
        #genmap = atrophymap(genmap, 30) #currently not resulting in what I want, we'll work on it.
        genmap = blurmap(genmap, 3, 0, fliptype)
        os.chdir(curdir)
    elif(map_properties["generation_type"] == "provided"):
        print("Using Provided.")
        os.chdir(curdir + '/provided_generation')
        genmap = provided_generation.provided_generation.generate_map_using_provided(map_properties)
        start_positions.clear()
        os.chdir(curdir)
    elif(map_properties["generation_type"] == "perlin"):
        print("Using Perlin.")
        os.chdir(curdir + '/perlin_generation')
        genmap = perlin_generation.perlin_generation.generate_map_using_perlin(map_properties, start_positions, fliptype)
        genmap = mirror_array(genmap, fliptype)
        genmap = blurmap(genmap, 3, 0, fliptype)
        os.chdir(curdir)
    
    #normalize height
    mult, minh = normalize_height(genmap)

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
            metmap_img_pixels[m, n] = metmap[n][m]
            m = m + 1
        n = n + 1
    metmap_img.save(dirname + mapname + '_metal.bmp')

    metmap_filename = dirname + mapname + '_metal.bmp'
    #TextureMap
    pris_tht = random.uniform(0, math.pi * 2)
    if(map_properties["prismatic"] != True):
        pris_tht = -1

    print("\tpris_tht: " + str(pris_tht))

    texmap = []
    if(map_properties["texturing_method"] == "complex"):
        texmap = complicated_texturing.complicated_texturing.generate_texmap_complicated(genmap, texture_picked, metmap, mult, minh, pris_tht)
    else:
        texmap = generate_texmap(genmap, texture_picked, metmap, mult, minh, pris_tht)

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

    #mapinfo_vars["[MAXHEIGHT]"] = int(int(mapinfo_vars["[MAXHEIGHT]"]) + minh) / mult
    #mapinfo_vars["[MINHEIGHT]"] = int(int(mapinfo_vars["[MINHEIGHT]"]) + minh) / mult
    #print("Updated [MAXHEIGHT] to: " + str(mapinfo_vars["[MAXHEIGHT]"]))
    #print("Updated [MINHEIGHT] to: " + str(mapinfo_vars["[MINHEIGHT]"]))

    if(map_properties["prismatic"] == True):
        base = 200
        extend = 255 - base
        pris_r = (base + extend * math.cos(pris_tht)) / 255
        pris_g = (base + extend * math.cos(pris_tht + math.pi * 2 / 3)) / 255
        pris_b = (base + extend * math.cos(pris_tht + math.pi * 4 / 3)) / 255
        mapinfo_vars["[FOGR]"] = 0.8 * pris_r
        mapinfo_vars["[FOGG]"] = 0.8 * pris_g
        mapinfo_vars["[FOGB]"] = 0.8 * pris_b
        mapinfo_vars["[SKYR]"] = 0.8 * pris_r
        mapinfo_vars["[SKYG]"] = 0.8 * pris_g
        mapinfo_vars["[SKYB]"] = 0.8 * pris_b
        mapinfo_vars["[WATR]"] = 0.67 * pris_r
        mapinfo_vars["[WATG]"] = 0.8 * pris_g
        mapinfo_vars["[WATB]"] = 1.0 * pris_b

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
    if(fliptype == 3):    # Bottom left/top right
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
        "seed": 9097,
        "numplayers": 8,
        "generation_type": "perlin",     #prefab, voronoi, paths, grid, provided, perlin
        "prismatic": True,               #reduces textures to b&w, then recolors at random
        "provided_filename": "provided_input.bmp",   #located in /provided_generation/
        "fliptype": -1,                  #sets the fliptype manually if not -1.
        "texturing_method": "complex"   #options are simple, complex.
        }
    main(map_properties)
    
    print("finished")
