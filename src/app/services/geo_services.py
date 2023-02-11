def pointNamer(lat, lon, exact=False):
    
    flat = abs(float(lat))
    flon = abs(float(lon))
    
    # These coords define a square around the FPV plant
    # UP: -25.5119 -49.36953, DOWN: -25.5123024 -49.3690549
    fpv = {
        "up-lat": -25.5119, 
        "down-lat": -25.5123024,
        "left-lon": -49.36953,
        "right-lon": -49.3690549
        }
    # These coords define a larger square around the FPV plant
    # UP: -25.51095 -49.3700, DOWN: -25.5135 -49.3685
    near = {
        "up-lat": -25.51095, 
        "down-lat": -25.5135,
        "left-lon": -49.3700,
        "right-lon": -49.3685
        }
    # These coords define a extra-larger square around the FPV plant
    # UP: -25.510 -49.3733, DOWN: -25.515 -49.3685
    far = {
        "up-lat": -25.510, 
        "down-lat": -25.515,
        "left-lon": -49.3733,
        "right-lon": -49.3685
        }
    # These coords define a square around point LR
    # UP: -25.51264 -49.36986, DOWN: -25.5128 -49.36968
    lr = {
        "up-lat": -25.51264, 
        "down-lat": -25.5128,
        "left-lon": -49.36986,
        "right-lon": -49.36968
        }
    # These coords define a square around point L1
    # UP: -25.5113 -49.3694, DOWN: -25.5118 -49.36915
    l1 = {
        "up-lat": -25.5113,
        "down-lat": -25.5118,
        "left-lon": -49.3694,
        "right-lon": -49.36915
        }
    # These coords define a square around point L2
    # UP: -25.5115 -49.36975, DOWN: -25.5117 -49.36948
    l2 = {
        "up-lat": -25.5115, 
        "down-lat": -25.5117,
        "left-lon": -49.36975,
        "right-lon": -49.36948
        }
    # These coords define a square around point L3
    # UP: -25.5119 -49.36992, DOWN: -25.5123 -49.3696
    l3 = {
        "up-lat": -25.5119, 
        "down-lat": -25.5123,
        "left-lon": -49.36992,
        "right-lon": -49.3696
        }
    # These coords define a square around point PV1
    # UP: -25.51201 -49.3694, DOWN: -25.51215 -49.3692
    pv1 = {
        "up-lat": -25.51201, 
        "down-lat": -25.51215,
        "left-lon": -49.3694,
        "right-lon": -49.3692
        }
    # These coords define a square around point PV6
    # UP: -25.51186 -49.36955, DOWN: -25.51201 -49.36915
    pv6 = {
        "up-lat": -25.51186, 
        "down-lat": -25.51201,
        "left-lon": -49.36955,
        "right-lon": -49.36915
        }
    # These coords define a square around point PV7
    # UP: -25.51217 -49.36958, DOWN: -25.51229 -49.36942
    pv7 = {
        "up-lat": -25.51217, 
        "down-lat": -25.51229,
        "left-lon": -49.36958,
        "right-lon": -49.36942
        }

    cross_section_lat = -25.5121
    names = ['PV1', 'PV6', 'PV7', 'LR', 'L1', 'L2', 'L3', 'FPV', 'NEAR', 'FAR']
    pipe = [pv1, pv6, pv7, lr, l1, l2, l3, fpv, near, far]
    name_found = False
    for i in range(len(pipe)):
        up = abs(pipe[i]["up-lat"])
        down = abs(pipe[i]["down-lat"])
        left = abs(pipe[i]["left-lon"])
        right = abs(pipe[i]["right-lon"])
        if flat >= up and flat <= down and flon >= right and flon <= left:
            ptname = names[i]
            if ptname == 'NEAR' or ptname == 'FAR':
                if flat <= abs(cross_section_lat):
                    name_found = True
                    return f'{ptname}_UP'
                else:
                    name_found = True
                    return f'{ptname}_DOWN'
            else:
                name_found = True
                return ptname

    if not name_found and flat < abs(cross_section_lat):
        return 'VERY_FAR_UP'
    else:
        return 'VERY_FAR_DOWN'


    
