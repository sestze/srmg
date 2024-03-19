#perlin_generation.py
#author: Sestze
#
#generates a heightmap from a randomized perlin noise result.

import random
import struct
import zlib
import math
import os

import copy

from PIL import Image

def perlin_interpolate(a, b, var):
    p = var
    #ret = (b - a) * p + a
    #smoothstep
    #ret = (b - a) * (3 - p * 2) * p * p + a
    #smootherstep
    ret = (b - a) * ((p * (p * 6.0 - 15) + 10) * p * p * p) + a

    return ret

def perlin_edge(n, w, div):
    edge = min((n / w) * div, div - 1)
    #print(str(edge) + ", " + str(n) + ", " + str(div))

    return int(edge)

def blot_position(x, y, flatrad, maxrad, inmap, hght):
    adjmap = copy.deepcopy(inmap)

    n = int(max(0, y - (flatrad + maxrad)))
    while n < int(min(len(inmap) - 1, y + (flatrad + maxrad))):
        m = int(max(0, x - (flatrad + maxrad)))
        while m < int(min(len(inmap) - 1, x + (flatrad + maxrad))):
            dst = pow(pow(x - m, 2) + pow(y - n, 2), 0.5)
            if(dst < flatrad):
                adjmap[n][m] = hght
            elif(dst < maxrad):
                p = (dst - flatrad) / (maxrad - flatrad)
                adjmap[n][m] = hght * (1 - p) + inmap[n][m] * p
            m = m + 1
        n = n + 1

    return adjmap

def generate_map_using_perlin (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []
    
    subdivs = random.randint(1, 2) * 2

    grid_x = map_properties["mapsizex"] / subdivs + 1
    grid_y = map_properties["mapsizey"] / subdivs + 1

    perlin_grads = []
    n = 0
    while n <= grid_y:
        m = 0
        row = []
        while m <= grid_x:
            tht = random.uniform(0, math.pi * 2)
            r = 1
            xv = r * math.cos(tht)
            yv = r * math.sin(tht)
            row.append([xv, yv])
            m = m + 1
        perlin_grads.append(row)
        n = n + 1

    #adjust perlin based on fliptype

    if(fliptype == 0) or (fliptype == 4):
        tht = 0
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        n = 0
        while (n < len(perlin_grads)):
            m = perlin_edge(width / 2, width, grid_x)
            #perlin_grads[n][m-1] = [xv, yv]
            perlin_grads[n][m] = [xv, yv]
            #perlin_grads[n][m+1] = [xv, yv]
            n = n + 1
    if(fliptype == 1) or (fliptype == 4):
        tht = math.pi / 2
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        n = 0
        while (n < len(perlin_grads[0])):
            m = perlin_edge(height / 2, height, grid_y)
            #perlin_grads[m-1][n] = [xv, yv]
            perlin_grads[m][n] = [xv, yv]
            #perlin_grads[m+1][n] = [xv, yv]
            n = n + 1
    if(fliptype == 2) or (fliptype == 5):
        tht = math.pi / -4
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        n = 0
        while (n < len(perlin_grads[0])):
            perlin_grads[n][len(perlin_grads[0]) - 1 - n] = [xv, yv]
            if(n+1 < len(perlin_grads)) and (len(perlin_grads[0]) - 1 - n + 1 < len(perlin_grads)):
                perlin_grads[n+1][len(perlin_grads[0]) - 1 - n + 1] = [xv, yv]
            if(n-1 > 0) and (len(perlin_grads[0]) - 1 - n - 1 > 0):
                perlin_grads[n-1][len(perlin_grads[0]) - 1 - n - 1] = [xv, yv]
            n = n + 1

    if(fliptype == 3) or (fliptype == 5):
        tht = math.pi / 4
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        n = 0
        while (n < len(perlin_grads[0])):
            perlin_grads[n][n] = [xv, yv]
            if(n+1 < len(perlin_grads)) and (n+1 < len(perlin_grads[0])):
                perlin_grads[n+1][n+1] = [xv, yv]
            if(n-1 >= 0):
                perlin_grads[n-1][n-1] = [xv, yv]
            n = n + 1

    n = 0
    while n < height:
        m = 0
        row = []
        while m < width:
            kx = perlin_edge(m, width, grid_x)
            ky = perlin_edge(n, height, grid_y)

            dx = width / grid_x
            dy = height / grid_y
            
            n0 = perlin_grads[ky][kx]
            n1 = perlin_grads[ky][kx+1]
            n2 = perlin_grads[ky+1][kx]
            n3 = perlin_grads[ky+1][kx+1]

            n0d = (n0[0]*(m - kx * dx) / dx + n0[1] * (n - ky * dy) / dy)
            n1d = (n1[0]*(m - (kx+1) * dx) / dx + n1[1] * (n - ky * dy) / dy)
            n2d = (n2[0]*(m - kx * dx) / dx + n2[1] * (n - (ky+1) * dy) / dy)
            n3d = (n3[0]*(m - (kx+1) * dx) / dx + n3[1] * (n - (ky+1) * dy) / dy)

            ix1 = perlin_interpolate(n0d, n1d, (m - kx * dx) / dx)
            ix2 = perlin_interpolate(n2d, n3d, (m - kx * dx) / dx)
            it = perlin_interpolate(ix1, ix2, (n - ky * dy) / dy)

            adjust = (it * 0.5 + 0.5) * 100
            if(adjust > 100):
                print(str(adjust))
            row.append(adjust)
            m = m + 1
        genmap.append(row)
        n = n + 1

    print("normalizing start position heights")

    spawnflat = 24
    spawnmax = 64

    s = 0
    while s < len(start_positions):
        hght = random.randint(4, 6) * 10
        genmap = blot_position(start_positions[s][0] * width, start_positions[s][1] * height, spawnflat, spawnmax, genmap, hght)
        s = s + 1

    print("managing seam")

    seam = 0
    seam_blur = 96

    if(seam + seam_blur > 0):
        gmc = copy.deepcopy(genmap)
        if(fliptype == 0) or (fliptype == 4):
            #horiz
            n = 0
            while(n < height):
                genmap = blot_position(width // 2, n, seam, seam_blur, genmap, gmc[n][width // 2])
                n = n + seam + seam_blur
        if(fliptype == 1) or (fliptype == 4):
            #vert
            n = 0
            while(n < width):
                genmap = blot_position(n, height // 2, seam, seam_blur, genmap, gmc[height // 2][n])
                n = n + seam + seam_blur
        if(fliptype == 2) or (fliptype == 5):
            #tlbr
            n = 0
            while(n < width):
                genmap = blot_position(n, height - n - 1, seam, seam_blur, genmap, gmc[height - n - 1][n])
                n = n + seam + seam_blur
        if(fliptype == 3) or (fliptype == 5):
            #bltr
            n = 0
            while(n < width):
                genmap = blot_position(n, n, seam, seam_blur, genmap, gmc[n][n])
                n = n + seam + seam_blur

    print("perlin generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("Too many inputs, really. Need to run srmg_1.py")
    print("finished")
