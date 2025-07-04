from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
from models.price_data import db, PriceData

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fintech.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def get_first_200_symbols(input_file: str) -> list:
    symbols = []
    seen = set()
    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            i = 0
            while i < len(line):
                if line[i].isupper():
                    start = i
                    while i < len(line) and line[i].isupper():
                        i += 1
                    if i - start >= 3:
                        symbol = line[start:i]
                        if symbol not in seen:
                            seen.add(symbol)
                            symbols.append(symbol)
                            if len(symbols) == 200:
                                return symbols
                else:
                    i += 1
    return symbols

def fetch_and_store_data(symbols: list):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)
    for symbol in symbols:
        print(f"Fetching data for {symbol}...")
        try:
            df = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, group_by='ticker')
            if df is not None:
                if isinstance(df.columns, pd.MultiIndex):
                    if symbol in df.columns.levels[0]:
                        df = df[symbol]
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    price = PriceData()
                    price.symbol = symbol
                    price.date = pd.Timestamp(str(idx)).date()
                    def get_scalar(val):
                        if val is None or pd.isna(val):
                            return None
                        if np.isscalar(val):
                            return val
                        try:
                            return float(val.item())
                        except Exception:
                            try:
                                return float(val.values[0])
                            except Exception:
                                return None
                    price.open_price = get_scalar(row.get('Open', None))
                    price.high_price = get_scalar(row.get('High', None))
                    price.low_price = get_scalar(row.get('Low', None))
                    price.close_price = get_scalar(row.get('Close', None))
                    v = get_scalar(row.get('Volume', None))
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        price.volume = int(v)
                    else:
                        price.volume = None
                    db.session.merge(price)
                db.session.commit()
                print(f"Stored data for {symbol}.")
            else:
                print(f"No data for {symbol}.")
        except Exception as e:
            db.session.rollback()
            print(f"Error fetching {symbol}: {e}")

@app.route('/initdb')
def initdb():
    with app.app_context():
        db.create_all()
    return 'Database initialized.'

@app.route('/fetch')
def fetch():
    input_file = 'test.html'
    symbols = get_first_200_symbols(input_file)
    fetch_and_store_data(symbols)
    return 'Data fetched and stored.'

@app.route('/data/<symbol>')
def get_data(symbol):
    records = PriceData.query.filter_by(symbol=symbol.upper()).all()
    return jsonify([r.as_dict() for r in records])

@app.route('/dashboard', methods=['GET'])
def dashboard():
    symbol = request.args.get('symbol', '').upper().strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    data = None
    status = None
    if symbol:
        records = PriceData.query.filter_by(symbol=symbol).order_by(PriceData.date).all()
        if records:
            data = [r.as_dict() for r in records]
            period = f"{data[0]['date']} to {data[-1]['date']}"
            status = f"Showing data for {symbol} from {period}."
        else:
            status = f"{symbol} not in database."
    return render_template('dashboard.html', data=data, status=status)

if __name__ == '__main__':
    app.run(debug=True)
