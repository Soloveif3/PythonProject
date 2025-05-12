from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

class UploadFileForm(FlaskForm):
    file = FileField('Файл', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'pdf', 'docx', 'xlsx', 'txt', 'zip', 'rar'],
                  'Разрешены только документы и изображения')
    ])
    target_folder = SelectField('Папка назначения', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Загрузить')

class CreateFolderForm(FlaskForm):
    folder_name = StringField('Имя папки', validators=[DataRequired()])
    parent_folder = SelectField('Родительская папка', coerce=str)
    submit = SubmitField('Создать')

class SearchForm(FlaskForm):
    query = StringField('Поиск')
    submit = SubmitField('Найти')