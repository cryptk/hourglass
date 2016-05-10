from . import main
from flask import render_template, redirect, url_for


@main.route('/')
def index():
    return redirect(url_for('main.events'))


@main.route('/events')
def events():
    return render_template('events.html', title='Events')


@main.route('/checks')
def checks():
    return render_template('checks.html', title='Checks')


@main.route('/about')
def about():
    return render_template('about.html', title='About')
