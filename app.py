import bottle_mysql
from MySQLdb._exceptions import IntegrityError
from bottle import run, template, request, redirect, static_file, Bottle
import re

app = Bottle()
plugin = bottle_mysql.Plugin(dbuser='root', dbpass="82134",
                             dbname='todo')
app.install(plugin)


def validate_email(email):
    pattern = re.compile(r'\w+\@\w+\.\w+')
    match = re.fullmatch(pattern, email)
    if match:
        return True
    else:
        return False


@app.get('/registration')
def registration():
    return template('registration', msg='')


@app.post('/registration')
def registration(db):
    if request.POST.save:
        name = request.POST.first_name.strip()
        surname = request.POST.surname.strip()
        email = request.POST.email.strip()
        login = request.POST.login.strip()
        password = request.POST.password.strip()

        if not validate_email(email):
            msg = 'Неверный формат email'
            return template('registration', msg=msg)

        if len(password) < 8:
            msg = 'Пароль должен быть не менее 8 символов'
            return template('registration', msg=msg)

        try:
            db.execute(
                "INSERT INTO todo.users(Name,Surname,Email,Login, Password"
                ") VALUES (%s, %s, %s, %s, %s);", (name, surname, email,
                                                   login, password))
        except IntegrityError as e:
            return template('registration', msg=str(e).split(',')[1][2:-2])

        return redirect("/todo")


@app.get('/login')
def sign_in():
    return template('login', msg='')


@app.post('/login')
def sign_in(db):
    if request.POST.save:
        login = request.POST.login.strip()
        password = request.POST.password.strip()

        db.execute("SELECT Name, Surname, Email, Login, Password FROM "
                   "todo.users WHERE Login LIKE %s;", (login,))

        user = db.fetchone()
        if password == user['Password']:
            print(user)
            return redirect("/todo")
        else:
            return template('login', msg='Неправильный пароль')


@app.get('/todo')
def todo_list(db):
    db.execute(
        "SELECT ID_tasks, Task FROM todo.tasks  WHERE Status LIKE '1';")
    rows = db.fetchall()
    if rows:
        return template('table', rows=rows, msg='')
    return "<b>Задач нет</b>"


@app.get('/done')
def done_list(db):
    db.execute("SELECT ID_tasks, Task FROM todo.tasks WHERE Status LIKE '0'")
    rows = db.fetchall()
    if rows:
        return template('table', rows=rows, msg='')
    return "<b>Задач нет</b>"


@app.post('/new')
def new_item(db):
    if request.POST.save:
        new = request.POST.task.strip()
        db.execute("INSERT INTO todo.tasks(Task, Status) VALUES (%s,%s);",
                   (new, 1))
        return redirect("/todo")


@app.get('/new')
def new_item():
    return template('new_task.tpl')


@app.post('/edit/<no:int>')
def edit_item(no, db):
    if request.POST.save:
        edit = request.POST.task.strip()
        status = request.POST.status.strip()

        if status == 'нужно сделать':
            status = 1
        else:
            status = 0

        db.execute(
            "UPDATE todo.tasks SET Task = %s, Status = %s WHERE ID_tasks "
            "LIKE %s;",
            (edit, status, no))
        return f'<p>Задача под номером {no} успешно обновлена</p><a ' \
               f'href="/todo"></a>'


@app.get('/edit/<no:int>')
def edit_item(no, db):
    db.execute("SELECT Task FROM todo.tasks WHERE ID_tasks LIKE %s;",
               (no,))
    cur_data = db.fetchone()
    return template('edit_task', old=list(cur_data.values())[0], no=no)


@app.post('/del/<no:int>')
def del_task(no, db):
    try:
        db.execute(
            "DELETE FROM todo.tasks WHERE ID_tasks LIKE %s;", (no,))
    except:
        return f'<p>Задачу под номером {no} удалить не удалось</p>'
    return f'<p>Задача под номером {no} успешно удалена</p>'


@app.route('/static/:filename#.*#')
def send_static(filename):
    return static_file(filename, root='./static/')


@app.error(403)
def mistake403(err):
    return 'Неверный формат передаваемого параметра!'


@app.error(404)
def mistake404(err):
    return f'Ошибка 404. Данной страницы не существует!'


run(app, reloader=True, debug=True)
