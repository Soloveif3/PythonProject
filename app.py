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


def get_user_folders(user_folder, current_path=''):
    full_path = os.path.join(user_folder, current_path)
    folders = []

    if os.path.exists(full_path):
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                rel_path = os.path.join(current_path, item)
                folders.append((rel_path, rel_path))
                folders.extend(get_user_folders(user_folder, rel_path))

    return folders


@app.route('/')
@login_required
def index():
    return browse('')


@app.route('/browse/')
@app.route('/browse/<path:path>')
@login_required
def browse(path):
    user_id = current_user.id
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    current_full_path = os.path.join(base_path, path)

    os.makedirs(base_path, exist_ok=True)

    path_parts = []
    accumulated_path = ''
    for part in path.split('/'):
        if part:
            accumulated_path = os.path.join(accumulated_path, part)
            path_parts.append({
                'name': part,
                'path': accumulated_path
            })

    files = []
    folders = []
    if os.path.exists(current_full_path):
        for item in os.listdir(current_full_path):
            item_path = os.path.join(current_full_path, item)
            item_rel_path = os.path.join(path, item) if path else item

            if os.path.isfile(item_path):
                files.append({
                    'name': item,
                    'path': item_rel_path,
                    'size': os.path.getsize(item_path),
                    'type': item.split('.')[-1].lower() if '.' in item else 'file'
                })
            elif os.path.isdir(item_path):
                folders.append({
                    'name': item,
                    'path': item_rel_path,
                    'type': 'folder'
                })
    return render_template('index.html',
                           upload_form=UploadFileForm(),
                           folder_form=CreateFolderForm(),
                           search_form=SearchForm(),
                           files=files,
                           folders=folders,
                           current_path=path,
                           path_parts=path_parts)


def redirect_back(path):
    if path:
        return redirect(url_for('browse', path=path))
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = current_user.id
    current_path = request.form.get('current_path', '')
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}', current_path)

    os.makedirs(target_dir, exist_ok=True)

    if 'file' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect_back(current_path)

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect_back(current_path)

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(target_dir, filename)

        if os.path.exists(file_path):
            flash('Файл с таким именем уже существует', 'danger')
        else:
            try:
                file.save(file_path)
                flash('Файл успешно загружен', 'success')
            except Exception as e:
                flash(f'Ошибка при загрузке : {str(e)}', 'danger')

    return redirect_back(current_path)


@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    user_id = current_user.id
    current_path = request.form.get('current_path', '')
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}', current_path)
    folder_name = secure_filename(request.form.get('folder_name', ''))

    if not folder_name:
        flash('Введите имя папки', 'danger')
        return redirect(url_for('browse', path=current_path))

    new_folder_path = os.path.join(target_dir, folder_name)

    if os.path.exists(new_folder_path):
        flash('Папка с таким именем уже существует', 'danger')
    else:
        try:
            os.makedirs(new_folder_path)
            flash('Папка успешно создана', 'success')
        except Exception as e:
            flash(f'Ошибка при создании папки: {str(e)}', 'danger')
    if current_path:
        return redirect(url_for('browse', path=current_path))
    return redirect(url_for('index'))


@app.route('/download/<path:path>')
@login_required
def download(path):
    user_id = current_user.id
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    file_path = os.path.join(base_path, path)

    if os.path.isfile(file_path):
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=True
        )
    else:
        flash('Файл не найден', 'danger')
        return redirect(url_for('browse', path=os.path.dirname(path)))


@app.route('/delete_item/<path:path>', methods=['POST'])
@login_required
def delete_item(path):
    user_id = current_user.id
    current_path = request.form.get('current_path', '')
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    target_path = os.path.join(base_path, path)

    try:
        if os.path.isfile(target_path):
            os.remove(target_path)
            flash('Файл удален', 'success')
        elif os.path.isdir(target_path):
            if not os.listdir(target_path):
                os.rmdir(target_path)
                flash('Папка удалена', 'success')
            else:
                flash('Папка не пуста. Удалите сначала содержимое.', 'danger')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'danger')

    return redirect_back(current_path)


@app.route('/watch_item/<path:path>', methods=['POST'])
@login_required
def watch_item(path):
    user_id = current_user.id
    current_path = request.form.get('current_path', '')
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    target_path = os.path.join(base_path, path)

    try:
        return redirect_back(current_path)
    except Exception as e:
        flash(f'Ошибка при просмотре: {str(e)}', 'danger')
        return redirect_back(current_path)





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
        print()
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
        user_fl_nm = 'user_' + str(user_id)
        __User_Folder = app.config['UPLOAD_FOLDER'] + user_fl_nm
        if user_fl_nm not in os.listdir(app.config['UPLOAD_FOLDER']):
            os.mkdir(__User_Folder)
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
    db_session.global_init("db/blogs.db")
    app.run(debug=True)