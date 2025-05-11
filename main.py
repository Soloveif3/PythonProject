from flask import Flask, render_template, request, make_response, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, current_user, logout_user
from data import db_session
import datetime
import os
from data.users import User
from forms.user import RegisterForm, LoginForm
from forms.page import UploadFileForm, CreateFolderForm, SearchForm
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = 'WEBPROject'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=62)

login_manager = LoginManager()
login_manager.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    upload_form = UploadFileForm()
    folder_form = CreateFolderForm()
    search_form = SearchForm()


    user_id = current_user.id
    __User_Folder = app.config['UPLOAD_FOLDER'] + 'user_' + str(user_id)
    user_id = current_user.id
    # Обработка загрузки файла
    if upload_form.validate_on_submit():
        file = upload_form.file.data
        filename = secure_filename(file.filename)
        file.save(os.path.join(__User_Folder, filename))
        flash('Файл успешно загружен', 'success')
        return redirect(url_for('index'))

    # Обработка создания папки
    if folder_form.validate_on_submit():
        folder_name = folder_form.folder_name.data
        folder_path = os.path.join(__User_Folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        flash(f'Папка "{folder_name}" создана', 'success')
        return redirect(url_for('index'))

    # Обработка поиска
    if search_form.validate_on_submit():
        query = search_form.query.data
        # Здесь будет логика поиска файлов
        flash(f'Результаты поиска по запросу: {query}', 'info')
        return redirect(url_for('index'))

    # Получаем список файлов для отображения
    files = []
    for filename in os.listdir(__User_Folder):
        path = os.path.join(__User_Folder, filename)
        if os.path.isfile(path):
            files.append({
                'name': filename,
                'size': os.path.getsize(path),
                'type': filename.split('.')[-1]
            })
        else:
            files.append({
                    'name': filename,
                    'size': os.path.getsize(path),
                    'type': filename.split('.')[-1]
            })
    return render_template('index.html',
                         upload_form=upload_form,
                         folder_form=folder_form,
                         search_form=search_form,
                         files=files)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Файл удален', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
@guest_required
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password = form.password.data
        if len(password) < 8:
            return render_template('register.html', title='Регистрация',
                                 form=form,
                                 message="Пароль должен быть больше восьми символов")
        if not any(c.isdigit() for c in password):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Добавьте хотя бы одну цифру")
        if not any(c.isupper() for c in password):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Добавьте хотя бы одну заглавную букву")
        if not any(c in "!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?" for c in password):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Добавьте хотя бы один спецсимвол")
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                 form=form,
                                 message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                 form=form,
                                 message="Такой пользователь уже есть")
        email = form.email.data
        user = User(
            name=form.name.data,
            email=email,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        user_id = user.id
        os.mkdir('uploads/user_' + str(user_id))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
@guest_required
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            # next_page = request.args.get('next')
            return redirect(url_for('index'))
        return render_template('login.html',
                             message="Неправильный логин или пароль",
                             form=form)
    return render_template('login.html', title='Авторизация', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    from waitress import serve
    db_session.global_init("db/blogs.db")
    app.run(port=8080, host='192.168.31.155')
    # serve(app, host="192.168.31.155", port=8080)