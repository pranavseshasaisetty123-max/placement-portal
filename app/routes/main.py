from flask import Blueprint, render_template

# main blueprint — public pages that do not require authentication.
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html")
