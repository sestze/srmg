#complicated_texturing.py
#author: Sestze
#
#starting with the base texturing method that srmg_1.py has, adding more mathematical
#depth to the texturing process and leaning on the gradient a fair bit more.

import random
import struct
import zlib
import math
import os

from PIL import Image

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
        while m < (len(flattened[n])):
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

def find_flats ( heightmap, gradient ):
    h = len(heightmap)
    w = len(heightmap[0])

    flats = []

    n = 0
    while n < h:
        m = 0
        while m < w:
            gradcomb = pow(pow(gradient[n][m][0],2) + pow(gradient[n][m][1],2), 0.5)
            if(gradcomb < 0.01):
                hght = heightmap[n][m]
                include = True
                r = 0
                while(r < len(flats)):
                    disp = abs(flats[r] - hght)
                    if(disp < 10):
                        include = False
                        r = len(flats)
                    r = r + 1
                if(include == True):
                    flats.append(hght)
            m = m + 1
        n = n + 1
        
    return flats

def generate_texmap_complicated( genmap, texture_family, metmap, mult, minh, pris_tht ):
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
            infopack.append([int(commasep[1]), int(commasep[2]), commasep[0]])
            print(str(commasep[0]) + ": " + str(commasep[1]) + ", " + str(commasep[2]))
        n = n + 1
    
    #expand...
    expanded_heightmap = generate_expandmap( genmap )
    gradient_heightmap = generate_gradient ( genmap )

    flats = find_flats(expanded_heightmap, gradient_heightmap)
    flats.sort()

    flats_textures = []
    n = 0
    while n < len(flats):
        pris_temp = pris_tht
        if(pris_tht != -1):
            pris_temp = pris_temp + random.uniform(math.pi / -12, math.pi / 12)
            if(color_types == 1):
                pris_temp = pris_temp + random.randint(0, 1) * math.pi
        if(n < len(infopack)):
            flats_textures.append([flats[n], n, pris_temp])
            print("height: " + str(flats[n]) + ", texture: " + infopack[n][2] + ", pris: " + str(pris_temp))
        else:
            tex_chosen = random.randint(0, len(infopack) - 1)
            flats_textures.append([flats[n], tex_chosen, pris_temp])
            print("height: " + str(flats[n]) + ", texture: " + infopack[tex_chosen][2] + ", pris: " + str(pris_temp))
        n = n + 1
    
    #load textures...
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
        
    total_width = len(expanded_heightmap[0])
    total_height = len(expanded_heightmap)

    print("generating perlin noise")
    perlin_grads = []

    div = min(total_width, total_height) // 16
    n = 0
    while n < total_height + div:
        m = 0
        row = []
        while m < total_width + div:
            tht = random.uniform(0, math.pi*2)
            r = 1
            xv = r * math.cos(tht)
            yv = r * math.sin(tht)

            row.append([xv, yv])
            m = m + div
        perlin_grads.append(row)
        n = n + div

    def interpolate(x0, x1, var):
        ret = (x1 - x0) * ((var * (var * 6.0 - 15) + 10) * var * var * var) + x0
        return ret

    interps = []
    n = 0
    while n < total_height:
        m = 0
        row = []
        while m < total_width:
            gradx = m // div
            grady = n // div

            n0 = perlin_grads[grady][gradx]    #top left
            n1 = perlin_grads[grady][gradx+1]  #top right
            n2 = perlin_grads[grady+1][gradx]  #bottom left
            n3 = perlin_grads[grady+1][gradx+1] #bottom right

            #dots
            n0d = (n0[0]*(m - (gradx) * div) + n0[1]*(n - (grady) * div)) / div
            n1d = (n1[0]*(m - (gradx+1) * div) + n1[1]*(n - grady * div)) / div
            n2d = (n2[0]*(m - (gradx) * div) + n2[1]*(n - (grady+1)*div)) / div
            n3d = (n3[0]*(m - (gradx+1) * div) + n3[1]*(n - (grady+1)*div)) / div

            #tops
            ix1 = interpolate(n0d, n1d, (m - (gradx) * div) / div)
            #bottoms
            ix2 = interpolate(n2d, n3d, (m - (gradx) * div) / div)
            #top to bottom
            it = interpolate(ix1, ix2, (n - (grady) * div) / div)

            fix = (it * 0.5 + 0.5) * 12

            row.append(fix)
            m = m + 1
        interps.append(row)
        n = n + 1
    print("perlin done")

    def isbetween( var, l, u ):
        if (var > l) and (var < u):
            return True
        return False

    def perlin_merge ( x, y, mx, my, key, tex, perlinval ):
        tupf = tex[key][y%my][x%mx]
        tupv = tex[key][my - y%my - 1][x%mx]
        tuph = tex[key][y%my][mx - x%mx - 1]
        tupr = tex[key][my - y%my - 1][mx - x%mx - 1]

        mod = int(perlinval) % 4
        mod2 = int(perlinval) % 3
        lst = [tupf, tupv, tuph, tupr]
        firstpick = lst[mod]
        secondpick = lst[(mod + 1 + mod2) % len(lst)]

        tail = perlinval % 1

        nr = firstpick[0] * (1 - tail) + secondpick[0] * (tail)
        ng = firstpick[1] * (1 - tail) + secondpick[1] * (tail)
        nb = firstpick[2] * (1 - tail) + secondpick[2] * (tail)

        return (nr, ng, nb)
        

    #merge textures...
    def merge_function( x, y, tex, ip, ft, height, pn ):
        #tupa/tupb/tupc tuples from pixels
        r = 0
        g = 0
        b = 0

        mrg = 0.8
        base = 200
        extend = 255 - base

        #clamping the heights
        height = min(ft[len(ft)-1][0], height)
        height = max(ft[0][0], height)

        if(len(ft) > 1):
            key = 0
            while(height > ft[key][0]):
                key = key + 1
            key = key - 1
            while(key+1 > (len(ft) - 1)):
                print("key oob, height is: " + str(height))
                print(str(len(ip)))
                key = key - 1

            lk = ft[key][1]
            lp = ft[key][2]
            lw = ip[lk][0]
            lh = ip[lk][1]
            lpe = perlin_merge(x, y, lw, lh, lk, tex, pn[y][x])
            lr = lpe[0]
            lg = lpe[1]
            lb = lpe[2]
##            lr = tex[lk][y%lh][x%lw][0]
##            lg = tex[lk][y%lh][x%lw][1]
##            lb = tex[lk][y%lh][x%lw][2]

            if(lp != -1):
                lr = lr * mrg + (base + extend * math.cos(lp)) * (1 - mrg)
                lg = lg * mrg + (base + extend * math.cos(lp + math.pi * 2 / 3)) * (1 - mrg)
                lb = lb * mrg + (base + extend * math.cos(lp + math.pi * 4 / 3)) * (1 - mrg)

            rk = ft[key+1][1]
            rp = ft[key+1][2]
            rw = ip[rk][0]
            rh = ip[rk][1]
            rpe = perlin_merge(x, y, rw, rh, rk, tex, pn[y][x])
            rr = rpe[0]
            rg = rpe[1]
            rb = rpe[2]
##            rr = tex[rk][y%rh][x%rw][0]
##            rg = tex[rk][y%rh][x%rw][1]
##            rb = tex[rk][y%rh][x%rw][2]

            if(rp != -1):
                rr = rr * mrg + (base + extend * math.cos(rp)) * (1 - mrg)
                rg = rg * mrg + (base + extend * math.cos(rp + math.pi * 2 / 3)) * (1 - mrg)
                rb = rb * mrg + (base + extend * math.cos(rp + math.pi * 4 / 3)) * (1 - mrg)

            p = (height - ft[key][0]) / (ft[key+1][0] - ft[key][0])
            q = 1 - p

            r = lr * q + rr * p
            g = lg * q + rg * p
            b = lb * q + rb * p

            hm = max(min(50+height/2, 80), 20)
            r = r * hm / 80
            g = g * hm / 80
            b = b * hm / 80
            #print("height: " + str(height) + "/ key: " + str(key) + "/ p: " + str(p))
        elif(len(ft) > 0):
            #If there's only one height, output the base texture
            lk = ft[0][1]
            lw = ip[lk][0]
            lh = ip[lk][1]

            lpe = perlin_merge(x, y, lw, lh, lk, tex, pn[y][x])
            r = lpe[0]
            g = lpe[1]
            b = lpe[2]
            #r = tex[lk][y%lh][x%lw][0]
            #g = tex[lk][y%lh][x%lw][1]
            #b = tex[lk][y%lh][x%lw][2]
            
            if(ft[0][2] != -1):
                r = r * mrg + (base + extend * math.cos(ft[0][2])) * (1 - mrg)
                g = g * mrg + (base + extend * math.cos(ft[0][2] + math.pi * 2 / 3)) * (1 - mrg)
                b = b * mrg + (base + extend * math.cos(ft[0][2] + math.pi * 4 / 3)) * (1 - mrg)

            hm = max(min(50+height/2, 80), 20)
            r = r * hm / 80
            g = g * hm / 80
            b = b * hm / 80
        else:
            #No found heights? somehow something went very wrong
            print("I don't know how you got here.")
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
    count = 0
    n = 0
    while (n < total_height):
        m = 0
        row = []
        while (m < total_width):
            ah = (expanded_heightmap[n][m] - minh) * mult
            merge_pixel = merge_function(m, n, texseq, infopack, flats_textures, ah, interps)
            gradpix = gradient_merge(m, n, gradient_heightmap, merge_pixel)
            row.append(gradpix)
            if(n * total_width + m > count):
                perc = int((n * total_width + m) / (total_width * total_height) * 100)
                print("... " + str(perc) + "% complete")
                count = count + total_width * total_height / 20
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
                if(xs < len(texmap[0])) and (ys < len(texmap)):
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

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("There's too many inputs required for this script, run srmg_1.py")
    #print(str(genmap))
    print("finished")
