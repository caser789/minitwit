import os
from flask import Flask, _app_ctx_stack
from flask import redirect, url_for, g
from flask import request
from sqlite3 import dbapi2 as sqlite3

app = Flask(__name__)
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, '/tmp/minitwit.db'),
    DEBUG=True,
    SECRET_KEY='xuejiao',
    PER_PAGE=30,
    ))
# app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)

def get_db():
    """open a new db connection if no one for current app context"""
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db

def init_db():
    """initialize the db"""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.route('/register', methods=['GET', 'POST'])
def register():
    """register the user"""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute("""insert into user (username, email, pw_hash) values (?,?,?)""",
                    [
                        request.form['username'],
                        request.form['email'], 
                        generate_password_hash(request.form['password'])
                    ])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)






if __name__ == '__main__':
    app.run(debug=True)
