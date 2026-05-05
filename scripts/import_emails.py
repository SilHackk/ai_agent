from app.services.project_db import init_db
from app.services.email_importer import import_recent_emails

if __name__ == '__main__':
    init_db()
    print(import_recent_emails(limit=100))
