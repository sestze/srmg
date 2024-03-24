#perlin_hill_generator.py
#author: Sestze

#Generates randomized 256x256px "hills" that can be used as prefabs.


import random
import math
import os

from PIL import Image

def perlin_r_func(x, y, wc, hc, functype):
    out = 1
    if(functype == 0):
        #euclid
        dst = pow(pow(x - wc, 2) + pow(y - hc, 2), 0.5)
        thr = (wc + hc) / 2
        out = 0
        if(dst < thr):
            p = (thr - dst) / thr
            q = 1 - p
            out = random.uniform(max(q - 0.2, 0), q)
    if(functype == 1):
        #euclid - downward
        dst = pow(pow(x - wc, 2) + pow(y - hc, 2), 0.5)
        thr = (wc + hc) / 2
        out = 0
        if(dst < thr):
            p = (thr - dst) / thr
            q = 1 - p
            out = random.uniform(-1 * q, min(-1 * q + 0.2, 0))
    if(functype == 2):
        out = random.uniform(0.5, 1.5)

    return out

def perlin_tht_func(x, y, wc, hc, functype):
    out = random.uniform(0, math.pi * 2)
    if(functype == 0):
        #point towards the center
        out = math.atan2(hc - y, wc - x)
    if(functype == 1):
        #point away from the center
        out = math.atan2(y - hc, x - wc)
    if(functype == 2):
        #down-right
        out = math.pi / 4

    return out

def perlin_it_func(it, x, y, wc, hc, functype):
    out = it
    if(functype == 0):
        #above
        dst = pow(pow(x - wc, 2) + pow(y - hc, 2), 0.5)
        thr = (hc + wc) / 2
        out = 0
        if(dst < thr):
            p = min((thr - dst) / thr, 0.9)
            q = 1 - p
            out = p * (0.5 + it * 0.5) + p * q
    if(functype == 1):
        #below
        dst = pow(pow(x - wc, 2) + pow(y - hc, 2), 0.5)
        thr = (hc + wc) / 2
        out = 0
        if(dst < thr):
            p = min((thr - dst) / thr, 0.9)
            q = 1 - p
            out = -1 * p * (0.5 + it * 0.5) - p * q
    if(functype == 2):
        #above, show only positive
        out = max(it, 0)
    if(functype == 3):
        #below, show only negative
        out = -1 * max(it, 0)
    return out

def perlin_hill(filename):
    grads = []
    w = 256
    h = 256

    subs = random.randint(3, 4)
    rtype = random.randint(0, 1)
    rtype = 2
    ttype = random.randint(0, 1)
    ttype = 3
    ittype = random.randint(2, 3)
    hmod = 1
    divx = w / subs
    divy = h / subs
    n = 0
    while n < subs + 1:
        m = 0
        row = []
        while m < subs + 1:
            tht = perlin_tht_func(divx * m, divy * n, w / 2, h / 2, ttype)
            r = perlin_r_func(divx * m, divy * n, w / 2, h / 2, rtype)
            xv = r * math.cos(tht)
            yv = r * math.sin(tht)

            row.append([xv, yv])
            m = m + 1
        grads.append(row)
        n = n + 1
        ##makes things tile, not necessary
    n = 0
    while n < len(grads):
        m = 0
        while m < len(grads[0]):
            if(n == 0) or (m == 0):
                xv = 0
                yv = 0
                grads[n][m] = [xv, yv]
            if (n == subs) or (m == subs):
                xv = 0
                yv = 0
                grads[n][m] = [xv, yv]
            m = m + 1
        n = n + 1

    def interpolate(x0, x1, var):
        #ret = (x1 - x0) * var + x0
        #smoothstep
        #ret = (x1 - x0) * (3 - var * 2) * var * var + x0
        #smootherstep
        ret = (x1 - x0) * ((var * (var * 6.0 - 15) + 10) * var * var * var) + x0

        return ret

    interps = []
    n = 0
    while n < h:
        m = 0
        row = []
        while m < w:
            gradx = int((m / w) * subs)
            grady = int((n / h) * subs)

            #neighbors
            n0 = grads[grady][gradx]    #top left
            n1 = grads[grady][gradx+1]  #top right
            n2 = grads[grady+1][gradx]  #bottom left
            n3 = grads[grady+1][gradx+1] #bottom right

            #dots
            n0d = (n0[0]*(m - (gradx) * divx) / divx + n0[1]*(n - (grady) * divy) / divy)
            n1d = (n1[0]*(m - (gradx+1) * divx) / divx + n1[1]*(n - grady * divy) / divy)
            n2d = (n2[0]*(m - (gradx) * divx) / divx + n2[1]*(n - (grady+1)*divy) / divy)
            n3d = (n3[0]*(m - (gradx+1) * divx) / divx + n3[1]*(n - (grady+1)*divy) / divy)

            #tops
            ix1 = interpolate(n0d, n1d, (m - (gradx) * divx) / divx)
            #bottoms
            ix2 = interpolate(n2d, n3d, (m - (gradx) * divx) / divx)
            #top to bottom
            it = interpolate(ix1, ix2, (n - (grady) * divy) / divy)
            
            it = perlin_it_func(it, m, n, w / 2, h / 2, ittype) * hmod

            row.append(it)
            m = m + 1
        interps.append(row)
        n = n + 1

    ofw = w
    ofh = h

    outfile = Image.new('RGB', (ofw, ofh), 'black')
    outfile_pixels = outfile.load()
    n = 0
    while n < ofh:
        m = 0
        while m < ofw:
            adj = int(128 + interps[n%h][m%w] * 120)
            pix = (adj, adj, adj)
            outfile_pixels[m, n] = pix
            m = m + 1
        n = n + 1
    outfile.save(filename)
    print("... saved " + filename)
    outstr = "," + str(ofw) + "," + str(ofh) + "\n"
    return outstr

def main():
    random.seed()
    maxhills = 20
    basename = "perlin_hill"
    outdir = "perlin_hill/"
    os.makedirs(outdir, exist_ok=True)
    ptxt = ""
    n = 0
    while n < maxhills:
        ptxt = ptxt + basename + "_" + str(n) + ".bmp"
        ptxt = ptxt + perlin_hill(outdir + basename + "_" + str(n) + ".bmp")
        n = n + 1
    hmap = open(outdir + "fablist.txt", 'w')
    hmap.write(ptxt)
    hmap.close()
    print("... saved " + outdir + "fablist.txt")
    
if __name__ == "__main__":
    print("perlin_hill_generator.py")
    main()
    print("finished")
