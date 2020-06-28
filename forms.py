from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.widgets import TextArea

class LoginForm(FlaskForm):
    username = StringField('Username',
                        validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UploadForm(FlaskForm):
    CSV_file = FileField(validators=[FileRequired(), FileAllowed(['csv', 'CSV', 'tar.gz', 'zip'],
    	                                                        'CSV, zip, or tar.gz files only!')])
    submit = SubmitField('Submit')

class PastedTextForm(FlaskForm):
    csvtext = TextAreaField('CSVText', validators=[DataRequired()], widget=TextArea() )
    submit = SubmitField('Submit')