import json
from flask import Flask, g, url_for, render_template
from flask import request, redirect, flash, jsonify
from sqlalchemy import create_engine
from flask import session as login_session
from db_setup import BASE, User, Item, Category
from db_command import *
import random
import string
import pdb
import requests
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

from flask_httpauth import HTTPBasicAuth
from flask import make_response

import logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')


import os
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
secrets_url = os.path.join(PROJECT_ROOT, 'secrets.json')


DB_CONNECTION_STR =  (
        json.loads(
            open(secrets_url, 'r')
            .read())['db_conn_str']
    )


SUPER_SECRET_KEY = (
        json.loads(
            open(secrets_url, 'r')
            .read())['super_secret_key']
    )

client_secrets_url = os.path.join(PROJECT_ROOT, 'client_secrets.json')
GOOG_CLIENT_ID = (
        json.loads(
            open(client_secrets_url, 'r')
            .read())['web']['client_id']
    )
logging.debug( 'client secret url' + str(client_secrets_url))
auth = HTTPBasicAuth()


app = Flask(__name__)
app.secret_key = SUPER_SECRET_KEY
engine = create_engine('sqlite:///catalog.db')
BASE.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

"""
ROUTES

Contents:
    1. User based routes
    2. Catalog routes
    3. JSON API based routes

Authentication and Access:
Note that there are multiple auth and access controls in place

Auth:
API - Using HTTPAuth, to authenticate as a user, and return a token
OAuth - Google can be used for created and logging in as a user
Custom - Using passlib, there is a custom implementation as well using
         password hashing.

Access Control:
Some routes require having a username in the session. This will be set
by both Google OAuth and the custom mechanism
Some routes use the `verify_password` from HTTPAuth to protect API routes

navigating to /logout will clear the session and send 401 logout for HTTPAuth
browser clearing
"""


@app.route('/login', methods=['GET', 'POST'])
def showLogin():
    # This page presents a Google OAuth option
    # and a custom logon option
    # The POST method should only be used for the custom login function
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Try to get user from username first
        user = get_user(username)

        # Try to get user from email
        if user is None:
            user = get_user(email)
        if user is not None:
            if user.verify_password(password):
                login_session['username'] = user.username
                login_session['email'] = user.email
                flash("you are now logged in as {0}"
                      .format(login_session['username']))
                return redirect(url_for('dashboard'))
            else:
                flash("Password failed")
                return redirect(url_for('dashboard'))

    if request.method == 'GET':
        if get_user('admin') is None:
            return redirect(url_for('createInitialAdmin'))
        # Protect CSRF
        state = get_state_token()
        login_session['state'] = state
        return render_template('login.html',
                               STATE=state,
                               googOAuthClientId=GOOG_CLIENT_ID)


@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        oauth_flow = flow_from_clientsecrets(client_secrets_url, scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    content = (h.request(url, 'GET')[1])
    result = json.loads(content.decode('utf-8'))

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOG_CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token ent ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                'Current user is already connected.'),
                200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'
    # see if user exists, if not make it
    userID = get_user_id_from_email(login_session['email'])

    if userID is None:
        # print('No user ID found, creating user')
        userID = createUser(login_session)
        login_session['user_id'] = userID
    else:
        login_session['user_id'] = userID
    output = ''
    output += '<h2>Welcome, '
    output += login_session['username']
    output += '!</h2>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 60px; height: 60px; border-radius: 500px"> '
    flash("Now logged in as {0}".format(login_session['username']))
    return output


@app.route('/gdisconnect')
def gdisconnect():
    """
    Purpose:
        The the access token from the session, and call out to google
        to revoke the access the token has. Also, clear the login_session
    """

    try:
        access_token = login_session.get('access_token')
    except NameError as e:
        print("login_session not present")
        print(e.message)
        access_token = None
        pass

    if access_token is None:
        print('Current user not connected.')

        return redirect(url_for('Logout'))

    url = (
            "https://accounts.google.com/o/oauth2/revoke?token={0}"
            .format(login_session['access_token'])
        )

    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        login_session.clear()
        print('Successfully disconnected.')
        return redirect(url_for('Logout'), 301)
    else:
        login_session.clear()
        print('Error 400: Failed to revoke token for given user.')
        return redirect(url_for('Logout'), 301)


@app.route('/logout')
def Logout():

    if login_session.get('gplus_id'):
        print("Logged in with google. Calling gdisconnect...")
        return redirect(url_for('gdisconnect'))
    login_session.clear()
    return render_template('loggedout.html'), 401


@auth.verify_password
def verify_password(usernameOrToken, password):
    # first see if the usernameOrToken is a token
    # if it is, it will pass back and ID, if not
    # it will send back None

    user_id = User.verify_auth_token(usernameOrToken)
    if user_id:
        print("Looking for user_id {0}".format(user_id))
        user = session.query(User).filter_by(id=user_id).first()
    else:
        user = session.query(User).filter_by(username=usernameOrToken).first()
        # print("Found user: {0}".format(user.username))
        if not user or not user.verify_password(password):
            return False
        print("Authorized access to :{0}".format(user.username))

    g.user = user
    return True


# add /token route here to get a token for a user with login credentials
@app.route('/token', methods=['GET'])
@auth.login_required
def get_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')}), 201


@app.route('/user/create/admin')
def createInitialAdmin():
    if get_user('admin') is None:
        """create the admin user with defaults"""
        add_user('admin', 'password', 'admin@example.com')
        admin = get_user('admin')

        # update_object(admin)
        if admin is None:
            print "couldn't create the admin"
        return render_template('initialize.html')
    else:
        print "admin was found"
        return "already made"


@app.route('/user/create', methods=['GET', 'POST'])
def create_user():

    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Get fields from form
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Ensure fields have data and username doesn't exist
        if (
                username is not None and
                password is not None and
                get_user(username) is None and
                get_user_id_from_email(email) is None):
            new_id = add_user(username, password, email)
            id = get_user(username).id
            return redirect(url_for('getUser', user_id=id))
        else:
            print """Error: could not find password or username in
                    post request, or username already exists"""
            return """Error: could not find password or username in
                    post request, or username already exists"""

    if request.method == 'GET':
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        return render_template('adduser.html', STATE=state)


@app.route('/user/<int:id>/edit', methods=['GET', 'POST'])
def editUser(id):

    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Get user input from form
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Ensure the fields have data
        # and the user making the post is the
        # logged in user from the session
        if (username is not None and
                password is not None and
                id == get_user(login_session['username']).id):
            user = update_user(username, password, email)
            if user is not None:
                flash("User updated")
                login_session['username'] = user.username
                login_session['email'] = user.email
            else:
                flash("""There was a problem. Please make sure you're
                         using a unique username and email address.""")
            return redirect(url_for('currentUser'))
        else:
            print """Error: could not find password or username in
                    post request, or username already exists"""
            return """Error: could not find password or username in
                    post request, or username already exists"""

    if request.method == 'GET':
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        user = get_user(login_session['username'])
        return render_template('changepassword.html', user=user, STATE=state)


@app.route('/user')
def currentUser():
    if 'username' in login_session:
        username = login_session['username']
        email = login_session['email']
        user = get_user(username)
        # may need to look up using email instead for OAuth accounts
        # the user will be None if it wasn't found
        user = get_user_from_email(email) if user is None else user
        return render_template('user.html', user=user)
    else:
        flash("couldn't find user in session, please try logging in")
        return redirect(url_for('dashboard'))


@app.route('/user/<int:user_id>')
def getUser(user_id):
    if 'username' in login_session:
        user = get_user_from_id(user_id)

        if user is not None:
            return render_template('user.html', user=user)
    else:
        flash("Finding your way?")
        return redirect(url_for('dashboard'))


"""
Catalog routes
"""


@app.route('/')
@app.route('/dashboard')
def dashboard():
    categories = get_all_categories()
    recent_items = get_recent_items()
    return render_template('dashboard.html',
                           categories=categories,
                           items=recent_items,
                           userLoggedIn=userLoggedIn())


@app.route('/dashboard/<int:cat_id>/')
def categoryDash(cat_id):
    categories = get_all_categories()
    category = get_category(cat_id)
    recent_items = get_recent_items(category.id, 100)
    return render_template('category_dash.html', categories=categories,
                           items=recent_items, category=category,
                           userLoggedIn=userLoggedIn())


@app.route('/categories')
def index():
    if 'username' not in login_session:
        flash("Please login first!")
        print(request.referrer)
        return redirect(request.referrer)
    categories = get_all_categories()
    return render_template('categories.html',
                           categories=categories,
                           userLoggedIn=userLoggedIn())


@app.route('/category/<int:cat_id>/')
@app.route('/category/<int:cat_id>/show')
def category(cat_id):

    category = get_category(cat_id)
    return render_template('category.html',
                           category=category,
                           userLoggedIn=userLoggedIn())


@app.route('/category/<int:cat_id>/category_items')
def categoryItems(cat_id):
    category = session.query(Category).filter_by(id=cat_id).one()
    items = session.query(Item).filter_by(cat_id=category.id)
    return render_template('category_items.html',
                           category=category,
                           items=items,
                           userLoggedIn=userLoggedIn())


@app.route('/item/<int:item_id>/')
def itemInfo(item_id):
    item = get_item(item_id)
    # userLoggedIn = 0
    # if 'username' in login_session:
    #     userLoggedIn = 1
    return render_template('item.html',
                           item=item,
                           userLoggedIn=userLoggedIn())


@app.route('/category/<int:cat_id>/category_items/new',
           methods=['GET', 'POST'])
def newItem(cat_id):

    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Get user from login_session to create owner of new item
        user = get_user(login_session['username'])

        # Create a new item from the request
        new_id = add_item(
                request.form['cat_id'], request.form['name'],
                request.form['description'],
                user.id,
                request.form['price'])
        flash("New item created!")
        new_cat_id = get_item(new_id).cat_id
        if new_cat_id is None:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('categoryDash', cat_id=new_cat_id))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        categories = get_all_categories()
        if categories.first() is None:
            flash("Please create a category before you make an item!")
            print('Must create a category first...')
            return redirect(url_for('newCategory'))
        return render_template('new_category_item.html', cat_id=cat_id,
                               userLoggedIn=userLoggedIn(),
                               categories=categories, STATE=state)


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id):
    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Check if user is owner of item
        if login_session['username'] != get_item(item_id).user.username:
            flash("You can't change what's not yours...")
            return redirect(url_for('itemInfo', item_id=item_id))

        # Update the item details
        update_item(request.form['cat_id'], item_id,
                    request.form['name'], request.form['description'],
                    request.form['price'])
        flash("Item updated!")
        return redirect(url_for('itemInfo', item_id=item_id))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        item = get_item(item_id)
        categories = get_all_categories()
        return render_template('edititem.html', item=item,
                               categories=categories,
                               userLoggedIn=userLoggedIn(), STATE=state)


@app.route('/category/<int:cat_id>/category_items/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(cat_id, item_id):
    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response
        # Check if user is owner of item
        if login_session['username'] != get_item(item_id).user.username:
            flash("You can't change what's not yours...")
            return redirect(url_for('itemInfo', item_id=item_id))
        # Delete or Cancel based on the value of delete field
        if request.form['delete'] == 'Delete':
            delete_item(item_id)
            flash("Item deleted!")
        elif request.form['delete'] == 'Cancel':
            pass
        return redirect(url_for('categoryDash', cat_id=cat_id))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        item = get_item(item_id)
        return render_template('deleteitem.html',
                               item=item,
                               userLoggedIn=userLoggedIn(),
                               STATE=state)


@app.route('/category/new', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('dashboard', userLoggedIn=userLoggedIn()))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Get user from session to set owner of new Category
        user = get_user(login_session['username'])

        # Create the category
        new_id = add_category(request.form['name'], user.id)
        flash("Category added!")
        return redirect(url_for('categoryDash', cat_id=new_id))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        return render_template('newcategory.html',
                               userLoggedIn=userLoggedIn(),
                               STATE=state)


@app.route('/category/<int:cat_id>/edit', methods=['GET', 'POST'])
def editCategory(cat_id):
    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('category', cat_id=cat_id,
                                userLoggedIn=userLoggedIn()))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Verify Category ownership
        if login_session['username'] != get_category(cat_id).user.username:
            flash("You can't change what's not yours...")
            return redirect(url_for('categoryDash', cat_id=cat_id))

        update_category(cat_id, request.form['name'])
        flash("Category updated!")
        return redirect(url_for('categoryDash', cat_id=cat_id))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        category = get_category(cat_id)
        return render_template('editcategory.html',
                               category=category,
                               userLoggedIn=userLoggedIn(),
                               STATE=state)


@app.route('/category/<int:cat_id>/delete', methods=['GET', 'POST'])
def deleteCategory(cat_id):
    if 'username' not in login_session:
        flash("Please login first!")
        return redirect(url_for('category', cat_id=cat_id))
    if request.method == 'POST':
        # Protect for CRSF
        response = bad_state(
                request.form['state'],
                login_session['state'])
        if response is not None:
            return response

        # Verify ownership
        user = get_user(login_session['username'])

        if user.username != get_category(cat_id).user.username:
            flash("You can't change what's not yours...")
            return redirect(url_for('deleteCategory', cat_id=cat_id))

        # Verify all items in the category are owned by the user
        non_owned_items = check_cat_item_owner(cat_id)
        if non_owned_items.first() is not None:
            flash("Sorry, some sub items aren't yours.")
            return redirect(url_for('categoryDash', cat_id=cat_id))

        if request.form['delete'] == 'Delete':
            delete_category(cat_id)
            flash("Category deleted!")
        elif request.form['delete'] == 'Cancel':
            pass
        return redirect(url_for('dashboard'))
    else:
        # Treat as GET request with a state token
        # to protect CSRF
        state = get_state_token()
        login_session['state'] = state
        category = get_category(cat_id)
        return render_template('deletecategory.html',
                               category=category,
                               STATE=state)


"""
Routes used exclusively for json
"""


@app.route('/json')
def jsonPage():
    return render_template('json_page.html')


@app.route('/category/<int:cat_id>/json', methods=['GET'])
def getAllItemJson(cat_id):
    cat = get_category(cat_id).serialize
    items = get_all_items(cat_id)
    return_json = cat.copy()
    return_json.update(Items=[item.serialize for item in items])
    return jsonify(return_json)


@app.route('/item/<int:item_id>/json', methods=['GET'])
def getItemJson(item_id):
    item = get_item(item_id)
    return jsonify(Items=item.serialize)


@app.route('/categories/json', methods=['GET'])
def getAllCategoriesJson():
    categories = get_all_categories()
    return jsonify(Categories=[res.serialize for res in categories])


@app.route('/fullcatalog/json', methods=['GET'])
def getFullCatalogJson():
    return_json = []
    categories = get_all_categories()

    for category in categories:
        temp = category.serialize.copy()
        items = get_all_items(category.id)
        temp.update(Items=[item.serialize for item in items])
        return_json.append(temp)
    return jsonify(return_json)


@app.route('/allitems/json', methods=['GET'])
def getAllItems():
    items = get_all_items()
    Items = [item.serialize for item in items]
    return jsonify(Items)


@app.route('/users/json')
@auth.login_required
def getUsers():
    if g.user or 'username' in login_session:
        users = get_all_users()
        return jsonify(User=[user.serialize for user in users])
    flash("Please login first!")
    return redirect(url_for('dashboard'))


@app.route('/user/<int:user_id>/json')
@auth.login_required
def getUserJson(user_id):

    user = get_user_from_id(user_id)
    if user is not None:
        print user.username
        print login_session
        return jsonify(user.serialize)
    else:
        print 'no user with id {0}'.format(user_id)
        return 'none'


# helper functions
@app.context_processor
def userLoggedIn():
    """
    Purpose: Used to check if a user is logged in.
             Can be called from templates to prevent
             rending sections of html is the user
             is not logged in.
    """
    return dict(globalUserLoggedIn=1 if 'username' in login_session else 0)


def get_state_token():
    """
    Create a random string for use int state tokens for CRSF protection
    """
    token = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    return token


def bad_state(request_token, session_token):
    """
    Purpose: Check if the request has the proper state token

    Returns: A response object.  If the state is valid, the response
             is returned with 'None' as the value.
    """
    if request.form['state'] != login_session['state']:
            response = make_response(json.dumps('Invalid state parameter.'),
                                     401)
            response.headers['Content-Type'] = 'application/json'

    else:
        response = None

    return response


if __name__ == '__main__':
#    app.secret_key = SUPER_SECRET_KEY
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
