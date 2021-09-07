#!/usr/bin/env python

from PIL import Image
import re
import os
import uuid
from flask import Flask, abort, request, jsonify, make_response, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
import flask
import pymongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask_httpauth import HTTPBasicAuth


myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient['db']
app = Flask(__name__)
auth = HTTPBasicAuth()
app.config['UPLOAD_FOLDER'] = './uploads/'


def random_filename():
    return str(uuid.uuid4())

@auth.verify_password
def get_password(username, password):
    if username == 'xyguo' and password == 'xyguo':
        return 'xyguo'
    elif username == "rui" and password == 'rui':
        return 'rui'
    return None

@auth.error_handler
def unauthorized(error):
    return jsonify({'error': 'Unauthorized access'}), 401

@app.errorhandler(400)
def handle_invalid_keys(error):
    return jsonify({'error': str(error)}), 400

def str2date(s):
    if s:
        return datetime.strptime(s, '%Y%m%d%H%M%S')
    else:
        return None

# @app.errorhandler(Exception)
# def handle_exception(e):
#     if isinstance(e, HTTPException):
#         return e
#     return jsonify({'error': str(e)}), 500

def check_json_keys(obj, keys, description='notdefined'):
    if not obj:
        print('None obj')
        abort(400, description="{} is None object".format(description))
    print('checking keys', keys, obj.keys())
    for k in keys:
        if k not in obj:
            print('no key', k)
            abort(400, description="There is no {} in {}".format(k, description))


@app.route('/', methods=['GET'])
@auth.login_required
def index():
    return "Hello, {}".format(auth.username())


# @app.route('/api/v1.0/msg', methods=['POST'])
# @auth.login_required
# def new_msg():
#     check_json_keys(request.json, ['msg'], "msgrequest")
#     msg = {
#         'time': datetime.now(),
#         'msg': request.json['msg'],
#         'user': request.json.get("user", "nobody")
#     }
#     msgs_db = mydb.msgs
#     inserted_id = msgs_db.insert_one(msg.copy()).inserted_id
#     num_msg = msgs_db.find().count()
#     return jsonify({'result': 'success', '_id': str(inserted_id), 'data': msg, 'num_msg': num_msg})
# 
# 
# @app.route('/api/v1.0/msg', methods=['GET'])
# @auth.login_required
# def get_msg():
#     msgs_db = mydb.msgs
#     msgs = []
#     for msg in msgs_db.find():
#         del msg['_id']
#         msgs.append(msg)
#     print('msgs', msgs)
#     return jsonify({"data": msgs})

@app.route('/api/v1.0/db', methods=['DELETE'])
@auth.login_required
def drop_db():
    mydb.drop_collection('foods')
    mydb.foods.drop()
    return jsonify({'result': 'success'})


@app.route('/api/v1.0/dbclean', methods=['POST'])
@auth.login_required
def clean_db():
    query = { "$or": [{"name": re.compile("^(debug|测试)") }, {"useddate": {"$exists": False}}], "used": True}
    result = mydb.foods.delete_many(query)
    return jsonify({'result': 'success', 'deleted_count': result.deleted_count})

@app.route('/api/v1.0/food', methods=['POST'])
@auth.login_required
def new_food():
    check_json_keys(request.json, ['foods'], 'foodrequest')
    print(request.json)
    foods = []
    for idx, item in enumerate(request.json['foods']):
        check_json_keys(item, ['used', 'name', 'createdate', 'expiredate', 'type', 'imagename', 'createby'], 'fooditem-{}'.format(idx))
        foods.append(dict(
            name=item['name'],
            type=item['type'],
            createdate=str2date(item['createdate']),
            expiredate=str2date(item['expiredate']),
            useddate=str2date(item['useddate']) if 'useddate' in item else None,
            imagename=item['imagename'] if item['imagename'] else '',
            createby=item['createby'],
            used=item['used']
        ))
    foods_db = mydb.foods
    inserted_ids = foods_db.insert_many([x.copy() for x in foods]).inserted_ids
    inserted_ids = [str(x) for x in inserted_ids]
    num_food = foods_db.find().count()
    print('return', {'result': 'success', '_id': inserted_ids, 'data': foods, 'num_food': num_food})
    return jsonify({'result': 'success', '_id': inserted_ids, 'data': foods, 'num_food': num_food})

@app.route('/api/v1.0/food', methods=['PUT'])
@auth.login_required
def update_food():
    check_json_keys(request.json, ['foods'], 'foodrequest')
    print(request.json)
    foods = []
    for idx, item in enumerate(request.json['foods']):
        check_json_keys(item, ['_id', 'name', 'createdate', 'expiredate', 'type', 'imagename', 'createby', 'used'], 'fooditem-{}'.format(idx))
        foods.append(dict(
            _id=ObjectId(item['_id']),
            name=item['name'],
            type=item['type'],
            createdate=str2date(item['createdate']),
            expiredate=str2date(item['expiredate']),
            useddate=str2date(item['useddate']) if 'useddate' in item else None,
            imagename=item['imagename'] if item['imagename'] else '',
            createby=item['createby'],
            used=item['used']
        ))
    foods_db = mydb.foods
    updates = []
    for food in foods:
        ret = foods_db.replace_one({'_id': food['_id']}, food, True)
        updates.append(dict(matched_count=ret.matched_count, modified_count=ret.modified_count))
    num_food = foods_db.find().count()
    for food in foods:
        food['_id'] = str(food['_id'])
    return jsonify({'result': 'success', 'ret': updates, 'data': foods, 'num_food': num_food})




@app.route('/api/v1.0/food', methods=['GET'])
@auth.login_required
def get_food():
    foods_db = mydb.foods
    foods = []
    for food in foods_db.find():
        foods.append(dict(
            _id=str(food['_id']),
            name=food['name'],
            type=food['type'],
            createdate=food['createdate'].strftime("%Y%m%d%H%M%S"),
            expiredate=food['expiredate'].strftime("%Y%m%d%H%M%S"),
            useddate=food['useddate'].strftime("%Y%m%d%H%M%S") if 'useddate' in food and food['useddate'] is not None else None,
            createby=food['createby'],
            imagename=food['imagename'],
            used=food['used']
        ))
    foods = sorted(foods, key=lambda x: x['expiredate'])
    return jsonify({"data": foods})


@app.route('/api/v1.0/food', methods=['DELETE'])
@auth.login_required
def delete_food():
    check_json_keys(request.json, ['_id'], 'foodrequest')
    ids = request.json['_id']
    print('delete these ids', ids)
    assert isinstance(ids, list)
    query = {"_id": {"$in": [ObjectId(x) for x in ids]}}
    result = mydb.foods.delete_many(query)
    return jsonify({'result': 'success', 'deleted_count': result.deleted_count, 'failed_count': len(ids) - result.deleted_count})


@app.route('/api/v1.0/file', methods=['POST'])
@auth.login_required
def upload_file():
    if 'file' not in request.files:
        abort(400, description="no file parte specified")
    filenames = []
    for file in request.files.getlist('file'):
        if file.filename == '' or '.' not in file.filename:
            abort(400, description="filename invalid: {}".format(file.filename))
        if not file:
            abort(400, description="file invalid: {}".format(file))

        filename = random_filename() + "." + file.filename.split('.')[-1]
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        filenames.append(filename) 
    return jsonify({'result': 'success', 'filenames': filenames})


@app.route('/api/v1.0/image', methods=['POST'])
@auth.login_required
def upload_image():
    if 'file' not in request.files:
        abort(400, description="no file parte specified")
    filenames = []
    for file in request.files.getlist('file'):
        if file.filename == '' or '.' not in file.filename:
            abort(400, description="filename invalid: {}".format(file.filename))
        if not file:
            abort(400, description="file invalid: {}".format(file))
        ext = file.filename.split('.')[-1].lower()
        if ext not in ['jpg', 'png']:
            abort(400, description="file invalid ext: {}".format(file.filename))

        uuid = random_filename()
        filename = uuid + "." + ext
        filename_resized = uuid + '-96x96' + "." + ext
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        with Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as im:
            im_resized = im.resize((96, 96))
            im_resized.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_resized))
        filenames.append(filename_resized) 
    return jsonify({'result': 'success', 'filenames': filenames})

@app.route("/api/v1.0/file/<filename>", methods = ['GET'])
def download_file(filename):
    print('sending', filename)
    if '.' not in filename:
        filename = filename + '.jpg'
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/api/v1.0/expireinfo', methods=['POST'])
@auth.login_required
def new_expire_info():
    check_json_keys(request.json, ['expireinfos'], 'expireinforequest')
    print(request.json)
    infos = []
    for idx, item in enumerate(request.json['expireinfos']):
        check_json_keys(item, ['name', 'type', 'expireduration'], 'fooditem-{}'.format(idx))
        infos.append(dict(
            name=item['name'],
            type=item['type'],
            expireduration=item['expireduration']
        ))
    expireinfo_db = mydb.expireinfos
    inserted_ids = expireinfo_db.insert_many([x.copy() for x in infos]).inserted_ids
    inserted_ids = [str(x) for x in inserted_ids]
    num_infos = expireinfo_db.find().count()
    print('return', {'result': 'success', '_id': inserted_ids, 'data': infos, 'num_food': num_infos})
    return jsonify({'result': 'success', '_id': inserted_ids, 'data': infos, 'num_food': num_infos})

@app.route('/api/v1.0/expireinfo', methods=['GET'])
@auth.login_required
def get_expire_info():
    expireinfo_db = mydb.expireinfos
    expireinfos = []
    for info in expireinfo_db.find():
        expireinfos.append(dict(
            name=info['name'],
            type=info['type'],
            expireduration=info['expireduration'],
        ))
    return jsonify({"data": expireinfos})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2333, debug=False)

