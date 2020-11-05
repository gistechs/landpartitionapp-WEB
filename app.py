from flask import Flask, render_template, redirect, request, url_for, flash, current_app, send_from_directory, abort
from werkzeug.utils import secure_filename
from db import *
from sub import *
from shapely import geometry
import os
import zipfile

app = Flask(__name__)
app.config.from_object("config.ProductionConfig")

# Define variable
pr_data = "pr.zip"
rs_data = "ra.zip"
table_1 = "parent_lot"
table_2 = "reserve_lot"
table_res = "diff_res"
table_dump = "diff_dump"
table_lay = "layout"
table_final = "sub_lot"
fileo = 'final_output.json'
table_wgs = "wgs_lot"

basedir = os.path.abspath(os.path.dirname(__file__))


def insert_lay(leng, wid, val):
    layt = {
        "length": float(leng),
        "width": float(wid),
        "value": val
    }
    return layt


def create_lay(fet):
    lys = []
    for i in fet:
        ls = insert_lay(i[1], i[2], i[3])
        lys.append(ls)
    return lys


def feet_to_meter(value):
    num = int(value) * 0.3048
    res = round(num, 3)
    return res


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower(
           ) in app.config['ALLOWED_EXTENSIONS']


@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/guidelines")
def guide():
    return render_template("guide.html")


@app.route("/partition")
def partition():
    con = create_con(users='tpbrfmnlwyofoz', passwords='6efd3600455f60b581a7df4eadfe3b98178b5926f6fe27e0734cbbd148c49f5c',
                     hosts='ec2-35-172-73-125.compute-1.amazonaws.com', ports='5432', db='ddm5k5irinsntc')

    for fileop in os.listdir(os.path.join(basedir, app.config['UPLOAD_FOLDER'])):
        if fileop == 'final_output.json':
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], fileop))

    set_isolation(con)
    cur = create_cur(con)
    test = fetch_tb(table_lay, cur)
    trys = create_lay(test)
    con.commit()
    close_cur(cur)
    close_con(con)
    return render_template("partition.html", trys=trys)


@app.route("/form", methods=['GET', 'POST'])
def forms():
    if request.method == 'POST':
        strepsg = request.form.get('epsg')
        intepsg = int(strepsg)

        # Create connection
        con = create_con(users='tpbrfmnlwyofoz', passwords='6efd3600455f60b581a7df4eadfe3b98178b5926f6fe27e0734cbbd148c49f5c',
                         hosts='ec2-35-172-73-125.compute-1.amazonaws.com', ports='5432', db='ddm5k5irinsntc')

        # con = create_con(users='postgres', passwords='123456',
        #                 hosts='localhost', ports='5432', db='update')

        cur = create_cur(con)
        set_isolation(con)

        # Create table
        create_table(tb_names=table_1, srid=intepsg, cursor=cur)
        create_table(tb_names=table_2, srid=intepsg, cursor=cur)
        create_table(tb_names=table_final, srid=intepsg, cursor=cur)

        lay = request.form.get('layout')
        test = fetch_tb(table_lay, cur)
        trys = create_lay(test)
        for i in trys:
            if i['value'] == lay:
                lay_length = i['length']
                lay_width = i['width']

        # check if the post request has the file part
        if 'file1' not in request.files:
            flash('No file part!!', 'danger')
            return redirect(request.url)

        if 'file2' not in request.files:
            flash('No file part!!', 'danger')
            return redirect(request.url)

        file1 = request.files['file1']
        file2 = request.files['file2']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file1.filename == '':
            flash('No selected file!!', 'danger')
            return redirect(request.url)
        if file2.filename == '':
            flash('No selected file!!', 'danger')
            return redirect(request.url)

        if file1 and allowed_file(file1.filename):
            filename1 = secure_filename(file1.filename)
            file1.save(os.path.join(
                basedir, app.config['UPLOAD_FOLDER_PR'], filename1))

            with current_app.open_resource('static/shp/upload_pr/{}'.format(filename1)) as f:
                with zipfile.ZipFile(f, "r") as data_zip:
                    data_zip.extractall(app.config['UPLOAD_FOLDER_PR'])
                    os.remove(os.path.join(basedir,
                                           app.config['UPLOAD_FOLDER_PR'], filename1))

            for filesp in os.listdir(os.path.join(basedir, app.config['UPLOAD_FOLDER_PR'])):
                if filesp.endswith(".shp"):
                    parentlot = os.path.join(
                        app.config['UPLOAD_FOLDER_PR'], filesp)

        else:
            flash('Invalid file extension !!', 'danger')
            return redirect(request.url)

        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(
                basedir, app.config['UPLOAD_FOLDER_RZ'], filename2))

            with current_app.open_resource('static/shp/upload_rz/{}'.format(filename2)) as f:
                with zipfile.ZipFile(f, "r") as data_zip:
                    data_zip.extractall(app.config['UPLOAD_FOLDER_RZ'])
                    os.remove(os.path.join(basedir,
                                           app.config['UPLOAD_FOLDER_RZ'], filename2))

            for filesr in os.listdir(os.path.join(basedir, app.config['UPLOAD_FOLDER_RZ'])):
                if filesr.endswith(".shp"):
                    reservelot = os.path.join(
                        app.config['UPLOAD_FOLDER_RZ'], filesr)

            gj_map = create_gj(epsg='4326')
            gj_output = create_gj(epsg=strepsg)

            shp2db(parentlot, tb=table_1, ep=intepsg, cu=cur)
            shp2db(reservelot, tb=table_2, ep=intepsg, cu=cur)

            sym_diff(tb_res=table_res, tb_names1=table_1,
                     tb_names2=table_2, cursor=cur)
            dump_poly(tb_res=table_dump, tb_names=table_res, cursor=cur)

            res_geom = fetch_geom(tb_names=table_dump, cursor=cur)

            list_wko = sub(res_geom, lay_length, lay_width)

            list_to_tb(list_wko, table_final, ep=intepsg, cu=cur)

            insert_wgs(table_wgs, intepsg, table_final, cur)

            res_wgs = fetch_geom(table_wgs, cur)

            list_wk = fetchtowkt(res_wgs)

            wkt2json(list_wk, gj_map)
            wkt2json(list_wko, gj_output)

            # for feature in gj_map['features']:
            #     feature['geometry']['coordinates'] = swapCoords(
            #         feature['geometry']['coordinates'])

            con.commit()
            close_cur(cur)
            close_con(con)

            for filesp in os.listdir(os.path.join(basedir, app.config['UPLOAD_FOLDER_PR'])):
                if filesp != '.keep':
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER_PR'], filesp))

            for filesr in os.listdir(os.path.join(basedir, app.config['UPLOAD_FOLDER_RZ'])):
                if filesr != '.keep':
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER_RZ'], filesr))
                    
            with open(os.path.join(basedir, app.config['UPLOAD_FOLDER'], fileo), 'w') as f:
                json.dump(gj_output, f)

            disp_json = gj_map["features"]

        else:
            flash('Invalid file extension !!', 'danger')
            return redirect(request.url)

        # return render_template("partition.html", disp_json=disp_json)
        return render_template("partition.html", disp_json=disp_json)

    return redirect(url_for('partition'))


@app.route("/create-layout")
def create_layout():
    return render_template("create_layout.html")


@app.route("/save-layout", methods=['GET', 'POST'])
def save_layout():
    if request.method == 'POST':
        # Create connection
        con = create_con(users='tpbrfmnlwyofoz', passwords='6efd3600455f60b581a7df4eadfe3b98178b5926f6fe27e0734cbbd148c49f5c',
                         hosts='ec2-35-172-73-125.compute-1.amazonaws.com', ports='5432', db='ddm5k5irinsntc')

        # con = create_con(users='postgres', passwords='123456',
        #         hosts='localhost', ports='5432', db='update')

        set_isolation(con)
        cur = create_cur(con)
        query = cur.execute(
            "SELECT EXISTS(SELECT relname FROM pg_class WHERE relname= %s)", [table_lay])
        res = cur.fetchone()
        if res[0] == False:
            create_tbl(table_lay, cur)
        lengthf = request.form.get('length')
        widthf = request.form.get('width')
        length = feet_to_meter(lengthf)
        width = feet_to_meter(widthf)
        lays = widthf + 'x' + lengthf
        insert_tbl('layout', length, width, lays, cur)
        con.commit()
        close_cur(cur)
        close_con(con)
        return redirect(url_for('partition'))


@app.route("/get-sample-pr/")
def get_sample_pr():
    try:
        return send_from_directory(
            app.config["SAMPLE_FOLDER"], filename=pr_data, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route("/get-sample-rs/")
def get_sample_rs():
    try:
        return send_from_directory(
            app.config["SAMPLE_FOLDER"], filename=rs_data, as_attachment=True)
    except FileNotFoundError:
        abort(404)


@app.route("/get-output/")
def get_output():
    try:
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], filename=fileo, as_attachment=True)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run()
