from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from db import init_db, add_user, get_user, log_user_interaction, get_user_interactions, get_user_by_id

app = Flask(__name__)

# Flask app configurations
app.secret_key = '@cherop2003'  # Use a secure and random key for production
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)

# Initialize database
init_db()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Load user from database for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        return User(user['id'], user['username'])
    return None

def add_time_of_day(data):
    current_hour = datetime.now().hour

    if 6 <= current_hour < 12:
        time_of_day = 'morning'
    elif 12 <= current_hour < 18:
        time_of_day = 'afternoon'
    elif 18 <= current_hour < 21:
        time_of_day = 'evening'
    else:
        time_of_day = 'night'

    data['time_of_day'] = time_of_day
    return data

# Load article data
def load_data():
    data = pd.read_csv('news_data.csv')
    data['published'] = pd.to_datetime(data['published'], errors='coerce')
    locations = ['New York', 'London', 'Tokyo', 'Berlin', 'Sydney']
    data['location'] = [random.choice(locations) for _ in range(len(data))]
    if 'link' not in data.columns:
        data['link'] = ''  # Add link column if missing
    # Add time_of_day column
    data = add_time_of_day(data)
    return data


data = load_data()

# TF-IDF and cosine similarity for content-based filtering
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(data['summary'].fillna(''))
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if get_user(username):
            return "Username already exists. Please choose a different one."
        hashed_password = generate_password_hash(password)
        add_user(username, hashed_password)
        return redirect(url_for('login'))
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        return "Invalid username or password."
    return render_template('login.html')

# User dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    username = current_user.username
    trending_stories = data.sort_values(by='published', ascending=False).head(5).to_dict(orient='records')

    # Collaborative recommendations
    user_interactions = get_user_interactions(current_user.id)
    collaborative_articles = (
        collaborative_filtering_recommendation(current_user.id, user_interactions)
        if user_interactions else []
    )

    # Content-based recommendations
    content_recommendations = (
        content_based_recommendation(trending_stories[0]['title'], cosine_sim, current_user.id)
        if trending_stories else []
    )

    # Contextual recommendations
    current_time_of_day = get_current_time_of_day()
    contextual_recommendations = contextual_filtering(current_time_of_day, current_user.id)

    # Check if no recommendations are available
    no_recommendations = not any([collaborative_articles, content_recommendations, contextual_recommendations])

    return render_template(
        'dashboard.html',
        username=username,
        trending_stories=trending_stories,
        collaborative_articles=collaborative_articles,
        content_articles=content_recommendations,
        contextual_articles=contextual_recommendations,
        no_recommendations=no_recommendations
    )

# Helper functions for recommendations
def content_based_recommendation(title, cosine_sim, user_id=None):
    # For new users, return the latest articles instead of relying on their history
    if user_id is None:  # No user interactions
        return data.sort_values(by='published', ascending=False).head(5).to_dict(orient='records')
    
    idx = data.index[data['title'] == title].tolist()
    if not idx:
        return []
    idx = idx[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:6]  # Top 5 recommendations excluding the article itself
    return data.iloc[[score[0] for score in sim_scores]].to_dict(orient='records')



def collaborative_filtering_recommendation(user_id, user_interactions):
    # If user has no interactions, show popular articles
    if not user_interactions:
        return data.sort_values(by='published', ascending=False).head(5).to_dict(orient='records')
    
    # Placeholder for actual collaborative filtering logic
    return []


def contextual_filtering(current_time_of_day, user_id=None):
    # For new users, return a diverse set of articles
    if user_id is None:
        return data[data['time_of_day'] == current_time_of_day].head(5).to_dict(orient='records')
    
    # For users with history, apply personalized filtering logic
    filtered_data = data[data['time_of_day'] == current_time_of_day]
    return filtered_data.head(5).to_dict(orient='records')


def get_current_time_of_day():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    return 'night'

# Article reading route
@app.route('/read_article/<article_title>')
@login_required
def read_article(article_title):
    article = data[data['title'] == article_title].iloc[0]
    log_user_interaction(current_user.id, article_title, article['link'])
    return render_template('article_page.html', article=article)

# Search route
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    query = request.form.get('query', '') if request.method == 'POST' else ''
    filtered_articles = (
        data[data['title'].str.contains(query, case=False) | data['summary'].str.contains(query, case=False)]
        if query else pd.DataFrame()
    )
    return render_template('search_results.html', articles=filtered_articles.to_dict(orient='records'), query=query)

# Trending stories
# Route for Trending stories
@app.route('/trending')
def trending():
    trending_stories = data.sort_values(by='published', ascending=False).head(5)
    # Convert the top 5 trending articles into a list of dictionaries
    trending_stories_dict = trending_stories.to_dict(orient='records')
    return render_template('trending.html', trending_stories=trending_stories_dict)


# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
