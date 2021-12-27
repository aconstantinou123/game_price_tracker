import os
import pandas as pd
import requests
from urllib import parse
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE_NAME = os.getenv('INPUT_FILE_NAME')
OUTPUT_FILE_NAME = os.getenv('OUTPUT_FILE_NAME')

c = CurrencyConverter()

workbook = pd.ExcelFile(f'spreadsheets/{INPUT_FILE_NAME}')
sheets = workbook.sheet_names
df = pd.concat([pd.read_excel(workbook, sheet_name=s)
                .assign(sheet_name=s) for s in sheets])

prices = []
for index, row in df.iterrows():
    title = parse.quote(row['Title'].lower().replace(' ', '-'))
    console = row['sheet_name'].lower().replace(' ', '-')
    region = row['Region'].lower()
    platform = f'{region}-{console}' if region == 'pal' else console
    url = f'https://www.pricecharting.com/game/{platform}/{title}'
    r = requests.get(url)

    data = r.text
    soup = BeautifulSoup(data, features='html.parser')
    price_html_id = 'complete_price' if row['CIB'] == 'X' else 'used_price'
    try:
        price_html = soup.find(id=price_html_id)
        price_text = price_html.find(class_='price js-price').text
        us_price = float(("".join(line.strip() 
                    for line in price_text.split("\n")).replace('$', '')))
        gbp_price = round(c.convert(us_price, 'USD', 'GBP'), 2)
        prices.append(float(gbp_price))
    except AttributeError:
        price = 0.00
        print('Missing price', row['Title'])
        prices.append(price)
df['Price (GBP)'] = prices

writer = pd.ExcelWriter(f'spreadsheets/{OUTPUT_FILE_NAME}', engine='xlsxwriter')
for group, data in df.groupby('sheet_name'):
    data.to_excel(writer, group, float_format="%.2f", index=False)
writer.save()
