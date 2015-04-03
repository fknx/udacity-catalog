import os
import base64

from datetime import datetime
from urllib import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask import session as flask_session
from werkzeug.exceptions import NotFound
app = Flask(__name__)

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

from jinja2 import Environment, PackageLoader

from flask_login import LoginManager, login_user, logout_user, login_required
from flask_googlelogin import GoogleLogin

env = Environment(loader=PackageLoader('project', 'templates'))
env.filters['urlencode'] = urlencode

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# limit the size of the content to ~ 5 MB (for the picture upload)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

app.config['GOOGLE_LOGIN_CLIENT_ID'] = '<Client ID>'
app.config['GOOGLE_LOGIN_CLIENT_SECRET'] = '<Client Secret>'
app.config['GOOGLE_LOGIN_REDIRECT_URI'] = 'http://localhost:8000/oauth2callback/'

login_manager = LoginManager()
login_manager.init_app(app)
googlelogin = GoogleLogin(app, login_manager)

@app.route('/')
def latestItems():
    """Lists the items which were recently created in descending order (newest item first)."""
    categories = session.query(Category).all()
    items = session.query(Item).order_by(desc(Item.creation_date)).limit(10).all()
    return render_template('latest_items.html', categories=categories, items=items)

@app.route('/category/<int:category_id>/items/')
def listItems(category_id):
    """Lists all items of the specified category.

    Args:
        category_id: the id of the category
    """
    categories = session.query(Category).all()
    category = session.query(Category).get(category_id)
    return render_template('list_items.html', categories=categories, category=category, number_of_items=len(category.items), items=category.items)

@app.route('/category/<int:category_id>/item/<int:item_id>/')
def showItem(category_id, item_id):
    """Shows the details of the specified item.

    Args:
        category_id: the id of the item's category
        item_id: the id of the item
    """
    categories = session.query(Category).all()
    category = session.query(Category).get(category_id)

    item = session.query(Item).filter_by(id=item_id, category_id=category.id).one()
    return render_template("show_item.html", categories=categories, item=item)

@app.route('/item/<int:item_id>/picture/')
def itemPicture(item_id):
    item = session.query(Item).get(item_id)

    if not item.picture:
        raise NotFound()

    file_extension = item.picture.rsplit('.', 1)[1].lower()

    if file_extension == "jpg" or file_extension == "jpeg":
        content_type = "image/jpeg"
    else:
        content_type = "image/png" # the image type must be png, as only jpg and png are allowed

    return item.picture_data, 200, {'Content-Type': content_type, 'Content-Disposition': "filename='%s'" % item.picture}

@app.route('/item/new/', methods=['GET','POST'])
@login_required
def createItem():
    """Creates a new item."""
    categories = session.query(Category).all()
    if request.method == 'GET':
        return render_template('create_item.html', categories=categories, nonce=createNonce())

    nonce = request.form['nonce'].strip()

    if not useNonce(nonce):
        flash("An error occurred. Please try again.", "danger")
        return render_template('create_item.html', categories=categories, nonce=createNonce())

    name = request.form['name'].strip()

    if not name:
        flash("Please enter a name.", "danger")
        return render_template('create_item.html', categories=categories, nonce=createNonce())

    category_name = request.form['category'].strip()

    if not category_name:
        flash("Please choose a category", "danger")
        return render_template('create_item.html', categories=categories, nonce=createNonce())

    try:
        category = session.query(Category).filter_by(name=category_name).one()
    except Exception, e:
        flash("Please choose a valid category.", "danger")
        return render_template('create_item.html', categories=categories, nonce=createNonce())

    # check if an items with the same name already exists in this category
    existingItem = session.query(Item).filter_by(category_id=category.id, name=name).first()
    if existingItem:
        flash("An item with the same name already exists in this category. Please choose a different name", "danger")
        return render_template('create_item.html', categories=categories)

    description = request.form['description'].strip()

    picture = request.files['picture']
    picture_data = None

    if picture:
        if not allowed_file(picture.filename):
            flash("The picture must be a JPEG or PNG file.", "danger")
            return render_template('create_item.html', categories=categories, nonce=createNonce())

        picture_data = picture.read()

    item = Item(name=name, description=description, category=category, creation_date=datetime.utcnow())
    if picture_data:
        item.picture = picture.filename
        item.picture_data = picture_data

    session.add(item)
    session.commit()
    flash("The item '%s' has been created." % name, "success")

    return redirect(url_for('listItems', category_id=category.id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['jpg', 'jpeg', 'png']

@app.route('/item/<int:item_id>/edit/', methods=['GET','POST'])
@login_required
def editItem(item_id):
    """Modifies the item with the given id.

    Args:
        item_id: the id of the item which shall be modified
    """
    categories = session.query(Category).all()
    item = session.query(Item).get(item_id)

    if request.method == 'GET':
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    nonce = request.form['nonce'].strip()

    if not useNonce(nonce):
        flash("An error occurred. Please try again.", "danger")
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    name = request.form['name'].strip()

    if not name:
        flash("Please enter a name.", "danger")
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    category_name = request.form['category'].strip()

    if not category_name:
        flash("Please choose a category", "danger")
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    try:
        category = session.query(Category).filter_by(name=category_name).one()
    except Exception, e:
        flash("Please choose a valid category", "danger")
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    description = request.form['description'].strip()

    # check if an items with the same name already exists in this category
    existingItem = session.query(Item).filter_by(category_id=category.id, name=name).first()
    if existingItem and existingItem.id != item.id:
        flash("An item with the same name already exists in this category. Please choose a different name", "danger")
        return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

    removeExistingPicture = request.form['removeExistingPicture'].strip().lower()

    if removeExistingPicture == "true":
        item.picture = None
        item.picture_data = None

    picture = request.files['picture']
    picture_data = None

    if picture:
        if not allowed_file(picture.filename):
            flash("The picture must be a JPEG or PNG file.", "danger")
            return render_template('edit_item.html', categories=categories, item=item, nonce=createNonce())

        picture_data = picture.read()
        print "Content-Length: %s" % picture.content_length

    item.name = name
    item.description = description
    item.category = category

    if picture_data:
        item.picture = picture.filename
        item.picture_data = picture_data

    session.add(item)
    session.commit()
    flash("Your changes have been saved.", "success")

    return redirect(url_for('listItems', category_id=category.id))

@app.route('/item/<int:item_id>/delete/', methods=['GET','POST'])
@login_required
def deleteItem(item_id):
    """Delete the item with the given id.

    Args:
        item_id: the id of the item which shall be deleted
    """
    categories = session.query(Category).all()
    item = session.query(Item).get(item_id)
    if request.method == 'GET':
        return render_template('delete_item.html', categories=categories, item=item, nonce=createNonce())

    nonce = request.form['nonce'].strip()

    if not useNonce(nonce):
        flash("An error occurred. Please try again.", "danger")
        return render_template('delete_item.html', categories=categories, item=item, nonce=createNonce()) # ToDo error message

    session.delete(item)
    session.commit()
    flash("The item '%s' has been removed." % item.name, "success")

    return redirect(url_for('listItems', category_id=item.category.id))

@app.route('/catalog.json/')
def catalogJSON():
    """Returns the catalog in JSON notation."""
    categories = session.query(Category).all()
    return jsonify(Categories=[category.serialize for category in categories])

@app.route('/catalog.xml/')
def catalogXML():
    """Returns the catalog as XML document."""
    categories = session.query(Category).all()

    content = []
    content.append('<?xml version="1.0" encoding="UTF-8"?>')
    content.append("<Categories>")

    for category in categories:
        category.serializeToXml(content)

    content.append("</Categories>")

    return str.join("\n", content), 200, {'Content-Type': 'text/xml'}

@app.route('/login/', methods=['GET','POST'])
def login():
    """Redirects the user to the Google login page."""
    if request.method == 'GET':
        categories = session.query(Category).all()
        return render_template('login.html', categories=categories)

    return googlelogin.unauthorized_callback()

@app.route('/logout/', methods=['GET','POST'])
@login_required
def logout():
    """Logs out the current user."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/oauth2callback/')
@googlelogin.oauth2callback
def oauth2callback(token, userinfo, **params):
    """The Oauth2 callback from Flask-GoogleLogin"""
    id = str(userinfo['id'])
    name = userinfo['name'].strip()

    changed = False

    user = session.query(User).filter_by(id=id).first()

    if not user:
        user = User(id=id, name=name)
        changed = True
    elif user.name != name:
        user.name = name
        changed = True

    if changed:
        session.add(user)
        session.commit()

    login_user(user, remember=True)

    return redirect(request.args.get("next") or url_for("latestItems"))

@login_manager.user_loader
def load_user(userid):
    """User loader for Flask Login. As the user is only stored
    in the session an attempt is made to retrieve the user from the session.
    In case this fails, None is returned.

    Args:
        userid: the user id

    Returns:
        the user object or None in case the user could not be retrieved from the session
    """
    try:
        print "load_user called: %s" % userid
        user = session.query(User).filter_by(id=str(userid)).first()

        if not user:
            return None

        return user
    except:
        return None

def createNonce():
    """Creates a new nonce and stores it in the session."""
    nonce = base64.b64encode(os.urandom(32))
    flask_session['nonce'] = nonce

    return nonce

def useNonce(nonce):
    """Compares the provided nonce with the one stored in the session.

    If a nonce is stored in the session it will be remoed even if the nonces should not match.

    Args:
        nonce: the nonce which was included in the post request

    Returns:
        True in case the provided nonce is equal to the nonce stored in the session, otherwise False
    """
    try:
        session_nonce = flask_session['nonce']
        if not session_nonce:
            return False

        del(flask_session['nonce'])

        if not nonce:
            return False

        if nonce != session_nonce:
            return False

        return True
    except Exception:
        return False

if __name__ == '__main__':
    app.secret_key = "jIdee28q8BzcqR3oPmKICRkCYUTs5fn3cHOpoBbLMMbuK0B/Nhwd//hrYkwUD6CTAhlwo7jiuNnFfiMrf36m/g=="
    app.debug = True
    app.run(host = '0.0.0.0', port = 8000)