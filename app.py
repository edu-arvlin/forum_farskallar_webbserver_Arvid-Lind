
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "forum-farskallar-nyckel"


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="forum_farskallar"
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Fyll i både användarnamn och lösenord.", "error")
            return redirect(url_for("register"))

        if len(username) > 50:
            flash("Användarnamnet får vara högst 50 tecken.", "error")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )

            conn.commit()

        except mysql.connector.IntegrityError:
            flash("Användarnamnet är redan upptaget.", "error")
            return redirect(url_for("register"))

        finally:
            cur.close()
            conn.close()

        flash("Kontot har skapats! Du kan nu logga in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and user["password"] == password:

            session["username"] = user["username"]
            session["user_id"] = user["id"]

            return redirect(url_for("index"))

        flash("Fel användarnamn eller lösenord.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


@app.route("/topics")
def topics():

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT topics.id, topics.title, topics.created_at, users.username
        FROM topics
        JOIN users ON topics.user_id = users.id
        ORDER BY topics.created_at DESC, topics.id DESC
    """)

    topic_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("topics.html", topics=topic_list)


@app.route("/create_topic", methods=["GET", "POST"])
def create_topic():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"].strip()
        content = request.form["content"].strip()

        if not title or not content:
            flash("Fyll i både rubrik och inlägg.", "error")
            return redirect(url_for("create_topic"))

        if len(title) > 150:
            flash("Rubriken får vara högst 150 tecken.", "error")
            return redirect(url_for("create_topic"))

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO topics (title, user_id) VALUES (%s, %s)",
                (title, session["user_id"])
            )

            topic_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO posts (content, user_id, topic_id)
                VALUES (%s, %s, %s)
                """,
                (content, session["user_id"], topic_id)
            )

            conn.commit()

        except Exception:
            conn.rollback()
            flash("Det gick inte att skapa diskussionen.", "error")
            return redirect(url_for("create_topic"))

        finally:
            cur.close()
            conn.close()

        return redirect(url_for("topic", topic_id=topic_id))

    return render_template("create_topic.html")


@app.route("/topic/<int:topic_id>", methods=["GET", "POST"])
def topic(topic_id):

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT topics.id, topics.title, topics.created_at, users.username
        FROM topics
        JOIN users ON topics.user_id = users.id
        WHERE topics.id = %s
    """, (topic_id,))

    current_topic = cur.fetchone()

    if current_topic is None:
        cur.close()
        conn.close()
        return "Diskussionen kunde inte hittas.", 404

    if request.method == "POST":

        if "user_id" not in session:
            cur.close()
            conn.close()
            return redirect(url_for("login"))

        content = request.form["content"].strip()

        if not content:
            flash("Du kan inte skicka ett tomt inlägg.", "error")
            cur.close()
            conn.close()
            return redirect(url_for("topic", topic_id=topic_id))

        cur.execute(
            """
            INSERT INTO posts (content, user_id, topic_id)
            VALUES (%s, %s, %s)
            """,
            (content, session["user_id"], topic_id)
        )

        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for("topic", topic_id=topic_id))

    cur.execute("""
        SELECT posts.content, posts.created_at, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.topic_id = %s
        ORDER BY posts.created_at ASC, posts.id ASC
    """, (topic_id,))

    posts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "topic.html",
        topic=current_topic,
        posts=posts
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
