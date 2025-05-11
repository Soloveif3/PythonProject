from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Optional


class UploadFileForm(FlaskForm):
    file = FileField('Файл', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'pdf', 'docx', 'xlsx', 'txt'], 'Разрешены только документы и изображения')
    ])
    submit = SubmitField('Загрузить')

class CreateFolderForm(FlaskForm):
    folder_name = StringField('Имя папки', validators=[DataRequired()])
    submit = SubmitField('Создать')

class SearchForm(FlaskForm):
    query = StringField('Поиск')
    submit = SubmitField('Найти')