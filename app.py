from beaker.middleware import SessionMiddleware
import bottle_mysql
from bottle import run, template, request, redirect, static_file, Bottle
import re

session_opts = {
    'session.type': 'ext:database',
    'session.cookie_expires': True,
    'session.url': 'mysql://root:82134@localhost:3306/todo',
    'session.timeout': 300,
}
bottle_app = Bottle()
plugin = bottle_mysql.Plugin(dbuser='root', dbpass="82134",
                             dbname='todo')
bottle_app.install(plugin)

app = SessionMiddleware(bottle_app, session_opts)


def validate_email(email):
    pattern = re.compile(r'^\w{3,}@\w{2,}\.\w{2,4}$')
    match = re.fullmatch(pattern, email)
    return True if match else False


def is_auth():
    s = request.environ.get('beaker.session')
    user_id = 'user_id' in s
    return True if user_id else False


def exist(db, value, kind):
    if kind == 'Login':
        db.execute("SELECT ID_user FROM "
                   "todo.users WHERE Login LIKE %s;", (value,))
    elif kind == 'Email':
        db.execute("SELECT ID_user FROM "
                   "todo.users WHERE Email LIKE %s;", (value,))
    item = db.fetchone()

    return False if item is None else True


@bottle_app.get('/')
def main():
    return template('main', msg='')


@bottle_app.get('/registration')
def registration():
    return template('registration', msg='', data='')


@bottle_app.post('/registration')
def registration(db):
    name = request.POST.first_name.strip()
    surname = request.POST.surname.strip()
    email = request.POST.email.strip()
    login = request.POST.login.strip()
    password1 = request.POST.password1.strip()
    password2 = request.POST.password2.strip()

    data = {'name': name, 'surname': surname, 'email': email, 'login': login}

    if exist(db, email, 'Email'):
        msg = 'Данный email уже используется'
        return template('registration', msg=msg, data=data)
    elif not validate_email(email):
        msg = 'Неверный формат email'
        return template('registration', msg=msg, data=data)
    elif exist(db, login, 'Login'):
        msg = 'Данный логин уже используется'
        return template('registration', msg=msg, data=data)
    elif len(password1) < 8:
        msg = 'Пароль должен быть не менее 8 символов'
        return template('registration', msg=msg, data=data)
    elif password1 != password2:
        msg = 'Пароли не совпадают'
        return template('registration', msg=msg, data=data)

    db.execute(
        "INSERT INTO todo.users(Name,Surname,Email,Login, Password) VALUES (%s, %s, %s, %s, %s);",
        (name, surname, email, login, password1))

    db.execute("SELECT ID_user FROM todo.users WHERE Login LIKE %s;", (login,))
    user = db.fetchone()

    s = request.environ.get('beaker.session')
    s['user_id'] = f'{user["ID_user"]}'
    s.save()
    msg = 'Вы успешно зарегистрировались'
    return template('table', rows='', msg=msg)


@bottle_app.get('/login')
def sign_in():
    return template('login', msg='')


@bottle_app.post('/login')
def sign_in(db):
    login = request.POST.login.strip()
    password = request.POST.password.strip()

    db.execute("SELECT ID_user, Login, Password FROM "
               "todo.users WHERE Login LIKE %s;", (login,))
    user = db.fetchone()
    if user:
        if password == user['Password']:
            s = request.environ.get('beaker.session')
            s['user_id'] = f'{user["ID_user"]}'
            s.save()
            msg = 'Вы успешно вошли'
            return template('table', rows='', msg=msg)
        else:
            return template('login', msg='Неправильный пароль')
    else:
        return template('login', msg='Не удалось найти пользователя с '
                                     'таким именем')


@bottle_app.get('/logout')
def sign_out():
    s = request.environ.get('beaker.session')
    s.delete()
    msg = 'Вы успешно вышли'
    return template('main', msg=msg)


@bottle_app.get('/todo')
def todo_list(db):
    if not is_auth():
        return redirect('/login')
    else:
        s = request.environ.get('beaker.session')
        user_id = s['user_id']
        db.execute(
            "SELECT ID_tasks, Task FROM todo.tasks  WHERE Status = '1' AND "
            "ID_user = %s;", (user_id,))
        rows = db.fetchall()
        return template('table', rows=rows, msg='')


@bottle_app.get('/done')
def done_list(db):
    if not is_auth():
        return redirect('/login')
    else:
        s = request.environ.get('beaker.session')
        user_id = s['user_id']
        db.execute(
            "SELECT ID_tasks, Task FROM todo.tasks WHERE Status LIKE '0' AND ID_user = %s;",
            (user_id,))
        rows = db.fetchall()
        return template('table', rows=rows, msg='')


@bottle_app.post('/new')
def new_item(db):
    if not is_auth():
        return redirect('/login')
    else:
        s = request.environ.get('beaker.session')
        user_id = s['user_id']
        new = request.POST.task.strip()
        db.execute("INSERT INTO todo.tasks(Task, Status, ID_user) VALUES ("
                   "%s,%s,%s);",
                   (new, 1, user_id))
        msg = 'Задача успешно создана'
        return template("table", rows='', msg=msg)


@bottle_app.get('/new')
def new_item():
    if not is_auth():
        return redirect('/login')
    else:
        return template('new_task.tpl')


@bottle_app.post('/edit/<no:int>')
def edit_item(no, db):
    if not is_auth():
        return redirect('/login')
    else:
        s = request.environ.get('beaker.session')
        user_id = s['user_id']

        edit = request.POST.task.strip()
        status = request.POST.status.strip()

        status = 1 if status == 'нужно сделать' else 0

        db.execute(
            "UPDATE todo.tasks SET Task = %s, Status = %s WHERE ID_tasks = "
            "%s AND ID_user = %s;",
            (edit, status, no, user_id))

        msg = f'Задача под номером {no} успешно обновлена'
        return template("table", rows='', msg=msg)


@bottle_app.get('/edit/<no:int>')
def edit_item(no, db):
    if not is_auth():
        return redirect('/login')
    else:
        s = request.environ.get('beaker.session')
        user_id = s['user_id']
        db.execute("SELECT Task FROM todo.tasks WHERE ID_tasks = %s AND "
                   "ID_user = %s;",
                   (no, user_id))
        cur_data = db.fetchone()
        return template('edit_task', old=list(cur_data.values())[0], no=no)


@bottle_app.post('/del/<no:int>')
def del_task(no, db):
    if not is_auth():
        return redirect('/login')
    else:
        try:
            s = request.environ.get('beaker.session')
            user_id = s['user_id']
            db.execute(
                "DELETE FROM todo.tasks WHERE ID_tasks = %s AND "
                "ID_user = %s;", (no, user_id))
            msg = 'Задача успешно удалена'
        except:
            msg = 'Ошибка при удалении. Попробуйте еще раз'
        return template("table", rows='', msg=msg)


@bottle_app.route('/static/:filename#.*#')
def send_static(filename):
    return static_file(filename, root='./static/')


@bottle_app.error(403)
def mistake403(err):
    return 'Неверный формат передаваемого параметра!'


@bottle_app.error(404)
def mistake404(err):
    return 'Ошибка 404. Данной страницы не существует!'


run(app=app, host='localhost', port='8000',
    debug=True,
    reloader=True)
