import os
from flask import Flask, _app_ctx_stack
from flask import redirect, url_for, flash, render_template
from flask import request, session, g
from sqlite3 import dbapi2 as sqlite3
from werkzeug import generate_password_hash, check_password_hash

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

@app.teardown_appcontext
def close_database(exception):
    """close the database again at the end of the request"""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()

def init_db():
    """initialize the db"""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Create the database tables"""
    init_db()
    print "Initialized the database"

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
                        generate_password_hash(str(request.form['password']))
                    ])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?', 
                          [session['user_id']], one=True)


def get_user_id(username):
    """convenience method to lookup the id for a username"""
    rv = query_db('select user_id from user where username = ?',
                  [username], one=True)
    return rv[0] if rv else None

def query_db(query, args=(), one=False):
    """Queries the db and return a list of dict"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in"""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where username = ?''',
                        [request.form['username']],
                        one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['user_id'],
                str(request.form['password'])):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)

@app.route('/public')
def public_timeline():
    """Displays the latest messages for all users"""
    template = 'timeline.html'
    messages = query_db("""
    select message.*, user.* from message, user
    where message.author_id = user.user_id
    order by message.pub_date desc limit ?
            """, [app.config['PER_PAGE']])
    return render_template(template, messages=messages)

@app.route('/<username>')
def user_timeline(username):
    """Display a user's tweets"""
    profile_user = query_db("""
    select * from user where username = ?
            """,
            [username],
            one=True)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db("""
        select 1 from follower where 
        follower.who_id = ? and follower.whom_id = ?
                """,
                [session['user_id'], profile_user['user_id']],
                one=True) is not None
    template = 'timeline.html'
    messages = query_db("""
    select message.*, user.* from message, user where
    user.user_id = message.author_id and user.user_id = ?
    order by message.pub_date desc limit ?
            """,
            [profile_user['user_id'], app.config['PER_PAGE']])
    return render_template(template, messages=messages, followed=followed,
            profile_user=profile_user)

@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user"""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute("""
    insert into follower (who_id, whom_id) values (?, ?)
            """,
            [session['user_id'], whom_id])
    db.commit()
    flash("You are now following '%s'" % username)
    return redirect(url_for('user_timeline', username=username))

@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Remove the current user as follower of the given user"""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    db = get_db()
    db.execute("""
    delete from follower where who_id = ? and whom_id = ?
            """,
            [session['user_id'], whom_id])
    db.commit()
    flash("You are no longer following '%s'" % username)
    return redirect(url_for('user_timeline', username=username))


def format_datetime(timestamp):
    """Format a timestamp for display"""
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d @ %H:%M")

def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address"""
    return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % \
            (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)

@app.route('/')
def timeline():
    """Shows a users timeline of if no user is logged in it will
    redirect to the public timeline. This timeline shows the user's
    messages as well as the messages of followed users.
    """
    if not g.user:
        return redirect(url_for('public_timeline'))
    template = 'timeline.html'
    messages = query_db("""
    select message.*, user.* from message, user
    where message.author_id = user.user_id and (
    user.user_id = ? or
    user.user_id in (select whom_id from follower 
    where who_id = ?))
    order by message.pub_date desc limit ?
            """,
            [session['user_id'], session['user_id'], PER_PAGE])
    return render_template(template, messages=messages)

app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    app.run(debug=True)
