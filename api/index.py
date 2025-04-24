from flask import Flask, render_template, redirect, session, request
import uuid as uuidlib
import requests
import json
import sqlite3
import time

app = Flask(__name__)
conn = sqlite3.connect('user.db',check_same_thread=False)
db = conn.cursor()
app.secret_key = "super_secret_key"

@app.route('/reset')
def reset():
    db.execute("DROP TABLE IF EXISTS PROBLEMSET")
    db.execute('''
        CREATE TABLE PROBLEMSET (
            problemid INTEGER PRIMARY KEY NOT NULL,
            name STRING NOT NULL,
            link STRING,
            contestid INT,
            contestname STRING,
            rating INT,
            quality INT,
            addedtime INT NOT NULL,
            contesttime INT
            )
        ''')
    conn.commit()
    return redirect('/')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'a' and request.form['password'] == 'a':
            session['admin'] = True
            return redirect('/admin')
        else:
            return "Invalid credentials", 403
    return '''
    <form method="post">
        <input name="username" placeholder="Username">
        <input name="password" type="password" placeholder="Password">
        <button type="submit">Login</button>
    </form>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin'):
        return redirect('/admin/login')

    if request.method == 'POST':
        name = request.form['name']
        link = request.form['link']
        contestname = request.form['contestname']
        rating = request.form.get('rating', None)
        quality = request.form.get('quality', None)
        contestid = request.form.get('contestid', None)
        addedtime = int(request.form.get('addedtime', 0) or time.time())

        db.execute('''
            INSERT INTO PROBLEMSET (name, link, contestname, rating, quality, addedtime, contestid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, link, contestname, rating, quality, addedtime, contestid))
        conn.commit()

    return '''
    <h1>Admin Panel</h1>
    <form method="post">
        <input name="name" placeholder="Problem Name" required><br>
        <input name="link" placeholder="Problem Link"><br>
        <input name="contestname" placeholder="Contest Name"><br>
        <input name="rating" type="number" placeholder="Rating"><br>
        <input name="quality" type="number" placeholder="Quality"><br>
        <input name="contestid" type="number" placeholder="Contest ID"><br>
        <input name="addedtime" type="number" placeholder="Timestamp (leave blank for now)"><br>
        <button type="submit">Add Problem</button>
    </form>
    <br>
    <a href="/admin/logout">Logout</a>
    '''

@app.route('/')
def index():
    return redirect('/table')

@app.route('/table/<handle>', methods=['GET', 'POST'])
@app.route('/table', methods=['GET', 'POST'])
def user_problemset(handle=None):
    if request.method == 'POST':
        print("hi")
        handle = request.form.get('handle')
        if handle == None:
            return redirect('/table')
        return redirect('/table/' + handle)

    # Get solved problems from Codeforces API
    solved_keys = set()

    if handle != None:
        r = requests.get(f"https://codeforces.com/api/user.status?handle={handle}")
        data = r.json()

        if data["status"] == "OK":
            for sub in data["result"]:
                if sub.get("verdict") == "OK":
                    prob = sub["problem"]
                    key = f'{prob.get("contestId")}-{prob.get("index")}'
                    solved_keys.add(key)

    # Get problem list
    db.execute("SELECT * FROM PROBLEMSET ORDER BY addedtime DESC")
    problems = db.fetchall()

    # Pair each problem with its solved status
    problem_list = []
    for p in problems:
        # assuming p[0]=index, p[8]=contestId
        key = f'{p[3]}-{p[0]}'
        is_solved = key in solved_keys
        problem_list.append((p, is_solved))

    return render_template("problemset.html", problems=problem_list, handle=handle)