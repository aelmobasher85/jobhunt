from abilities import llm_prompt
import logging
from gunicorn.app.base import BaseApplication
from app_init import create_initialized_flask_app
import feedparser
from flask_apscheduler import APScheduler
from models import db, User, JobAlert
from flask_mail import Mail, Message
import os
from datetime import datetime, timedelta

# Flask app creation should be done by create_initialized_flask_app to avoid circular dependency problems.
app = create_initialized_flask_app()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)

# Initialize APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def fetch_and_process_rss_feeds():
    with app.app_context():
        users = User.query.all()
        for user in users:
            if user.rss_feed_url:
                feed = feedparser.parse(user.rss_feed_url)
                for entry in feed.entries:
                    # Check if this job alert already exists
                    existing_alert = JobAlert.query.filter_by(job_id=entry.id, user_id=user.id).first()
                    if not existing_alert:
                        # Create new job alert
                        new_alert = JobAlert(
                            job_id=entry.id,
                            title=entry.title,
                            description=entry.description,
                            link=entry.link,
                            user_id=user.id
                        )
                        db.session.add(new_alert)
                        
                        # Generate custom cover letter
                        cover_letter = generate_cover_letter(entry.title, entry.description)
                        
                        # Send email alert
                        send_email_alert(user.email, new_alert, cover_letter)
                
                db.session.commit()

def generate_cover_letter(job_title, job_description):
    prompt = f"Generate a professional cover letter for the position of {job_title}. Job description: {job_description}"
    cover_letter = llm_prompt(prompt, model="gpt-3.5-turbo-1106", temperature=0.7)
    return cover_letter

def send_email_alert(email, job_alert, cover_letter):
    # Check if the user has reached their daily email limit
    today = datetime.utcnow().date()
    user = User.query.filter_by(email=email).first()
    alerts_sent_today = JobAlert.query.filter(
        JobAlert.user_id == user.id,
        JobAlert.created_at >= today
    ).count()
    
    if alerts_sent_today < user.daily_email_limit:
        msg = Message(f"New Job Alert: {job_alert.title}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Job Title: {job_alert.title}\n\n" \
                   f"Description: {job_alert.description}\n\n" \
                   f"Apply here: {job_alert.link}\n\n" \
                   f"Suggested Cover Letter:\n\n{cover_letter}"
        mail.send(msg)
        logger.info(f"Email alert sent to {email} for job: {job_alert.title}")
    else:
        logger.info(f"Daily email limit reached for user: {email}")

# Schedule the RSS feed check
scheduler.add_job(id='fetch_rss_feeds', func=fetch_and_process_rss_feeds, trigger='interval', minutes=30)

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        # Apply configuration to Gunicorn
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == "__main__":
    options = {
        "bind": "0.0.0.0:8080",
        "workers": 4,
        "loglevel": "info",
        "accesslog": "-"
    }
    StandaloneApplication(app, options).run()