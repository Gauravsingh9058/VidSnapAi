from app import create_app
from app.services.scheduler_service import process_due_jobs


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        processed = process_due_jobs()
        print(f"Processed {processed} scheduled job(s).")
