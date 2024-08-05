from flask import render_template, request, redirect, url_for, flash
from flask import current_app as app
from models import db, User, JobAlert

def register_routes(app):
    @app.route("/")
    def home_route():
        return render_template("home.html")

    @app.route("/settings", methods=['GET', 'POST'])
    def settings():
        if request.method == 'POST':
            email = request.form['email']
            rss_feed_url = request.form['rss_feed_url']
            daily_email_limit = int(request.form['daily_email_limit'])

            user = User.query.filter_by(email=email).first()
            if user:
                user.rss_feed_url = rss_feed_url
                user.daily_email_limit = daily_email_limit
            else:
                new_user = User(email=email, rss_feed_url=rss_feed_url, daily_email_limit=daily_email_limit)
                db.session.add(new_user)

            db.session.commit()
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings'))

        return render_template("settings.html")

    @app.route("/alerts")
    def alerts():
        # TODO: Implement user authentication and fetch alerts for the logged-in user
        alerts = JobAlert.query.order_by(JobAlert.created_at.desc()).limit(10).all()
        return render_template("alerts.html", alerts=alerts)