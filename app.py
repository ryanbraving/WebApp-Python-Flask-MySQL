from flask import Flask, render_template, json, request, redirect, session, jsonify, url_for
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
# from werkzeug.wsgi import LimitedStream
import uuid
import os

mysql = MySQL()
app = Flask(__name__)

# set a secret key for the session
app.secret_key = 'why would I tell you my secret key?'

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'ryan'
app.config['MYSQL_DATABASE_DB'] = 'BucketList'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# Default setting
pageLimit = 5
app.config['UPLOAD_FOLDER'] = 'static/Uploads'


@app.route("/")
def main():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            print('No file part')
            return "No file"
        file = request.files['file']
        extension = os.path.splitext(file.filename)[1]

        f_name = str(uuid.uuid4()) + extension
        print(f_name)
        print(os.path)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_name))
        return json.dumps({'filename': f_name})


@app.route('/showSignin')
def showSignin():
    return render_template('signin.html')


@app.route('/userHome')
def userHome():
    if session.get('user'):
        return render_template('userHome.html')
    else:
        return render_template('error.html', error='Unauthorized Access')


@app.route('/logout')
def logout():
    print(session)
    session.pop('user', None)
    print(session)
    return redirect('/')


@app.route('/showSignup')
def showSignUp():
    return render_template('signup.html')


@app.route('/showAddWish')
def showAddWish():
    return render_template('addWish.html')


@app.route('/signUp', methods=['POST'])
def signUp():
    try:

        # read the posted values from the UI
        _name = request.form['inputName']
        _email = request.form['inputEmail']
        _password = request.form['inputPassword']

        # validate the received values
        if _name and _email and _password:
             # All Good, let's call MySQL
            conn = mysql.connect()
            cursor = conn.cursor()
            _hashed_password = generate_password_hash(_password)
            cursor.callproc('sp_createUser', (_name, _email, _hashed_password))
            data = cursor.fetchall()
            print(data)
            if len(data) is 0:
                conn.commit()
                return json.dumps({'message': 'User created successfully !'})
            else:
                return json.dumps({'error': str(data[0])})

        else:
            return json.dumps({'html': '<span>Enter the required fields</span>'})

    except Exception as e:
        return json.dumps({'error': str(e)})
    finally:
        cursor.close()
        conn.close()


@app.route('/validateLogin', methods=['POST'])
def validateLogin():
    try:
        # read the posted values from the UI
        _username = request.form['inputEmail']
        _password = request.form['inputPassword']

        # validate the received values
        # if _username and _password:
        # All Good, let's call MySQL
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.callproc('sp_validateLogin', (_username,))
        data = cursor.fetchall()
        if len(data) > 0:
            if check_password_hash(str(data[0][3]), _password):
                session['user'] = data[0][0]
                return redirect('/userHome')
            else:
                return render_template('error.html', error='Wrong Email address or Password.')
        else:
            return render_template('error.html', error='Wrong Email address or Password.')

    except Exception as e:
        return render_template('error.html', error=str(e))

    finally:
        cursor.close()
        conn.close()


@app.route('/addWish', methods=['POST'])
def addWish():
    try:
        if session.get('user'):
            _title = request.form['inputTitle']
            _description = request.form['inputDescription']
            _user = session.get('user')
            if request.form.get('filePath') is None:
                _filePath = ''
            else:
                _filePath = request.form.get('filePath')

            if request.form.get('private') is None:
                _private = 0
            else:
                _private = 1

            if request.form.get('done') is None:
                _done = 0
            else:
                _done = 1

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_addWish', (_title, _description, _user, _filePath,_private,_done))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return redirect('/userHome')
            else:
                return render_template('error.html', error='An error occurred!')

        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        conn.close()


@app.route('/getWish', methods=['POST'])
def getWish():
    try:
        if session.get('user'):
            _user = session.get('user')
            _limit = pageLimit
            _offset = request.form['offset']
            _total_records = 0

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_GetWishByUser',
                            (_user, _limit, _offset, _total_records))
            wishes = cursor.fetchall()

            cursor.close()
            cursor = conn.cursor()
            cursor.execute('SELECT @_sp_GetWishByUser_3')
            outParam = cursor.fetchall()
            response = []
            wishes_dict = []
            for wish in wishes:
                wish_dict = {
                    'Id': wish[0],
                    'Title': wish[1],
                    'Description': wish[2],
                    'User': wish[3],
                    'Date': wish[4],
                    'FilePath': wish[5],
                    'Private': wish[6],
                    'Done': wish[7]
                    }
                wishes_dict.append(wish_dict)

            response.append(wishes_dict)
            response.append({'total': outParam[0][0]})

            return json.dumps(response)
        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        conn.close()


@app.route('/updateWish', methods=['POST'])
def updateWish():
    
    try:
        if session.get('user'):
            _id = request.form['inputWishId']
            _title = request.form['inputTitle']
            _description = request.form['inputDescription']
            _user = session.get('user')
            _userWish = request.form['inputUserId']
            _filePath = request.form['filePath']
            _private = request.form.get('private')
            _done = request.form.get('done')
            if _private == 'on':
                _private = 1
            else:
                _private = 0
                
            if _done == 'on':
                _done = 1
            else:
                _done = 0

            if(str(_user) == _userWish):

                conn = mysql.connect()
                cursor = conn.cursor()
                cursor.callproc('sp_updateWish',
                                (_title,_description,_id,_user,_filePath,_private,_done))
                data = cursor.fetchall()

                if len(data) is 0:
                    conn.commit()
                    return redirect('/userHome')
                else:
                    return render_template('error.html', error='An error occurred!')
            else:
                return render_template('error.html', error='User is not the doc owner!')
        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        conn.close()


@app.route('/deleteWish', methods=['POST'])
def deleteWish():
    try:
        if session.get('user'):
            _id = request.form['inputWishId']
            _user = session.get('user')
            _userWish = request.form['inputUserId']

            if (str(_user) == _userWish):
                conn = mysql.connect()
                cursor = conn.cursor()
                cursor.callproc('sp_deleteWish', (_id, _user))
                data = cursor.fetchall()

                if len(data) is 0:
                    conn.commit()
                    return redirect('/userHome')
                else:
                    return render_template('error.html', error='An error occurred!')
            else:
                return render_template('error.html', error='User is not the doc owner!')
        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(host='0.0.0.0')
