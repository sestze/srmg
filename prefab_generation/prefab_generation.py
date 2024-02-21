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

def get_prefab_object ( family, info, scalar, severity ):
    prefab = []
    pixeldata = []
    
    texlist = get_texlist_from_infofile ( info )

    prefab_choice = random.choice(texlist)

    prefab_filename = "prefabs/" + family + "/" + prefab_choice[0]
    w = int(prefab_choice[1] * scalar)
    h = int(prefab_choice[2] * scalar)

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

def generate_map_using_prefabs (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    startheight = 50
    endheight = 50
    slopechoice = random.randint(0, 2)
    if(slopechoice == 1):
        startheight = random.randint(2, 4) * 10
        endheight = 100 - startheight
    if(slopechoice == 2):
        startheight = random.randint(6, 8) * 10
        endheight = 100 - startheight
    
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
            hght = cubic(inval, 1/8 * width, startheight, 3/8 * width, endheight) #defaults to horizontal fliptype
            if(fliptype == 1):
                inval = clamp(n, 1/8 * height, 3/8 * height)
                hght = cubic(inval, 1/8 * height, startheight, 3/8 * height, endheight)
            if(fliptype == 2):
                dst = pow(pow(n,2) + pow(m,2), 0.5)
                inval = clamp(dst, 1/8 * (width + height) / 2, 3/8 * (width + height) / 2)
                hght = cubic(inval, 1/8 * (width + height) / 2, startheight, 3/8 * (width + height) / 2, endheight)
            row.append(hght)
            m = m + 1
        genmap.append(row)
        n = n + 1
    #load prefabs
    prefab_families = get_prefab_families()
    chosen_family = random.choice(prefab_families)
    print("\tprefab family: " + chosen_family)
    prefab_info = get_prefab_infofile(chosen_family)
    #add in prefabs
    prefab_number = random.randint(2, 8) * max((map_properties["mapsizex"] + map_properties["mapsizey"]) // 24, 1)
    if(fliptype == 2):
        prefab_number = prefab_number // 2
    prefab_overall_scalar_low = random.randint(5, 8) / 4
    prefab_overall_scalar_high = prefab_overall_scalar_low * random.randint(3, 5) / 2
    prefab_severity = random.randint(1, 8) / 4

    print("\tprefab_number: " + str(prefab_number))
    print("\tprefab_overall_scalar_low: " + str(prefab_overall_scalar_low))
    print("\tprefab_overall_scalar_high: " + str(prefab_overall_scalar_high))
    print("\tprefab_severity: " + str(prefab_severity))

    def IsBetween( val, l, u ):
        if(val > l) and (val < u):
            return True
        return False

    def CheckDeadZone( x, y, w, h, pfo_w, pfo_h, fliptype ):
        if(fliptype == 0):
            if(IsBetween(x, -1 * pfo_w // 2, w / 24)):
                return True
            #if(x < pfo_w):
            #    return True
        if(fliptype == 1):
            if(IsBetween(y, -1 * pfo_h // 2, h / 24)):
                return True
            #if(y < 0):
            #    return True
        if(fliptype == 2):
            dst = pow(pow(x, 2) + pow(y, 2), 0.5)
            if(IsBetween(dst, 0, (w + h) / 24)):
                return True
            if((x < 0) and (y < 0)):
                return True
        return False

    n = 0
    while n < prefab_number:
        prefab_object = get_prefab_object(chosen_family, prefab_info, random.uniform(prefab_overall_scalar_low, prefab_overall_scalar_high), prefab_severity)
        pfo_w = len(prefab_object[0])
        pfo_h = len(prefab_object)
        divx = 1
        divy = 1

        xplace = random.randint(-1 * pfo_w // 2, int((width / divx) - pfo_w / 2))
        yplace = random.randint(-1 * pfo_h // 2, int((height / divy) - pfo_h / 2))
        if(fliptype == 0):
            divx = 2
            xplace = random.randint(0, int((width / divx)))
        if(fliptype == 1):
            divy = 2
            yplace = random.randint(0, int((height / divy)))
        if(fliptype == 2):
            divx = 2
            divy = 2
            radius = random.randint(0, int(max((width + height) / 2 - (pfo_w + pfo_h) / 2,0)))
            ang = random.randint(-45, 135)
            xplace = int(math.cos(ang) * radius)
            yplace = int(math.sin(ang) * radius)

#        xplace = random.randint(-1 * pfo_w // 2, int((width / divx) - pfo_w / 2))
#        yplace = random.randint(-1 * pfo_h // 2, int((height / divy) - pfo_h / 2))
        #xplace = random.randint(-1 * pfo_w // 2, int(width / divx))
        #yplace = random.randint(-1 * pfo_h // 2, int(height / divy))
        #print("width // 8: " + str(width // 8) + " / height // 8: " + str(height // 8) + " / xplace: " + str(xplace) + " / yplace: " + str(yplace))

        #while(CheckDeadZone(xplace, yplace, width, height, pfo_w, pfo_h, fliptype)):
            #xplace = random.randint(-1 * pfo_w // 2, int((width / divx) - pfo_w / 2))
            #yplace = random.randint(-1 * pfo_h // 2, int((height / divy) - pfo_h / 2))
            #xplace = random.randint(-1 * pfo_w // 2, int(width / divx))
            #yplace = random.randint(-1 * pfo_h // 2, int(height / divy))
            #print("fail, rerolling")
            #print("LOW: " + str(-1 * pfo_h // 2) + " / HIGH: " + str(int((height / divy) - pfo_h / 2)))
            #print("xplace: " + str(xplace) + " / yplace: " + str(yplace))

        genmap = place_prefab(genmap, prefab_object, xplace, yplace)
        print("prefab placed at: (" + str(xplace) + ", " + str(yplace) + ")")

        n = n + 1

    print("prefab generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("There's too many inputs required for this script, run srmg_1.py")
    #print(str(genmap))
    print("finished")
