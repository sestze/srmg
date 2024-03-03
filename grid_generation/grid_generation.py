#grid_generation.py
#author: Sestze
#
#Creates grid subdivisions and joins cells using ramps.
#
#How does this work, step by step?
#
#
#TODO:
#   - How can I do a contour from the space created?
#

import random
import struct
import zlib
import math
import os

from PIL import Image

def generate_map_using_grid (map_properties, start_positions, fliptype):
    #set up some variables
    width = int(map_properties["mapsizex"]) * 64 + 1
    height = int(map_properties["mapsizey"]) * 64 + 1
    genmap = []

    grid_x = map_properties["mapsizex"] * 2
    grid_y = map_properties["mapsizey"] * 2

    #define filltypes
    filltype = random.randint(0, 1)
    #bottom to top, top to bottom

    upper = 70
    mid = 50
    lower = 30

    fillgrid = [lower, mid, upper]
    if(filltype == 1):
        fillgrid = [upper, mid, lower]

    grid = []
    
    #create grid with base filltype
    n = 0
    while n < grid_y:
        m = 0
        row = []
        while m < grid_x:
            xvar = width * (m + 1) / (grid_x + 1)
            yvar = height * (n + 1) / (grid_y + 1)
            fill = fillgrid[0]
            type_of_square = 0
            row.append([xvar, yvar, fill, type_of_square])
            m = m + 1
        grid.append(row)
        n = n + 1

    #adjust grid with second filltype

    grid_second = []
    grid_second_children = []
    num_grid_second = random.randint(2, 4)
    num_grid_second_children = 5 - num_grid_second
    n = 0
    while n < num_grid_second:
        #fliptype placement
        xmin = 0
        xmax = width
        ymin = 0
        ymax = height

        if(fliptype == 0):
            xmax = xmax // 2
        if(fliptype == 1):
            ymax = ymax // 2
        if(fliptype == 4):
            xmax = xmax // 2
            ymax = ymax // 2

        xplace = random.randint(xmin, xmax)
        yplace = random.randint(ymin, ymax)

        if(fliptype == 2):
            ymax = height - xplace
            yplace = random.randint(ymin, ymax)
        if(fliptype == 3):
            xmax = yplace
            xplace = random.randint(xmin, xmax)
        if(fliptype == 5):
            xmax = max(-1 * abs(yplace - height // 2) + width // 2, xmin) + 1
            xpos = random.randint(xmin, xmax)

        radius = 0.5 * (5 - num_grid_second) / 5 * min(width, height)

        grid_second.append([xplace, yplace, radius])
        
        #place children 
        m = 0
        while m < num_grid_second_children:
            ang = random.uniform(0, math.pi * 2)
            radius2 = radius / 2

            xplace2 = xplace + math.cos(ang) * radius
            yplace2 = yplace + math.sin(ang) * radius

            grid_second_children.append([xplace2, yplace2, radius2])
            m = m + 1
        n = n + 1

    #adjust grid with third filltype
    grid_third = []
    grid_third_children = []
    num_grid_third = random.randint(2, 4)
    num_grid_third_children = 5 - num_grid_second
    n = 0
    while n < num_grid_third:
        grid_second_choice = random.choice(grid_second)
        ang = random.uniform(0, math.pi * 2)
        rplace = random.uniform(0, grid_second_choice[2] * 0.5)

        xplace = grid_second_choice[0] + math.cos(ang) * rplace
        yplace = grid_second_choice[1] + math.sin(ang) * rplace
        radius = (grid_second_choice[2] - rplace) * 0.9
        
        #place children 
        m = 0
        while m < num_grid_second_children:
            ang2 = random.uniform(ang + math.pi / 2, ang + 3 * math.pi / 2)
            radius2 = radius / 2

            xplace2 = xplace + math.cos(ang2) * radius
            yplace2 = yplace + math.sin(ang2) * radius

            grid_third_children.append([xplace2, yplace2, radius2])
            m = m + 1
        n = n + 1

    #use grid_second and grid_third to adjust grid heights

    # - grid_second
    n = 0
    while(n < len(grid_second)):
        m = 0
        while(m < grid_y):
            r = 0
            while(r < grid_x):
                dst = pow(pow(grid[m][r][0] - grid_second[n][0], 2) + pow(grid[m][r][1] - grid_second[n][1], 2),0.5)
                if(dst < grid_second[n][2]):
                    grid[m][r][2] = fillgrid[1]
                r = r + 1
            m = m + 1
        n = n + 1

    # - grid_second_children
    n = 0
    while(n < len(grid_second_children)):
        m = 0
        while(m < grid_y):
            r = 0
            while(r < grid_x):
                dst = pow(pow(grid[m][r][0] - grid_second_children[n][0], 2) + pow(grid[m][r][1] - grid_second_children[n][1], 2),0.5)
                if(dst < grid_second_children[n][2]):
                    grid[m][r][2] = fillgrid[1]
                r = r + 1
            m = m + 1
        n = n + 1

    # - grid_third
    n = 0
    while(n < len(grid_third)):
        m = 0
        while(m < grid_y):
            r = 0
            while(r < grid_x):
                dst = pow(pow(grid[m][r][0] - grid_third[n][0], 2) + pow(grid[m][r][1] - grid_third[n][1], 2),0.5)
                if(dst < grid_third[n][2]):
                    grid[m][r][2] = fillgrid[2]
                r = r + 1
            m = m + 1
        n = n + 1

    # - grid_third_children
    n = 0
    while(n < len(grid_third_children)):
        m = 0
        while(m < grid_y):
            r = 0
            while(r < grid_x):
                dst = pow(pow(grid[m][r][0] - grid_third_children[n][0], 2) + pow(grid[m][r][1] - grid_third_children[n][1], 2),0.5)
                if(dst < grid_third_children[n][2]):
                    grid[m][r][2] = fillgrid[2]
                r = r + 1
            m = m + 1
        n = n + 1

    # - start positions
    n = 0
    while(n < len(start_positions)):
        m = 0
        while(m < grid_y):
            r = 0
            while(r < grid_x):
                dst = pow(pow(grid[m][r][0] - start_positions[n][0] * width, 2) + pow(grid[m][r][1] - start_positions[n][1] * height, 2),0.5)
                if(dst < 48):
                    grid[m][r][2] = fillgrid[0]
                r = r + 1
            m = m + 1
        n = n + 1

    #reassign ramp settings to prevent ramps along the mirror line
    if(fliptype == 0):
        n = 0
        while n < grid_y:
            m = int(grid_x / 2) - 1
            grid[n][m][3] = 3
            n = n + 1
    if(fliptype == 1):
        m = 0
        while m < grid_x:
            n = int(grid_y / 2) - 1
            grid[n][m][3] = 3
            m = m + 1
    if(fliptype == 2):
        n = 0
        while n < grid_y:
            grid[n][m - n - 1][3] = 3
            n = n + 1
    if(fliptype == 3):
        n = 0
        while n < grid_y:
            m = n
            grid[n][m][3] = 3
            n = n + 1
    if(fliptype == 4):
        n = 0
        while n < grid_y:
            m = int(grid_x / 2) - 1
            grid[n][m][3] = 3
            n = n + 1
        m = 0
        while m < grid_x:
            n = int(grid_y / 2) - 1
            grid[n][m][3] = 3
            m = m + 1
    if(fliptype == 5):
        n = 0
        while n < grid_y:
            m = -1 * abs(n - grid_y // 2) + grid_x // 2
            grid[n][m][3] = 3
            n = n + 1

    #find neighboring cells to define ramps

    n = 0
    while n < grid_y:
        m = 0
        while m < grid_x:
            home_filltype = 0
            while(grid[n][m][2] != fillgrid[home_filltype]):
                home_filltype = home_filltype + 1
            #vertical check
            if(n < grid_y - 2):
                neighbor_filltype = 0
                while(grid[n + 1][m][2] != fillgrid[neighbor_filltype]):
                    neighbor_filltype = neighbor_filltype + 1
                double_neighbor = 0
                while(grid[n + 2][m][2] != fillgrid[double_neighbor]):
                    double_neighbor = double_neighbor + 1
                if(abs(home_filltype - neighbor_filltype) == 1) and(neighbor_filltype == double_neighbor):
                    uniform = random.uniform(0, 1)
                    if(grid[n + 1][m][3] == 0) and (grid[n][m][3] == 0) and (grid[n+2][m][3] == 0) and (uniform < 0.5):
                        #set to 1 to denote "vertical"
                        grid[n][m][3] = 3
                        grid[n + 1][m][3] = 1
                        grid[n + 2][m][3] = 3
            #horizontal check
            if(m < grid_x - 2):
                neighbor_filltype = 0
                while(grid[n][m + 1][2] != fillgrid[neighbor_filltype]):
                    neighbor_filltype = neighbor_filltype + 1
                double_neighbor = 0
                while(grid[n][m + 2][2] != fillgrid[double_neighbor]):
                    double_neighbor = double_neighbor + 1
                if(abs(home_filltype - neighbor_filltype) == 1) and(neighbor_filltype == double_neighbor):
                    uniform = random.uniform(0, 1)
                    if(grid[n][m + 1][3] == 0) and (grid[n][m][3] == 0) and (grid[n][m+2][3] == 0) and (uniform < 0.5):
                        #set to 2 to denote "horizontal"
                        grid[n][m][3] = 3
                        grid[n][m + 1][3] = 2
                        grid[n][m + 2][3] = 3
            m = m + 1
        n = n + 1

    #find neighboring cells sans ramps to define trigs
    n = 0
    while n < grid_y:
        m = 0
        while m < grid_x:
            if(grid[n][m][3] == 0) or (grid[n][m][3] == 3):
                #up-left trig
                if(n > 0) and (m > 0):
                    neighbor_1 = grid[n-1][m]
                    neighbor_2 = grid[n][m-1]
                    if((neighbor_1[3] == 0) or (neighbor_1[3] == 3)) and ((neighbor_2[3] == 0) or(neighbor_1[3] == 3)):
                        if(neighbor_1[2] == neighbor_2[2]) and (grid[n][m][2] < neighbor_1[2]):
                            grid[n][m][2] = neighbor_1[2]
                            grid[n][m][3] = 4
                            print("found an up-left trig")
                #up-right trig
                if(n > 0) and (m < grid_x - 1):
                    neighbor_1 = grid[n-1][m]
                    neighbor_2 = grid[n][m+1]
                    if((neighbor_1[3] == 0) or (neighbor_1[3] == 3)) and ((neighbor_2[3] == 0) or(neighbor_1[3] == 3)):
                        if(neighbor_1[2] == neighbor_2[2]) and (grid[n][m][2] < neighbor_1[2]):
                            grid[n][m][2] = neighbor_1[2]
                            grid[n][m][3] = 5
                            print("found an up-right trig")
                #bot-left trig
                if(n < grid_y - 1) and (m > 0):
                    neighbor_1 = grid[n+1][m]
                    neighbor_2 = grid[n][m-1]
                    if((neighbor_1[3] == 0) or (neighbor_1[3] == 3)) and ((neighbor_2[3] == 0) or(neighbor_1[3] == 3)):
                        if(neighbor_1[2] == neighbor_2[2]) and (grid[n][m][2] < neighbor_1[2]):
                            grid[n][m][2] = neighbor_1[2]
                            grid[n][m][3] = 6
                            print("found a bot-left trig")
                #bot-right trig
                if(n < grid_y - 1) and (m < grid_x - 1):
                    neighbor_1 = grid[n+1][m]
                    neighbor_2 = grid[n][m+1]
                    if((neighbor_1[3] == 0) or (neighbor_1[3] == 3)) and ((neighbor_2[3] == 0) or(neighbor_1[3] == 3)):
                        if(neighbor_1[2] == neighbor_2[2]) and (grid[n][m][2] < neighbor_1[2]):
                            grid[n][m][2] = neighbor_1[2]
                            grid[n][m][3] = 7
                            print("found a bot-right trig")
            m = m + 1
        n = n + 1

    def cubic(val, xo, yo, xt, yt, dbg=0):
        if(dbg != 0):
            print("cubic spline function: " + str(val) + ", " + str(xo) + ", " + str(yo) + ", " + str(xt) + ", " + str(yt))

        if(val < xo):
            val = xo
        if(val > xt):
            val = xt
        A = (-2 * (yt - yo)) / pow((xt - xo), 3)
        B = 3 * (yt - yo) / pow((xt - xo), 2)
        C = 0
        D = yo
        xin = val - xo

        retval = A * pow(xin, 3) + B * pow(xin, 2) + C * xin + D
        if(dbg != 0):
            print("Output: " + str(retval))
        return retval

    def trig_return(valx, valy, xo, yo, xt, yt, ho, ht, trigtype):
        if(valx < xo):
            valx = xo
        if(valx > xt):
            valx = xt

        if(valy < yo):
            valy = yo
        if(valy > yt):
            valy = yt

        #4 and 7
        trigfunc = -1 * (valx - xo) + yt
        if(trigtype == 5) or (trigtype == 6):
            trigfunc = valx - xo + yo

        if(trigtype == 4):
            if(valy < trigfunc):
                return ho
            else:
                return ht
        if(trigtype == 5):
            if(valy < trigfunc):
                return ho
            else:
                return ht
        if(trigtype == 6):
            if(valy < trigfunc):
                return ht
            else:
                return ho
        if(trigtype == 7):
            if(valy < trigfunc):
                return ht
            else:
                return ho

    #fill based on grid values.
    n = 0
    while(n < height):
        m = 0
        row = []
        while(m < width):
            keyx = 1
            while(m >= width * keyx / grid_x):
                keyx = keyx + 1
            keyy = 1
            while(n >= height * keyy / grid_y):
                keyy = keyy + 1

            while(keyx >= len(grid[0])):
                keyx = keyx - 1
            while(keyy >= len(grid)):
                keyy = keyy - 1

            hght = grid[keyy - 1][keyx - 1][2]
            #vertical ramp
            if(grid[keyy - 1][keyx - 1][3] == 1):
                hght = cubic(n, height * (keyy - 1) / grid_y, grid[keyy - 2][keyx - 1][2], height * (keyy) / grid_y, grid[keyy - 1][keyx - 1][2])
            #horizontal ramp
            if(grid[keyy - 1][keyx - 1][3] == 2):
                hght = cubic(m, width * (keyx - 1) / grid_x, grid[keyy - 1][keyx - 2][2], width * (keyx) / grid_x, grid[keyy - 1][keyx - 1][2])
            #trigs
            trigtype = grid[keyy - 1][keyx - 1][3]
            if(trigtype > 3) and (trigtype < 8):
                #print("type is: " + str(trigtype))
                if(trigtype == 4) or (trigtype == 5):
                    #print("ho: " + str(grid[keyy - 1][keyx - 1][2]) + ", ht: " + str(grid[keyy][keyx - 1][2]))
                    hght = trig_return(m, n, width * (keyx - 1) / grid_x, height * (keyy - 1) / grid_y, width * keyx / grid_x, height * keyy / grid_y, grid[keyy - 1][keyx - 1][2], grid[keyy][keyx - 1][2], grid[keyy - 1][keyx - 1][3])
                if(trigtype == 6) or (trigtype == 7):
                    #print("ho: " + str(grid[keyy - 1][keyx - 1][2]) + ", ht: " + str(grid[keyy - 2][keyx - 1][2]))
                    hght = trig_return(m, n, width * (keyx - 1) / grid_x, height * (keyy - 1) / grid_y, width * keyx / grid_x, height * keyy / grid_y, grid[keyy - 1][keyx - 1][2], grid[keyy - 2][keyx - 1][2], grid[keyy - 1][keyx - 1][3])
                    
            row.append(hght)
            m = m + 1
        genmap.append(row)
        n = n + 1

    #print(str(grid[23][11][3]))

    print("grid generation finished")

    return genmap

if __name__ == "__main__":
    print("This isn't meant to be run by itself, it's imported into srmg_1.py")
    print("Too many inputs, really. Need to run srmg_1.py")
    #genmap = generate_map_using_paths(map_properties)
    #print(str(genmap))
    print("finished")
