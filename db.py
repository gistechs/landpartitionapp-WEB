from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2
import psycopg2.extras


def create_con(users, passwords, hosts, ports, db=''):
    if db:
        connection = psycopg2.connect(user=users,
                                      password=passwords,
                                      host=hosts,
                                      port=ports,
                                      database=db)
    else:
        connection = psycopg2.connect(user=users,
                                      password=passwords,
                                      host=hosts,
                                      port=ports)

    return connection


def set_isolation(connection):
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)


def create_cur(connection):
    cursor = connection.cursor()
    return cursor


def close_cur(cursor):
    cursor.close()


def close_con(connection):
    connection.close()


def enabled_postgis(cursor):
    cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")


def create_table(tb_names, srid, cursor):
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
        sql.Identifier(tb_names)))
    cursor.execute(sql.SQL("""CREATE TABLE {}(
                            id SERIAL,
                            PRIMARY KEY (id))
                    """).format(sql.Identifier(tb_names)))
    cursor.execute(
        "SELECT AddGeometryColumn(%s, 'geom', %s, 'POLYGON', 2)", [tb_names, srid])


def insert_wkt_table(tb_names, wkt, epsg, cursor):
    cursor.execute(sql.SQL("INSERT INTO {} (geom) VALUES (ST_SetSRID(ST_GeomFromText(%s), %s))").format(
        sql.Identifier(tb_names)), (wkt, epsg))


def sym_diff(tb_res, tb_names1, tb_names2, cursor):
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
        sql.Identifier(tb_res)))
    cursor.execute(sql.SQL("CREATE TABLE {} AS SELECT ST_Difference({}.geom, {}.geom) AS geom FROM {}, {}").format(sql.Identifier(
        tb_res), sql.Identifier(tb_names1), sql.Identifier(tb_names2), sql.Identifier(tb_names1), sql.Identifier(tb_names2)))


def dump_poly(tb_res, tb_names, cursor):
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
        sql.Identifier(tb_res)))
    cursor.execute(sql.SQL("CREATE TABLE {} AS SELECT (ST_Dump({}.geom)).geom AS geom FROM {}").format(
        sql.Identifier(tb_res), sql.Identifier(tb_names), sql.Identifier(tb_names)))


def fetch_geom(tb_names, cursor):
    cursor.execute(sql.SQL("SELECT ST_AsText({}.geom) FROM {}").format(
        sql.Identifier(tb_names), sql.Identifier(tb_names)))
    res_fetch = cursor.fetchall()
    return res_fetch


def create_tbl(tb_names, cursor):
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
        sql.Identifier(tb_names)))
    cursor.execute(sql.SQL("""CREATE TABLE {}(
                                lay_id SERIAL,
                                PRIMARY KEY (lay_id),
                                length DOUBLE PRECISION,
                                width DOUBLE PRECISION,
                                lay VARCHAR(100))
                        """).format(sql.Identifier(tb_names)))


def insert_tbl(tb_names, leng, widt, ly, cursor):
    cursor.execute(sql.SQL("INSERT INTO {} (length, width, lay) VALUES (%s, %s, %s)").format(
        sql.Identifier(tb_names)), [leng, widt, ly])


def fetch_tb(tb_names, cursor):
    cursor.execute(
        sql.SQL("SELECT * FROM {}").format(sql.Identifier(tb_names)))
    return cursor.fetchall()


def insert_wgs(tb_names, epsg, tb_dir, cursor):
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
        sql.Identifier(tb_names)))
    cursor.execute(sql.SQL(
        "CREATE TABLE {}(geom) AS SELECT ST_SetSRID(ST_Transform(ST_SetSRID(geom, %s), 4326), 4326) FROM {}").format(sql.Identifier(tb_names), sql.Identifier(tb_dir)), [epsg])
