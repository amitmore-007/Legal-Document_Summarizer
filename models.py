from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db=SQLAlchemy()

class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    rouge_1 = db.Column(db.Float, nullable=True)
    rouge_2 = db.Column(db.Float, nullable=True)
    rouge_l = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)  # ✅ Store accuracy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
 

    def __repr__(self):
        return f"<Summary {self.id}-{self.filename}>"