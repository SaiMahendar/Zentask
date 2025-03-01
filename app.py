from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from textblob import TextBlob
from transformers import pipeline

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load users from the JSON file
def load_users():
    try:
        with open('users.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save users to the JSON file
def save_users(users):
    with open('users.json', 'w') as file:
        json.dump(users, file, indent=4)

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home route
@app.route('/')
def home():
    return render_template('index.html', logged_in='username' in session)

# # Feature page after clicking "Click Me"
# @app.route('/feature/<int:feature_id>')
# def feature(feature_id):
#     if 'username' not in session:
#         return redirect(url_for('login'))  # If not logged in, ask to login
#     return render_template('feature.html', feature_id=feature_id, username=session['username'])

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash("Incorrect username or password.")
            return redirect(url_for('login'))

    return render_template('login.html')

# Signup route
import os
from werkzeug.utils import secure_filename

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        sec_question = request.form['sec_question']
        sec_answer = request.form['sec_answer']

        # Check if the user exists in the dictionary
        users = load_users()
        if username in users:
            flash("Username already exists.", category='error')
        elif any(u['email'] == email for u in users.values()):
            flash("Email already exists.", category='error')
        else:
            # # Hash password before saving
            # password_hash = generate_password_hash(password)

            # Handle profile picture upload
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Save to 'static/uploads' folder
                file.save(os.path.join(app.static_folder, 'uploads', filename))  # Ensure this folder exists
            else:
                filename = None

            # Add new user to the users dictionary
            users[username] = {
                'firstname': firstname,
                'lastname': lastname,
                'email': email,
                'password': password,
                'sec_question': sec_question,
                'sec_answer': sec_answer,
                'profile_pic': filename
            }

            # Save the new user
            save_users(users)

            flash("Signup successful! Please login.", category='success')
            return redirect(url_for('login'))

    return render_template('signup.html')

# Forgot password route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        sec_answer = request.form['sec_answer']
        
        users = load_users()

        if username in users:
            user = users[username]
            if user['email'] == email and user['sec_answer'] == sec_answer:
                new_password = request.form['new_password']
                user['password'] = new_password
                save_users(users)
                flash("Password updated successfully!")
                return redirect(url_for('login'))
            else:
                flash("Details do not match.")
        else:
            flash("Username not found.")
    
    return render_template('forgot_password.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Profile page
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login

    users = load_users()  # Load users data
    username = session['username']
    user = users.get(username, None)

    if user:
        tasks = load_tasks_pro(username)  # Load the tasks for the logged-in user

        # Count done and not done tasks
        done_tasks = sum(1 for task in tasks if task.get('done', False))
        not_done_tasks = len(tasks) - done_tasks

        # Pass these counts and tasks to the template
        return render_template('profile.html', user=user, done_tasks=done_tasks, not_done_tasks=not_done_tasks, tasks=tasks)
    else:
        flash("User not found.")
        return redirect(url_for('login'))



# Function to load task data from the JSON file
def load_tasks_pro(username):
    try:
        with open('tada.json', 'r') as file:
            tasks_data = json.load(file)
            # Return tasks for the logged-in user
            return tasks_data.get(username, [])
    except FileNotFoundError:
        return []  # Return an empty list if the file is not found
    except json.JSONDecodeError:
        return []  # Return an empty list if there is an error in decoding the JSON


# ---------------------------------------------------------------------------------------------------------->
# Todo code starts here...

# Load tasks for the logged-in user from the JSON file
def load_tasks(username):
    try:
        with open('tada.json', 'r') as file:
            tasks = json.load(file)
            # Ensure the tasks are stored by username in a dictionary format
            if isinstance(tasks, list):  # If tasks are stored as a list, convert to dict
                tasks = {}
    except FileNotFoundError:
        tasks = {}

    # Return tasks specific to the logged-in user, or an empty list if no tasks exist for the user
    return tasks.get(username, [])

# Save tasks for the logged-in user to the JSON file
def save_tasks(username, tasks):
    try:
        with open('tada.json', 'r') as file:
            all_tasks = json.load(file)
            # Ensure the tasks are stored by username in a dictionary format
            if isinstance(all_tasks, list):  # If tasks are stored as a list, convert to dict
                all_tasks = {}
    except FileNotFoundError:
        all_tasks = {}

    # Update or create the user's task list
    all_tasks[username] = tasks

    with open('tada.json', 'w') as file:
        json.dump(all_tasks, file, indent=4)

# Home route to display tasks and form to add new tasks
@app.route('/todo', methods=['GET', 'POST'])
def todo():
    if 'username' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login

    username = session['username']
    tasks = load_tasks(username)  # Load tasks specific to the logged-in user

    if request.method == 'POST':
        task_title = request.form.get('title')
        task_description = request.form.get('task')
        subtasks = request.form.getlist('subtask')

        # Create a new task with subtasks
        if task_title and task_description:
            new_task = {
                'title': task_title,
                'task': task_description,
                'subtasks': [{'subtask': sub, 'done': False} for sub in subtasks],
                'done': False  # Main task is not done initially
            }
            tasks.append(new_task)
            save_tasks(username, tasks)  # Save tasks for the logged-in user
            return redirect(url_for('todo'))

    return render_template('todo.html', tasks=tasks)


# Mark task as done
@app.route('/mark_done/<int:task_id>', methods=['POST'])
def mark_done(task_id):
    username = session['username']
    tasks = load_tasks(username)
    task = tasks[task_id]
    task['done'] = True
    save_tasks(username, tasks)
    return jsonify({'message': f"You completed the task: {task['title']}"}), 200

# Mark task as undone
@app.route('/unmark_done/<int:task_id>', methods=['POST'])
def unmark_done(task_id):
    username = session['username']
    tasks = load_tasks(username)
    task = tasks[task_id]
    task['done'] = False
    save_tasks(username, tasks)
    return redirect(url_for('todo'))

# Delete task
@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    username = session['username']
    tasks = load_tasks(username)
    del tasks[task_id]
    save_tasks(username, tasks)
    return redirect(url_for('todo'))

# Mark subtask as done
@app.route('/mark_subtask_done/<int:task_id>/<int:subtask_id>', methods=['POST'])
def mark_subtask_done(task_id, subtask_id):
    username = session['username']
    tasks = load_tasks(username)
    subtask = tasks[task_id]['subtasks'][subtask_id]
    subtask['done'] = True
    save_tasks(username, tasks)
    return jsonify({'message': f"You completed the subtask: {subtask['subtask']}"}), 200

# Mark subtask as undone
@app.route('/unmark_subtask_done/<int:task_id>/<int:subtask_id>', methods=['POST'])
def unmark_subtask_done(task_id, subtask_id):
    username = session['username']
    tasks = load_tasks(username)
    subtask = tasks[task_id]['subtasks'][subtask_id]
    subtask['done'] = False
    save_tasks(username, tasks)
    return redirect(url_for('todo'))

# --------------------------------------------------------------------------------------------------------------------------->
# Diary_webiste

app.config['SECRET_KEY'] = 'your_secret_key'  # For flash messages
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mp4', 'wav'}

# Initialize the Hugging Face emotion detection pipeline
emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base")

# Path to the JSON file where entries are stored
DIARY_FILE_PATH = 'diary_entries.json'

# Load existing diary entries from JSON file
def load_entries():
    try:
        with open(DIARY_FILE_PATH, 'r') as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
            else:
                return {}  # Return an empty dictionary if the file structure is incorrect
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dictionary if the file doesn't exist or has errors


def save_entries(entries):
    with open(DIARY_FILE_PATH, 'w') as file:
        json.dump(entries, file, indent=4)


# Sentiment analysis function (TextBlob)
def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # Returns a value between -1 (negative) and 1 (positive)
    if sentiment > 0:
        return "Positive"
    elif sentiment < 0:
        return "Negative"
    else:
        return "Neutral"

# Emotion detection function using Hugging Face model
def detect_emotion(text):
    result = emotion_classifier(text)
    emotion = result[0]['label']
    return emotion

# Create the uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Home route (Index Page)
@app.route('/diary')
def diary():
    return render_template('diary.html')

# Route to handle new diary entry submission
@app.route('/add-entry', methods=['GET', 'POST'])
def add_entry():
    if 'username' not in session:
        flash("You must be logged in to add entries.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'] or datetime.now().strftime("%Y-%m-%d")
        content = request.form['content']
        files = request.files.getlist('attachments')

        # Handle file uploads
        file_paths = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                file_paths.append('uploads/' + filename)  # Store relative path for easier use

        sentiment = analyze_sentiment(content)
        emotion = detect_emotion(content)

        entry = {
            'title': title,
            'content': content,
            'sentiment': sentiment,
            'emotion': emotion,
            'attachments': file_paths,
            'date_created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        entries = load_entries()
        username = session['username']
        if username not in entries:
            entries[username] = []
        entries[username].append(entry)
        save_entries(entries)

        return redirect(url_for('dashboard'))

    return render_template('add_entry.html')




# Route to view all diary entries (Dashboard)
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("You must be logged in to view the dashboard.")
        return redirect(url_for('login'))

    entries = load_entries()
    username = session['username']
    user_entries = entries.get(username, [])

    # Prepare sentiment and emotion data for the chart
    sentiment_data = []
    emotion_data = []
    for entry in user_entries:
        sentiment = entry.get('sentiment', '')
        emotion = entry.get('emotion', '')

        sentiment_value = 1 if sentiment == 'Positive' else -1 if sentiment == 'Negative' else 0
        sentiment_data.append(sentiment_value)
        emotion_data.append(emotion)

    return render_template('dashboard.html', entries=user_entries, sentiment_data=sentiment_data, emotion_data=emotion_data)

# Route to view individual entry in detail
@app.route('/entry/<int:index>', methods=['GET'])
def view_entry(index):
    if 'username' not in session:
        flash("You must be logged in to view entries.")
        return redirect(url_for('login'))

    entries = load_entries()
    username = session['username']
    user_entries = entries.get(username, [])

    if index >= len(user_entries):
        flash("Entry not found.")
        return redirect(url_for('dashboard'))

    entry = user_entries[index]
    return render_template('view_entry.html', entry=entry, index=index)

# Route to delete an entry
@app.route('/delete-entry/<int:index>', methods=['POST'])
def delete_entry(index):
    entries = load_entries()
    del entries[index]
    save_entries(entries)
    return redirect(url_for('dashboard'))

# -------------------------------------------------------------------------------------------------------->
# Habit-tracker

# Path to the data directory and JSON file
HABITS_FILE = os.path.join('habits.json')

# Helper functions for reading and writing JSON
# Helper functions for reading and writing JSON
def read_habits():
    """Read habits for all users from the habits JSON file."""
    if os.path.exists(HABITS_FILE):
        with open(HABITS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):  # If the data is in list format, migrate it to dictionary format
                return {"default_user": data}
            return data  # Return habits as a dictionary
    return {}  # Return an empty dictionary if the file doesn't exist

def write_habits(habits):
    """Write habits to the JSON file."""
    with open(HABITS_FILE, 'w') as f:
        json.dump(habits, f, indent=4)  # Write habits as a dictionary
        
def habit_duration(start_date):
    """Calculate the duration in days from the start date."""
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')  # Convert string to datetime object
    today = datetime.today()  # Get the current date
    duration = (today - start_date_obj).days  # Calculate the difference in days
    return duration

def calculate_days_done(habit):
    """Calculate the number of days the habit has been done based on completed dates."""
    return len(habit['completed'])

def calculate_days_skipped(habit):
    """Calculate the number of days the habit has been skipped based on target days."""
    duration = habit_duration(habit['start_date'])
    days_done = calculate_days_done(habit)
    return max(0, duration - days_done)  # Ensure no negative values

# User-specific habit management
def get_user_habits():
    """Get habits for the logged-in user."""
    user = session.get('username')  # Get the username from the session
    habits = read_habits()  # Read all habits
    if isinstance(habits, dict):
        return habits.get(user, [])  # Return habits for the logged-in user
    return []  # Return an empty list if no habits are found for this user

def write_user_habits(habits):
    """Write habits for the logged-in user."""
    user = session.get('username')  # Get the logged-in user's username from the session
    all_habits = read_habits()  # Read all habits

    if isinstance(all_habits, list):  # If existing structure is a list, migrate it
        all_habits = {"default_user": all_habits}

    all_habits[user] = habits  # Update the habits for the logged-in user
    write_habits(all_habits)

@app.route('/habit_track')
def habit_track():
    """Display the list of habits for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    habits = get_user_habits()
    for habit in habits:
        if 'start_date' not in habit:
            habit['start_date'] = datetime.today().strftime('%Y-%m-%d')
        habit['duration'] = habit_duration(habit['start_date'])
        habit['days_done'] = calculate_days_done(habit)
        habit['days_skipped'] = calculate_days_skipped(habit)

    return render_template('habit_track.html', habits=habits)

@app.route('/add', methods=['GET', 'POST'])
def add_habit():
    """Add a new habit for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        habit = {
            "id": len(get_user_habits()) + 1,
            "name": request.form['name'],
            "category": request.form['category'],
            "frequency": request.form['frequency'],
            "goal": int(request.form['goal']),
            "completed": [],
            "start_date": datetime.today().strftime('%Y-%m-%d')
        }

        user_habits = get_user_habits()
        user_habits.append(habit)
        write_user_habits(user_habits)
        return redirect(url_for('habit_track'))
    return render_template('add_habit.html')

@app.route('/edit/<int:habit_id>', methods=['GET', 'POST'])
def edit_habit(habit_id):
    """Edit a habit for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    habits = get_user_habits()
    habit = next((h for h in habits if h['id'] == habit_id), None)

    if habit is None:
        return "Habit not found", 404

    if request.method == 'POST':
        habit.update({
            "name": request.form['name'],
            "category": request.form['category'],
            "frequency": request.form['frequency'],
            "goal": int(request.form['goal'])
        })
        write_user_habits(habits)
        return redirect(url_for('habit_track'))

    return render_template('edit_habit.html', habit=habit)

@app.route('/toggle/<int:habit_id>', methods=['GET'])
def toggle_habit(habit_id):
    """Toggle the completion status of a habit for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    habits = get_user_habits()
    habit = next((h for h in habits if h['id'] == habit_id), None)

    if habit is None:
        return "Habit not found", 404

    today = datetime.today().strftime('%Y-%m-%d')
    if today in habit['completed']:
        habit['completed'].remove(today)
    else:
        habit['completed'].append(today)

    write_user_habits(habits)
    return redirect(url_for('habit_track'))

@app.route('/delete/<int:habit_id>', methods=['GET'])
def delete_habit(habit_id):
    """Delete a habit for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    habits = get_user_habits()
    habit = next((h for h in habits if h['id'] == habit_id), None)

    if habit is None:
        return "Habit not found", 404

    habits.remove(habit)
    write_user_habits(habits)
    return redirect(url_for('habit_track'))

@app.route('/log/<int:habit_id>')
def habit_log(habit_id):
    """Display the log details of a specific habit for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))

    habits = get_user_habits()
    habit = next((h for h in habits if h['id'] == habit_id), None)

    if habit is None:
        return "Habit not found", 404

    habit['duration'] = habit_duration(habit['start_date'])
    habit['days_done'] = calculate_days_done(habit)
    habit['days_skipped'] = calculate_days_skipped(habit)

    return render_template('habit_log.html', habit=habit)


if __name__ == '__main__':
    app.run(debug=True)
