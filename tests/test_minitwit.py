# coding: utf-8
"""
    MiniTwit Tests
"""
import os
import pytest
import tempfile
from context import minitwit, logging

@pytest.fixture
def client(request):
    db_fd, minitwit.app.config['DATABASE'] = tempfile.mkstemp()
    client = minitwit.app.test_client()
    with minitwit.app.app_context():
        minitwit.init_db()

    def teardown():
        """Close db after each test"""
        os.close(db_fd)
        os.unlink(minitwit.app.config['DATABASE'])

    request.addfinalizer(teardown)
    return client

def register(client, username, password, password2=None, email=None):
    """helper function to register user"""
    password2 = password if password2 is None else password2
    email = '{}@example.com'.format(username) if email is None else email
    url = '/register'
    data = dict(username=username, password=password,
            password2=password2, email=email)
    return client.post(url, data=data, follow_redirects=True)

def login(client, username, password):
    """helper function to login"""
    url = '/login'
    data = dict(username=username, password=password)
    return client.post(url, data=data, follow_redirects=True)

def register_and_login(client, username, password):
    """register and login in one go"""
    register(client, username, password)
    return login(client, username, password)

def logout(client):
    """helper function to logout user"""
    url = '/logout'
    return client.post(url, follow_redirects=True)

def test_register(client):
    """make sure registering works"""
    rv = register(client, 'user1', 'default')
    assert b'You were successfully registered and can login now' in rv.data
    rv = register(client, 'user1', 'default')
    assert b'The username is already taken' in rv.data
    rv = register(client, '', 'default')
    assert b'You have to enter an username' in rv.data
    rv = register(client, 'meh', '')
    assert b'You have to enter a password' in rv.data
    rv = register(client, 'meh', 'x', 'y')
    assert b'The two passwords do not match' in rv.data
    rv = register(client, 'meh', 'foo', email='broken')
    assert b'You have to enter a valid email address' in rv.data


if __name__ == '__main__':
    pytest.main()






