from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class PriceData(db.Model):
    __tablename__ = 'price_data'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), index=True, nullable=False)
    date = db.Column(db.Date, index=True, nullable=False)
    open_price = db.Column('open', db.Float)
    high_price = db.Column('high', db.Float)
    low_price = db.Column('low', db.Float)
    close_price = db.Column('close', db.Float)
    volume = db.Column(db.BigInteger)

    def as_dict(self):
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat() if isinstance(self.date, date) else str(self.date),
            'open': self.open_price,
            'high': self.high_price,
            'low': self.low_price,
            'close': self.close_price,
            'volume': self.volume
        }
