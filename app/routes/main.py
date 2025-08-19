from flask import Blueprint, redirect, url_for, render_template, current_app, send_from_directory
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
                                          
    return render_template("home.html")

@main_bp.route("/home")
def home():
    return render_template("home.html")

@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/catalog")
@login_required
def catalog():
    return render_template("catalog.html")


@main_bp.route("/sw.js")
def service_worker():
                                               
    return send_from_directory(current_app.static_folder, "sw.js")


