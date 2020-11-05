from db import *
from shapely import geometry, wkt
from shapely.ops import polygonize, transform
from shapely.affinity import scale
from itertools import accumulate
import shapefile
import pygeoif
import math
import geojson
import os
import os.path
import shutil
import json


def shp2db(shp, tb, ep, cu):
    shpinput = shapefile.Reader(shp)
    for layer in shpinput.shapes():
        lot_geom = pygeoif.geometry.as_shape(layer)
        lot_shape = pygeoif.Polygon(lot_geom)
        lot_geom_wkt = lot_shape.wkt
        insert_wkt_table(tb_names=tb, epsg=ep, wkt=lot_geom_wkt, cursor=cu)


def cal_split(total_dist, dist_int):
    res_num = int((total_dist // dist_int))
    return res_num


def cal_dist(dx, dy):
    distance = math.sqrt(dx ** 2 + dy ** 2)
    return distance


def cal_inv_bearing(dx, dy):
    d_x = int(dx)
    d_y = int(dy)

    dx = math.radians(d_x)
    dy = math.radians(d_y)

    if dx >= 0:
        py_res = 90 - math.degrees(math.atan2(dy, dx))
        return py_res
    elif dx < 0:
        res = 270 - math.degrees(math.atan2(dy, dx))
        if res > 0 and res < 180:
            py_res = 180 + res
        else:
            py_res = abs(180 - res)
        return py_res


def cal_coor(x1, y1, bearing, distance):
    latitude = distance * math.cos(math.radians(bearing))
    departure = distance * math.sin(math.radians(bearing))
    x = x1 + departure
    y = y1 + latitude
    return (x, y)


def iter_coor(line_co1, line_br1, line_co2, line_br2, line_di, req_dist, req_list):
    sx = req_dist
    tolerance = sx
    while tolerance < line_di:
        l1_co = cal_coor(x1=int(line_co1[0]), y1=int(
            line_co1[1]), bearing=line_br1, distance=req_dist)
        l2_co = cal_coor(x1=int(line_co2[0]), y1=int(
            line_co2[1]), bearing=line_br2, distance=req_dist)
        line_cr = geometry.LineString([l1_co, l2_co])
        line_sc = scale(line_cr, 1.15, 1.15, 1.0)
        req_dist += sx
        tolerance += sx
        req_list.append(tuple(line_sc.coords))


def split_by_multi(line_co, list_split, list_geom):
    # Create empty list
    mts_length = []
    f_uns = []
    new_cut_poly = []

    # Split number of coordinate based on list and modified to multilinestring structure
    multi_line = [line_co[x - y: x]
                  for x, y in zip(accumulate(list_split), list_split)]

    # Create multilinestring
    for mul in multi_line:
        multi = geometry.MultiLineString(mul)
        mts_length.append(multi)

    # Union between lot mrr boundary and multilinestring
    for lt, mt in zip(list_geom, mts_length):
        ltmt = lt.union(mt)
        f_uns.append(ltmt)

    # Create new polygon from multilinestrin using polygonize
    for np in f_uns:
        pol = polygonize(np)
        for pl in pol:
            new_cut_poly.append(pl)

    return new_cut_poly


def intersect_list_geom(pr_lot, nw_lot):
    nw_int = []
    for kl in pr_lot:
        for ncp in nw_lot:
            if ncp.intersects(kl):
                res = ncp.intersection(kl)
                nw_int.append(res)
    return nw_int


# def project_geom(list_geom):
#     new_geom = []

#     crs_source = CRS("EPSG:3375")
#     crs_destination = CRS("EPSG:4326")
#     project = Transformer.from_crs(crs_source, crs_destination)

#     for ge in list_geom:
#         ge_transform = transform(project.transform, ge)
#         new_geom.append(ge_transform)

#     return(new_geom)


def swapCoords(x):
    out = []
    for iter in x:
        if isinstance(iter, list):
            out.append(swapCoords(iter))
        else:
            return [x[1], x[0]]
    return out


def list_to_tb(wkt_list, tb, ep, cu):
    for wk in wkt_list:
        insert_wkt_table(tb_names=tb, epsg=ep, wkt=wk, cursor=cu)


def list_to_wkt(rq_lot):
    ge_li = []
    for ge in rq_lot:
        ge_wkt = wkt.dumps(ge)
        ge_li.append(ge_wkt)
    return ge_li


def wkt_to_geojson(geom_wkt):
    wkt_load = wkt.loads(geom_wkt)
    g1 = geometry.mapping(wkt_load)
    g2 = geojson.Feature(type="Feature", geometry=g1, properties={})
    gj = geojson.dumps(g2)
    gj_load = geojson.loads(gj)
    return gj_load


def sub(res_fetch, len_dist, len_wid, maps=''):
    int(len_dist)
    int(len_wid)

    parent_lot = []
    list_mrr_line = []
    length_split = []
    width_split = []
    col_length = []
    col_width = []

    for geoms in res_fetch:
        geom = wkt.loads(geoms[0])
        poly = geometry.Polygon(geom)
        parent_lot.append(poly)

        # Create MRR
        mrr = poly.minimum_rotated_rectangle

        # Create line from MRR
        mrr_line = mrr.boundary
        list_mrr_line.append(mrr_line)

        # Defined coordinates for each line
        line_1 = mrr_line.coords[0]
        line_2 = mrr_line.coords[1]
        line_3 = mrr_line.coords[2]
        line_4 = mrr_line.coords[3]

        # Calculate distance and bearing for each line
        line1_dist = cal_dist(
            dx=(int(line_2[0]) - int(line_1[0])), dy=(int(line_2[1]) - int(line_1[1])))
        line1_brg = cal_inv_bearing(
            dx=(int(line_2[0]) - int(line_1[0])), dy=(int(line_2[1]) - int(line_1[1])))
        line2_dist = cal_dist(
            dx=(int(line_3[0]) - int(line_2[0])), dy=(int(line_3[1]) - int(line_2[1])))
        line2_brg = cal_inv_bearing(
            dx=(int(line_3[0]) - int(line_2[0])), dy=(int(line_3[1]) - int(line_2[1])))
        line3_dist = cal_dist(
            dx=(int(line_4[0]) - int(line_3[0])), dy=(int(line_4[1]) - int(line_3[1])))
        line3_brg = cal_inv_bearing(
            dx=(int(line_3[0]) - int(line_4[0])), dy=(int(line_3[1]) - int(line_4[1])))
        line4_dist = cal_dist(
            dx=(int(line_1[0]) - int(line_4[0])), dy=(int(line_1[1]) - int(line_4[1])))
        line4_brg = cal_inv_bearing(
            dx=(int(line_4[0]) - int(line_1[0])), dy=(int(line_4[1]) - int(line_1[1])))

        # Set length and width based on user inputted
        dist_l = len_wid
        dist_w = len_dist

        if line1_dist > line2_dist:
            # Calculate for length
            num_l = cal_split(line1_dist, dist_l)
            length_split.append(num_l)
            iter_coor(line_1, line1_brg, line_4, line3_brg,
                      line1_dist, dist_l, col_length)

            # Calculate for width
            num_w = cal_split(line2_dist, dist_w)
            width_split.append(num_w)
            iter_coor(line_2, line2_brg, line_1, line4_brg,
                      line2_dist, dist_w, col_width)

        elif line1_dist < line2_dist:
            # Calculate for length
            num_l = cal_split(line2_dist, dist_l)
            length_split.append(num_l)
            iter_coor(line_2, line2_brg, line_1, line4_brg,
                      line2_dist, dist_l, col_length)

            # Calculate for width
            num_w = cal_split(line1_dist, dist_w)
            width_split.append(num_w)
            iter_coor(line_1, line1_brg, line_4, line3_brg,
                      line1_dist, dist_w, col_width)

    # Subdivide the lot parcel
    new_lot_l = split_by_multi(col_length, length_split, list_mrr_line)
    new_lot_w = split_by_multi(col_width, width_split, list_mrr_line)

    new_lot = intersect_list_geom(new_lot_l, new_lot_w)

    # Intersect with parent lot
    new_lot_its = intersect_list_geom(parent_lot, new_lot)

    new_lot_int = list_to_wkt(new_lot_its)

    return new_lot_int


def create_gj(epsg):
    gj_res = {
        "type": "FeatureCollection",
        "features": [],
        "crs": {
            "type": "name",
            "properties": {
                "name": 'EPSG:' + epsg
            }
        }
    }

    return gj_res


def wkt2json(wkt_lot, gj_name):
    for cut_wk in wkt_lot:
        # Create geojson object
        cut_wk_wg = wkt_to_geojson(cut_wk)
        # Append geojson object
        gj_name["features"].append(cut_wk_wg)


def fetchtowkt(res_fetch):
    lists = []
    for geoms in res_fetch:
        geom = wkt.loads(geoms[0])
        poly = geometry.Polygon(geom)
        lists.append(poly)
    
    new_lot = list_to_wkt(lists)
    return new_lot
