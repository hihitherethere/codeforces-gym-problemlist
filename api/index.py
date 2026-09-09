from flask import Flask, render_template, redirect, session, request
import uuid as uuidlib
import requests
import time
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

FLASK_SECRET_KEY = os.environ["FLASK_SECRET_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect("/admin")
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
                addedtime = int(time.time())

                supabase.table("PROBLEMSET").insert({
                    "name": name,
                    "link": link,
                    "contestlink": contestlink,
                    "contestname": contestname,
                    "problemindex": index,
                    "contestid": contestid,
                    "rating": int(rating) if rating else None,
                    "votes": 1,
                    "addedtime": addedtime
                }).execute()
            return redirect('/admin')

        name = request.form.get('name')
        link = request.form.get('link')
        contestlink = request.form.get('contestlink')
        contestname = request.form.get('contestname')
        rating = request.form.get('rating', None)
        index = request.form.get('index')
        contestid = request.form.get('contestid')
        addtype = request.form.get('addtype')
        bulkcontestid = request.form.get('bulkcontestid')

        if addtype == "bulkadd":
            try:
                r = requests.get(f"https://codeforces.com/api/contest.standings?contestId={bulkcontestid}&from=1&count=10000")
                data = r.json()
                if data["status"] != "OK":
                    return "Failed to fetch contest problems", 400

                problems = data["result"]["problems"]
                contestname = data["result"]["contest"]["name"]
                return render_template("bulkadd.html", problems=problems, contestname=contestname, contestid=bulkcontestid)
            except Exception as e:
                return f"Error fetching contest problems: {e}", 500

        if not link and contestlink and index:
            link = f"{contestlink}/problem/{index}"

        existing = supabase.table("PROBLEMSET").select("*") \
            .eq("contestid", contestid).eq("problemindex", index).execute().data

        if existing:
            votes = existing[0]["votes"] + 1
            supabase.table("PROBLEMSET").update({
                "name": name,
                "link": link,
                "contestlink": contestlink,
                "contestname": contestname,
                "rating": int(rating) if rating else None,
                "votes": votes
            }).eq("contestid", contestid).eq("problemindex", index).execute()
        else:
            supabase.table("PROBLEMSET").insert({
                "name": name,
                "link": link,
                "contestlink": contestlink,
                "contestname": contestname,
                "rating": int(rating) if rating else None,
                "votes": 1,
                "addedtime": int(time.time()),
                "problemindex": index,
                "contestid": contestid
            }).execute()

    return render_template("admin.html")

@app.route('/')
def index():
    return redirect('/table')

@app.route('/table/<handle>', methods=['GET', 'POST'])
@app.route('/table', methods=['GET', 'POST'])
def user_problemset(handle=None):
    if request.method == 'POST':
        handle = request.form.get('handle')
        if handle:
            return redirect('/table/' + handle)
        return redirect('/table')

    solved_keys = set()
    page = int(request.args.get("page", 1))
    min_rating = request.args.get("min_rating", None, type=int)
    max_rating = request.args.get("max_rating", None, type=int)
    PAGE_SIZE = 100

    if handle:
        r = requests.get(f"https://codeforces.com/api/user.status?handle={handle}")
        data = r.json()
        if data["status"] == "OK":
            for sub in data["result"]:
                if sub.get("verdict") == "OK":
                    prob = sub["problem"]
                    key = f'{prob.get("contestId")}-{prob.get("index")}'
                    solved_keys.add(key)

    query = supabase.table("PROBLEMSET").select("*")

    if min_rating is not None:
        query = query.gte("rating", min_rating)
    if max_rating is not None:
        query = query.lte("rating", max_rating)

    # Order and paginate
    query = query.order("addedtime", desc=True).order("problemindex", desc=False).range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1)
    problems = query.execute().data

    problem_list = []
    for p in problems:
        key = f'{p["contestid"]}-{p["problemindex"]}'
        is_solved = key in solved_keys
        problem_list.append((p, is_solved))

    return render_template("problemset.html", problems=problem_list, handle=handle, page=page,
                           min_rating=min_rating, max_rating=max_rating)
