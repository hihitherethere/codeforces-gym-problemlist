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
    # db.execute("DROP TABLE IF EXISTS PROBLEMSET")
    db.execute('''
        CREATE TABLE IF NOT EXISTS PROBLEMSET (
            problemid INTEGER PRIMARY KEY NOT NULL,
            name STRING NOT NULL,
            link STRING NOT NULL,
            contestlink STRING NOT NULL,
            contestname STRING NOT NULL,
            problemindex STRING NOT NULL,
            contestid STRING NOT NULL,
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
        # Check if bulk add form is submitted
        count = int(request.form.get('count', 0))
        if count > 0:
            contestlink = request.form.get('contestlink')
            contestname = request.form.get('contestname')
            contestid = request.form.get('contestid')

            for i in range(count):
                name = request.form.get(f'name_{i}')
                index = request.form.get(f'index_{i}')
                link = f"{contestlink}/problem/{index}"
                rating = request.form.get(f'rating_{i}', None)
                quality = request.form.get(f'quality_{i}', None)
                addedtime = int(time.time())

                db.execute('''
                    INSERT INTO PROBLEMSET (name, link, contestlink, contestname, problemindex, contestid, rating, quality, addedtime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, link, contestlink, contestname, index, contestid, rating, quality, addedtime))
            conn.commit()
            return redirect('/admin')

        # Normal single problem add
        name = request.form.get('name')
        link = request.form.get('link')
        contestlink = request.form.get('contestlink')
        contestname = request.form.get('contestname')
        rating = request.form.get('rating', None)
        quality = request.form.get('quality', None)
        index = request.form.get('index', '')
        contestid = request.form.get('contestid')
        bulkcontestid = request.form.get('bulkcontestid')

        # If contestid is given but no name => fetch contest problems
        if bulkcontestid:
            try:
                r = requests.get(f"https://codeforces.com/api/contest.standings?contestId={bulkcontestid}&from=1&count=10000")
                data = r.json()
                if data["status"] != "OK":
                    return "Failed to fetch contest problems", 400

                problems = data["result"]["problems"]
                contestname = data["result"]["contest"]["name"]
                return render_template("bulkadd.html", problems=problems, contestname=contestname, contestid=contestid)
            except Exception as e:
                return f"Error fetching contest problems: {e}", 500

        # Build link if not given
        if not link and contestlink and index:
            link = f"{contestlink}/problem/{index}"

        # Check if problem exists
        db.execute("SELECT addedtime FROM PROBLEMSET WHERE contestid=? AND problemindex=?", (contestid, index))
        row = db.fetchone()
        print(contestid, index)
        if row:
            preserved_time = row[0]
            db.execute('''
                UPDATE PROBLEMSET
                SET name=?, link=?, contestlink=?, contestname=?, rating=?, quality=?
                WHERE contestid=? AND problemindex=?
            ''', (name, link, contestlink, contestname, rating, quality, contestid, index))
        else:
            addedtime = int(time.time())
            db.execute('''
                INSERT INTO PROBLEMSET (name, link, contestlink, contestname, rating, quality, addedtime, problemindex, contestid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, link, contestlink, contestname, rating, quality, addedtime, index, contestid))

        conn.commit()

    return render_template("admin.html")




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
        key = f'{p[6]}-{p[5]}'
        is_solved = key in solved_keys
        problem_list.append((p, is_solved))

    return render_template("problemset.html", problems=problem_list, handle=handle)

reset()