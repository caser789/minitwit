import os
from flask import Flask, _app_ctx_stack
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




if __name__ == '__main__':
    app.run(debug=True)
