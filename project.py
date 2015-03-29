import os
import base64

from datetime import datetime
from urllib import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask import session as flask_session
app = Flask(__name__)

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item

from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('project', 'templates'))
env.filters['urlencode'] = urlencode

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def latestItems():
    """Lists the items which were recently created in descending order (newest item first)."""
    categories = session.query(Category).all()
    items = session.query(Item).order_by(desc(Item.creation_date)).limit(10).all()
    return render_template('latest_items.html', categories=categories, items=items)

@app.route('/catalog/<string:category_name>/items/')
def listItems(category_name):
    """Lists all items of the specified category.

    Args:
        category_name: the name of the category
    """
    categories = session.query(Category).all()
    category = session.query(Category).filter_by(name=category_name).one()
    return render_template('list_items.html', categories=categories, category=category, number_of_items=len(category.items), items=category.items)

@app.route('/catalog/<string:category_name>/<string:item_name>/')
def showItem(category_name, item_name):
    """Shows the details of the specified item.

    Args:
        category_name: the name of the item's category
        item_name: the name of the item
    """
    categories = session.query(Category).all()
    category = session.query(Category).filter_by(name=category_name).one()

    item = session.query(Item).filter_by(name=item_name,category_id=category.id).one()
    return render_template("show_item.html", categories=categories, item=item)

@app.route('/item/new/', methods=['GET','POST'])
def createItem():
    """Creates a new item."""
    categories = session.query(Category).all()
    if (request.method == 'GET'):
        return render_template('create_item.html', categories=categories)

    name = request.form['name'].strip()

    if not name:
        return render_template('create_item.html', categories=categories) # ToDo error message

    category_name = request.form['category'].strip()

    if not category_name:
        return render_template('create_item.html', categories=categories) # ToDo error message

    # ToDo check if already exists

    category = session.query(Category).filter_by(name=category_name).one()

    description = request.form['description'].strip()

    item = Item(name=name, description=description, category=category, creation_date=datetime.utcnow())
    session.add(item)
    session.commit()
    flash("the item '%s' has been created" % name)

    return redirect(url_for('listItems', category_name=category_name))

@app.route('/item/edit/<int:item_id>/', methods=['GET','POST'])
def editItem(item_id):
    """Modifies the item with the given id.

    Args:
        item_id: the id of the item which shall be modified
    """
    categories = session.query(Category).all()
    item = session.query(Item).get(item_id)

    if (request.method == 'GET'):
        return render_template('edit_item.html', categories=categories, item=item)

    name = request.form['name'].strip()

    if not name:
        return render_template('edit_item.html', categories=categories, item=item) # ToDo error message

    category_name = request.form['category'].strip()

    if not category_name:
        return render_template('edit_item.html', categories=categories, item=item) # ToDo error message

    category = session.query(Category).filter_by(name=category_name).one()

    description = request.form['description'].strip()

    # ToDo check if already exists

    category = session.query(Category).filter_by(name=category_name).one()

    item.name = name
    item.description = description
    item.category = category
    session.add(item)
    session.commit()
    flash("the item '%s' has been modified" % name)

    return redirect(url_for('listItems', category_name=category_name))

@app.route('/item/delete/<int:item_id>/', methods=['GET','POST'])
def deleteItem(item_id):
    """Delete the item with the given id.

    Args:
        item_id: the id of the item which shall be deleted
    """
    categories = session.query(Category).all()
    item = session.query(Item).get(item_id)
    if (request.method == 'GET'):
        return render_template('delete_item.html', categories=categories, item=item, nonce=createNonce())

    nonce = request.form['nonce'].strip()

    if not useNonce(nonce):
        return render_template('delete_item.html', categories=categories, item=item, nonce=createNonce()) # ToDo error message

    session.delete(item)
    session.commit()
    flash("the item '%s' has been removed" % item.name)

    return redirect(url_for('listItems', category_name=item.category.name))

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