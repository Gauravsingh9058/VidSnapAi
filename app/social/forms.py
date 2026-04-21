import json

from flask_wtf import FlaskForm
from wtforms import HiddenField, RadioField, SubmitField
from wtforms.validators import DataRequired


class SelectSocialAccountForm(FlaskForm):
    selection_id = HiddenField("Selection id", validators=[DataRequired()])
    asset_key = RadioField("Available accounts", validators=[DataRequired()], choices=[])
    submit = SubmitField("Save connected account")

    def apply_assets(self, selection):
        payload = json.loads(selection.raw_assets_json)
        self.selection_id.data = selection.id
        self.asset_key.choices = [
            (
                asset["asset_key"],
                f"{asset['account_name']}|{asset.get('username') or ''}|{asset.get('page_name') or ''}|{asset['account_id']}",
            )
            for asset in payload
        ]
