#prefab_generation.py
#author: Sestze
#
#Different generation method to the ovals. Instead, copy/pasting prefab elements into a heightmap with/without rotation.
#Resources needed:
#   - I'll need some simple heightmap files.
#       - I think we separate them into specific families.
#       - We'll need the same index file strategy too. God help me.

#How does this work, step by step?
#   - Create a heightmap of pixels to start with
#       - We'll use a gradient based on a cubic spline between two heights depending on fliptype.
#       - v/h: flat up to 1/8 of map, spline across 1/4, flat for 1/8 of map.
#       - quad: flat up to radius 1/8, spline across 1/4, flat for remainder.
#   - Randomly determine fliptype (0, 1, 2, again)
#   - Load heightmap fodder into a list to be chosen from.
#       - tile info in the same list, as well.
#   - Use determined start positions (steal from srmg_1) to determine dead zones
#       - or in the case of certain greebles (like start position wrappers (?) live zones
#   - randomly select fodder, place at random on the map
#       - only additive, we can normalize heights afterwards (maybe adjust maxheight based on that normalization?)
#   - once fodder is placed, we mirror the pixels accordingly.
#   - ship back the generated map and fliptype.

#Issues:
#   - I lack good prefabs. I'd like more of them
#   - Maybe some form of intelligent prefabs? maybe?
#       - maybe if you have a string like start_ in your prefab it'll coopt it for startpoints
#       - obstacle_ could specifically be placed in such a way to avoid startpoints
#   - I don't have fliptypes for 2, 3, and I need to move fliptypes for 2 to 4 and 5.

import random
import struct
import zlib
import math
import os

import copy

from PIL import Image

def get_prefab_families ():
    retval = []
    familydir = "prefabs/"

    scanned = os.scandir(familydir)
    for objs in scanned:
        if objs.is_dir():
            retval.append(objs.name)
    return retval

def get_prefab_infofile (family):
    familydir = "prefabs/" + family + "/"

    file = ""
    retval = ""

    scanned = os.scandir(familydir)
    for objs in scanned:
        if(objs.is_file()):
            filename = objs.name
            if(filename.find('fablist.txt') != -1):
                file = objs.name

    if(file != ""):
        filevalue = open(familydir + file, 'r')
        retval = filevalue.read()
        filevalue.close()
        
    return retval

def get_texlist_from_infofile ( info ):
    texlist = []

    split = info.split('\n')

    for lines in split:
        split_2 = lines.split(',')
        if(len(split_2) == 3):
            obj = [split_2[0], int(split_2[1]), int(split_2[2])]
            texlist.append(obj)
    return texlist

def get_prefab_object ( family, info, scalar, severity, width, height ):
    prefab = []
    pixeldata = []
    
    texlist = get_texlist_from_infofile ( info )

    prefab_choice = random.choice(texlist)

    prefab_filename = "prefabs/" + family + "/" + prefab_choice[0]
    w = int(prefab_choice[1])
    h = int(prefab_choice[2])

    w = int(min(w * scalar, width * 0.25))
    h = int(min(h * scalar, height * 0.25))

    with Image.open(prefab_filename) as image:
        #resize the prefab
        resized = image.resize((w, h))
        #rotate the prefab - unused... for the moment.
        rotated = resized.rotate(random.randint(0, 3) * 90)
        pixeldata = list(rotated.getdata())

    n = 0
    while n < h:
        row = []
        m = 0
        while m < w:
            pixpos = n * w + m
            pixel = (pixeldata[pixpos][0] + pixeldata[pixpos][1] + pixeldata[pixpos][2]) / 3
            pixel = pixel * 100 / 256 #normalize to 0-100
            pixel = pixel - 50  #Kludge to allow for heightmaps to be added *or* subtracted.
            pixel = pixel * severity
            row.append(pixel)
            m = m + 1
        prefab.append(row)
        n = n + 1
    
    return prefab

def inbounds( val, l, u ):
    if val < l:
        return False
    if val > u:
        return False
    return True

def place_prefab(genmap, prefab_object, xplace, yplace):
    retmap = genmap.copy()

    n = 0
    while n < len(prefab_object):
        m = 0
        while m < len(prefab_object[n]):
            xpt = xplace + m
            ypt = yplace + n
            if(inbounds(xpt, 0, len(retmap[0]) - 1) and inbounds(ypt, 0, len(retmap) - 1)):
                hv = retmap[ypt][xpt]
                retmap[ypt][xpt] = hv + prefab_object[n][m]
            m = m + 1
        n = n + 1

    return retmap

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

def generate_map_using_prefabs (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = 50
    endheight = 50
    slopechoice = random.randint(0, 1)
    if(slopechoice == 0):
        startheight = random.randint(2, 4) * 10
        endheight = 100 - startheight
    if(slopechoice == 1):
        startheight = random.randint(6, 8) * 10
        endheight = 100 - startheight
    startheight = 50
    endheight = 50

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
    while(n < height):
        row = []
        m = 0
        while(m < width):
            #spline for overall map heights
            threshvariance = 0
            bumpvariance = 0
            threshvar = 0
            htemp = 50
            if(startheight != endheight):
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
                    threshvar = (n + m) / 2
                    if(threshvar < startspline):
                        htemp = startheight
                    elif(threshvar > endspline):
                        htemp = endheight
                    else:
                        htemp = cubic(threshvar, startspline, startheight, endspline, endheight)
                if(fliptype == 3):
                    threshvar = ((height - n) + m) / 2
                    if(threshvar < startspline):
                        htemp = startheight
                    elif(threshvar > endspline):
                        htemp = endheight
                    else:
                        htemp = cubic(threshvar, startspline, startheight, endspline, endheight)
                if(fliptype == 4) or (fliptype == 5):
                    tdst = pow(pow(m, 2) + pow(n, 2), 0.5)
                    threshvar = tdst
                    if(tdst < startspline):
                        htemp = startheight
                    elif(tdst > endspline):
                        htemp = endheight
                    else:
                        htemp = cubic(tdst, startspline, startheight, endspline, endheight)
            row.append(htemp)
            m = m + 1
        genmap.append(row)
        n = n + 1
    #load prefabs
    prefab_families = get_prefab_families()
    chosen_family = random.choice(prefab_families)
    print("\tprefab family: " + chosen_family)
    prefab_info = get_prefab_infofile(chosen_family)
    #add in prefabs
    prefab_number = random.randint(12, 16) * (map_properties["mapsizex"] + map_properties["mapsizey"]) / 24
    if(fliptype == 4) or (fliptype == 5):
        prefab_number = prefab_number // 2
    prefab_overall_scalar_low = random.uniform(0.5,0.9)
    prefab_overall_scalar_high = random.uniform(1.1, 1.5)
    
    print("\tprefab_number: " + str(prefab_number))
    print("\tprefab_overall_scalar_low: " + str(prefab_overall_scalar_low))
    print("\tprefab_overall_scalar_high: " + str(prefab_overall_scalar_high))

    def IsBetween( val, l, u ):
        if(val > l) and (val < u):
            return True
        return False

    DZ = []
    n = 0
    while n < len(start_positions):
        DZ.append([start_positions[n][0] * width, start_positions[n][1] * height, 24])
        n = n + 1

    blockseam = False
    if(blockseam == True):
        seamdz = 1
        seamsplit = 12
        if(fliptype == 0) or (fliptype == 4):
            n = 0
            while n < height:
                xp = width / 2
                yp = n
                DZ.append([xp, yp, seamdz])
                n = n + seamsplit
        if(fliptype == 1) or (fliptype == 4):
            n = 0
            while n < width:
                xp = n
                yp = height / 2
                DZ.append([xp, yp, seamdz])
                n = n + seamsplit
        if(fliptype == 2) or (fliptype == 5):
            n = 0
            while n < width:
                xp = n
                yp = height - n - 1
                DZ.append([xp, yp, seamdz])
                n = n + seamsplit
        if(fliptype == 3) or (fliptype == 5):
            n = 0
            while n < width:
                xp = n
                yp = n
                DZ.append([xp, yp, seamdz])
                n = n + seamsplit
            
    def CheckDeadZone( x, y, pfo_w, pfo_h, deadzones):
        DZ_MUL = 0.5
        n = 0
        while n < len(deadzones):
            pfo_rad = pow(pow(pfo_w / 2, 2) + pow(pfo_h / 2, 2), 0.5) * DZ_MUL
            dz_rad = deadzones[n][2] * DZ_MUL

            dst = pow(pow((x + pfo_w / 2) - deadzones[n][0], 2) + pow((y + pfo_h / 2) - deadzones[n][1], 2), 0.5)
            #print("Deadzone check: " + str(dst) + " vs " + str(pfo_rad) + " + " + str(dz_rad))
            if(dst < (pfo_rad + dz_rad)):
                #print("\n")
                #print("Deadzone fail: " + str(dst) + " vs " + str(pfo_rad) + " + " + str(dz_rad))
                #print("position: " + str(x) + ", " + str(y))
                #print("dz pos: " + str(deadzones[n][0]) + ", " + str(deadzones[n][1]))
                #print("size: " + str(pfo_w) + ", " + str(pfo_h))
                return True
            n = n + 1
        return False

    n = 0
    while n < prefab_number:
        prefab_severity = random.uniform(0.75, 1)
        prefab_object = get_prefab_object(chosen_family, prefab_info, random.uniform(prefab_overall_scalar_low, prefab_overall_scalar_high), prefab_severity, width, height)
        pfo_w = len(prefab_object[0])
        pfo_h = len(prefab_object)
        divx = 1
        divy = 1

        if(fliptype == 0):
            divx = 2
        if(fliptype == 1):
            divy = 2
        if(fliptype == 4):
            divx = 2
            divy = 2

        xupper = int((width / divx) - pfo_w / 2)
        yupper = int((height / divy) - pfo_h / 2)

        xplace = random.randint(-1 * pfo_w // 2, int((width / divx) - pfo_w / 2))
        yplace = random.randint(-1 * pfo_h // 2, int((height / divy) - pfo_h / 2))

        if(fliptype == 2):
            yupper = max(height - xplace - pfo_h // 2, -1 * pfo_h // 2 + 1)
            yplace = random.randint(-1 * pfo_h // 2, yupper)

        if(fliptype == 3):
            xupper = max(yplace - pfo_h // 2, -1 * pfo_w // 2 + 1)
            xplace = random.randint(-1 * pfo_w // 2, xupper)

        if(fliptype == 5):
            xupper = max(-1 * abs(yplace - height // 2) + width // 2 - pfo_w // 2, -1 * pfo_w // 2) + 1
            xplace = random.randint(-1 * pfo_w // 2, xupper)
        r = 25000
        while((CheckDeadZone(xplace, yplace, pfo_w, pfo_h, DZ)) and (r > 0)):
            xplace = random.randint(-1 * pfo_w // 2, int((width / divx) - pfo_w / 2))
            yplace = random.randint(-1 * pfo_h // 2, int((height / divy) - pfo_h / 2))

            if(fliptype == 2):
                yupper = max(height - xplace - pfo_h // 2, -1 * pfo_h // 2 + 1)
                yplace = random.randint(-1 * pfo_h // 2, yupper)

            if(fliptype == 3):
                xupper = max(yplace - pfo_h // 2, -1 * pfo_w // 2 + 1)
                xplace = random.randint(-1 * pfo_w // 2, xupper)

            if(fliptype == 5):
                xupper = max(-1 * abs(yplace - height // 2) + width // 2 - pfo_w // 2, -1 * pfo_w // 2) + 1
                xplace = random.randint(-1 * pfo_w // 2, xupper)
            r = r - 1

        if(r > 0):
            genmap = place_prefab(genmap, prefab_object, xplace, yplace)
            DZ.append([xplace + pfo_w / 2, yplace + pfo_h / 2, pow(pow(pfo_w / 2, 2) + pow(pfo_h / 2,2), 0.5) / 2])
            print("prefab placed at: (" + str(xplace) + ", " + str(yplace) + ")")
        else:
            print("ran out of prefab spots due to space. exiting.")
            n = prefab_number

        n = n + 1
        
    #debug, used to see if prefabs are placed correctly
    #n = 0
    #while n < len(DZ):
    #    genmap = blot_position(DZ[n][0], DZ[n][1], DZ[n][2], 0, genmap, 0)
    #    n = n + 1

    seam = 0
    seam_blur = 0

    gmc = []

    if(seam + seam_blur > 0):
        gmc = copy.deepcopy(genmap)
        if(fliptype == 0) or (fliptype == 4):
            #horiz
            n = 0
            while(n < height):
                genmap = blot_position(width // 2, n, seam, seam_blur, genmap, gmc[n][width // 2])
                n = n + (seam + seam_blur) // 2
        if(fliptype == 1) or (fliptype == 4):
            #vert
            n = 0
            while(n < width):
                genmap = blot_position(n, height // 2, seam, seam_blur, genmap, gmc[height // 2][n])
                n = n + (seam + seam_blur) // 2
        if(fliptype == 2) or (fliptype == 5):
            #tlbr
            n = 0
            while(n < width):
                genmap = blot_position(n, height - n - 1, seam, seam_blur, genmap, gmc[height - n - 1][n])
                n = n + (seam + seam_blur) // 2
        if(fliptype == 3) or (fliptype == 5):
            #bltr
            n = 0
            while(n < width):
                genmap = blot_position(n, n, seam, seam_blur, genmap, gmc[n][n])
                n = n + (seam + seam_blur) // 2

    print("prefab generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("There's too many inputs required for this script, run srmg_1.py")
    #print(str(genmap))
    print("finished")
