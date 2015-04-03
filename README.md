# udacity-catalog #

## Preparations ##

This app uses [Flask-GoogleLogin](https://pythonhosted.org/Flask-GoogleLogin/) so you have to install it before you can run the app.

To install Flask-GoogleLogin run

    pip install Flask-GoogleLogin

As the app uses Google for authentication as the next step you have to obtain a client id and client secret from Google:

1. Go to the [Google Developer Console](https://console.developers.google.com/project).
2. Create a new project.
3. Go to **APIs & auth - Consent screen** and select a valid Email address.
4. Go to **APIs & auth - Credentials** and create a new Client ID.
5. Enter **http://localhost:8000/oauth2callback/** in the **Authorized redirect URIs** field.
6. Open the **project.py** file and replace the **<Client ID\>** and **<Client Secret\>** placeholders with your client id and your client secret.

Next you have to create the categories. To do so run

	python database_setupy.py

## Run the app ##

To start the app simply run
	
	python project.py

## Remarks ##
- The app uses [Jasny Bootstrap's](http://jasny.github.io/bootstrap/javascript/#fileinput) file input widget for the picture upload.
- The pictures are stored in the database.
- The app uses nonces to prevent cross-site request forgeries (CSFR) when creating, updating and deleting items.
- The app offers two API endpoints:
	- **JSON:** /catalog.json
	- **XML:** /catalog.xml
- The app uses a (slightly modified) **dashboard.css** stylesheet from Bootstrap's [Dashboard sample page](http://getbootstrap.com/examples/dashboard/).
- The app is not optimized for small devices (smartphones etc.).
