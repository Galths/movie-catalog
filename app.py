import os

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "secret_dev_key" # Change this for production!

# MongoDB Configuration
MONGO_URI = mongodb+srv://gabrielgitmyhub_db_user:hxIYm9MeFwisVsa1@cluster0.mjbnjto.mongodb.net/?appName=Cluster0"MONGO_URI")
mongo = MongoClient(MONGO_URI)
movieDB = mongo.db
movieCollection = movieDB.movieCollection
users = movieDB.users



# --- DECORATORS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    users_id = session.get("users_id")
    if not users_id:
        return None
    
    try:
        return users.find_one({"_id": ObjectId(users_id)})
    except Exception:
        session.clear()
        return None

@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user()}

# --- ROUTES ---

@app.route('/')
def index():
    # Public viewing: fetch all movies
    movies = list(movieCollection.find())
    return render_template('base.html', movies=movies)

@app.route('/browse')
def browse():
    movies = list(movieCollection.find())
    return render_template('browse.html', movies=movies)

@app.route('/movie_detail/<movie_id>')
def movie_detail(movie_id):
    # Security Check: Ensure only admins can delete
        movie = movieCollection.find_one({"_id": ObjectId(movie_id)})
        
        if movie:
            return render_template('movie_detail.html', movie=movie)
        else:
            return "Movie Not Found", 404

# --- SIGNUP ROUTE ---
@app.route('/signup', methods=['GET', 'POST']) # Changed from /login to /signup
def signup():
    if request.method == 'POST':
        username= request.form["username"].strip()
        email= request.form["email"].strip().lower()
        password= request.form["password"]

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template('signup.html')

        if users.find_one({"email": email}):
            flash("An account with the email already exists.", "error")
            return render_template('signup.html')
            
        users.insert_one(
            {
                "username": username,
                "email": email,
                "password": generate_password_hash(password),
                "role": "admin"  # Default role
            }
        )
        # After signing up, send them to the login page
        flash("Account created! Please log in.")
        return redirect(url_for('login'))
    
    # Make sure you have a signup.html! 
    # If not, you can use login.html but the form action must point to /signup
    return render_template('signup.html') 

# --- LOGIN ROUTE ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        
        user = users.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user'] = {
                "id": str(user['_id']), 
                "role": user['role'], 
                "name": user['username'],
                "username": user['username'] # Added for your sidebar display
            }
            flash("Welcome Back!", "Success")
            # Redirect to the HOME PAGE after login, not back to login
            return redirect(url_for('browse')) 
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))
        
    return render_template('login.html')

# --- LOGOUT ROUTE ---
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "Success")
    return redirect(url_for("login"))



# --- BOOKMARK ROUTE ---
@app.route('/bookmark/<movie_id>')
@login_required
def bookmark(movie_id):
    # Add movie ID to user's bookmark array in MongoDB
    mongo.db.users.update_one(
        {"_id": ObjectId(session['user']['id'])},
        {"$addToSet": {"bookmarks": ObjectId(movie_id)}}
    )
    return redirect(url_for('index'))

# --- MY COLLECTION ROUTE ---
@app.route('/my_collection')
def my_collection():
    #if 'users' not in session:
    #   return redirect(url_for('login'))
    
    return render_template('my_collection.html')

# --- MANAGE MOVIES ROUTE---
@app.route('/manage_movies')
def manage_movies():
    #if 'users' not in session:
    #   return redirect(url_for('login'))

    movie_list = list(movieCollection.find())
    movie_count = len(movie_list)

    return render_template('manage_movies.html',
                            movies = movie_list,
                            count = movie_count,
                            user = session['user'])

# --- ADD MOVIES ROUTE ---
@app.route('/manage_movies', methods=['GET','POST'])
def add_movie():
    if request.method == "POST":
        title = request.form["title"]
        genre = request.form["genre"]
        year = request.form["year"]
        rating = request.form["rating"]
        duration = request.form["duration"]
        director = request.form["director"]
        cast = request.form["cast"]
        poster_url = request.form["poster_url"]
        trailer_url = request.form["trailer_url"]
        description = request.form["description"]

        movie = {
            "title": title,
            "genre": genre,
            "year": year,
            "rating": rating,
            "duration": duration,
            "cast": cast,
            "poster_url": poster_url,
            "trailer_url": trailer_url,
            "description": description
        }
        movieCollection.insert_one(movie)
        flash("MOVIE ADDED SUCCESSFULLY!")
        return redirect(url_for('add_movie'))
    return render_template('manage_movies.html')

#--- UPDATE MOVIE ---

@app.route("/manage_movies/update", methods=['POST'])
def update_movie():
    # Fetch ID from the hidden input field instead of the URL
    movie_id = request.form.get("movie_id") 

    if not movie_id:
        return "Error: Movie ID is missing", 400

    # Capture all form data
    updated_data = {
        "title": request.form.get("title"),
        "genre": request.form.get("genre"),
        "year": request.form.get("year"),
        "rating": request.form.get("rating"),
        "duration": request.form.get("duration"),
        "director": request.form.get("director"),
        "cast": request.form.get("cast"),
        "poster_url": request.form.get("poster_url"),
        "trailer_url": request.form.get("trailer_url"),
        "description": request.form.get("description")
    }

    # Perform the update
    movieCollection.update_one(
        {"_id": ObjectId(movie_id)},
        {"$set": updated_data}
    )

    return redirect(url_for("manage_movies"))

# --- DELETE MOVIE ---

@app.route('/delete_movie/<id>', methods=['POST'])
def delete_movie(id):
    # Security Check: Ensure only admins can delete
    if session.get('user') and session['user']['role'] == 'admin':
        movieCollection.delete_one({"_id": ObjectId(id)})
        return redirect(url_for("manage_movies"))
    
    # If not authorized, redirect to login or show error
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
