#contour_hill_generator.py
#author: Sestze

#Generates randomized 256x256px "hills" that can be used as prefabs.
#Standalone version of the hill contour creator from path_generation


import random
import math
import os

from PIL import Image

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
    #3 - cubic spline
    if(hilltype == 3):
        outval = cubic(var, xo, yt, xt, yo)

    if(debug == 1):
        print("For hilltype " + str(hilltype))
        print(str(var) + ", (" + str(xo) + ", " + str(yo) + "), (" + str(xt) + ", " + str(yt) + ")")
        print("\tyields: " + str(outval))
    return outval

def perlin_1d_interp( tht, grads ):
    tht = tht + math.pi
    tht = min(max(tht, 0), math.pi * 2 - 0.001)
    
    key = int((tht / (math.pi * 2)) * len(grads))

    xo = key * math.pi * 2 / len(grads)
    xt = (key + 1) * math.pi * 2 / len(grads)
    
    disp = tht - xo
    disp2 = tht - xt
    
    yo = grads[key % len(grads)][0] * disp
    yt = grads[(key+1) % len(grads)][0] * disp2

    ret = cubic(tht, xo, yo, xt, yt)

    return ret

def simple_contour_hill(filename):
    w = 256
    h = 256
    wobble = random.uniform(0.1, 0.9)
    hilltype = random.randint(0, 3)

    hill_maxh = random.uniform(0.4, 1)

    grads = []
    edges = random.randint(6, 10)
    n = 0
    while n < edges:
        tht = random.uniform(0, math.pi * 2)
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        grads.append([xv, yv])
        n = n + 1

    grads2 = []
    grads3 = []
    edges = random.randint(3, 6)
    n = 0
    while n < edges:
        tht = random.uniform(0, math.pi * 2)
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        grads2.append([xv, yv])

        tht = random.uniform(0, math.pi * 2)
        r = 1
        xv = r * math.cos(tht)
        yv = r * math.sin(tht)
        grads3.append([xv, yv])
        n = n + 1

    interps = []

    n = 0
    while n < h:
        row = []
        m = 0
        while m < w:
            xdisp = m - w / 2
            ydisp = n - h / 2
            dst = pow(pow(xdisp, 2) + pow(ydisp, 2), 0.5)

            ang = 0
            if(xdisp == 0):
                if(ydisp > 0):
                    ang = math.pi / 2
                else:
                    ang = math.pi / -2
            else:
                ang = math.atan2(ydisp,xdisp)
            hght = 0
            func_out = perlin_1d_interp(ang, grads)
            curverad = ((1 + wobble * func_out) / (1 + wobble)) * 120
            if(dst < curverad):
                func_out2 = (0.5 + perlin_1d_interp(ang, grads2) * 0.5) * 0.4
                func_out3 = func_out2 + 0.1 + (0.5 + perlin_1d_interp(ang, grads3) * 0.5) * (1 - func_out2 + 0.1)
                                
                dil = min(max((dst/curverad - func_out2)/(func_out3-func_out2), 0), 1)
                hght = hill_func(dst * dil, 0, 0, curverad, hill_maxh, hilltype)
                
            row.append(hght)
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
    basename = "contour_hill"
    outdir = "contour_hill/"
    os.makedirs(outdir, exist_ok=True)
    ptxt = ""
    n = 0
    while n < maxhills:
        ptxt = ptxt + basename + "_" + str(n) + ".bmp"
        ptxt = ptxt + simple_contour_hill(outdir + basename + "_" + str(n) + ".bmp")
        n = n + 1
    hmap = open(outdir + "fablist.txt", 'w')
    hmap.write(ptxt)
    hmap.close()
    print("... saved " + outdir + "fablist.txt")
    
if __name__ == "__main__":
    print("simple_contour_hill_generator.py")
    main()
    print("finished")
