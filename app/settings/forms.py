from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    submit = SubmitField("Save profile")


class PasswordUpdateForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired(), Length(min=8, max=128)])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new_password")])
    submit = SubmitField("Update password")


class NotificationForm(FlaskForm):
    notify_product_updates = BooleanField("Product updates")
    notify_scheduled_posts = BooleanField("Scheduled post reminders")
    notify_failures = BooleanField("Publishing failure alerts")
    submit = SubmitField("Save notifications")


class DeleteAccountForm(FlaskForm):
    confirm_text = StringField("Type DELETE to confirm", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Delete account")
