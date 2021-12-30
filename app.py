import os
import pandas as pd
import requests
from urllib import parse
from sys import argv
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter


if len(argv) < 3:
    raise AttributeError('Missing args')

INPUT_FILE_PATH = argv[1]
OUTPUT_FILE_PATH = argv[2]

try:
    PLATFORMS = argv[4].split(',')
    print(PLATFORMS)
except:
    PLATFORMS = None

try:
    CURRENCY = argv[3]
except IndexError:
    CURRENCY = 'USD'

c = CurrencyConverter()

workbook = pd.ExcelFile(f'{INPUT_FILE_PATH}')
sheets = workbook.sheet_names

if not PLATFORMS:
    PLATFORMS = sheets

df = pd.concat([pd.read_excel(workbook, sheet_name=s)
                .assign(Platform=s) for s in sheets
                if s in PLATFORMS])

prices = []
print('Collecting prices from www.pricecharting.com')
for index, row in df.iterrows():
    title = parse.quote(row['Title'].lower().replace(' ', '-'))
    console = row['Platform'].lower().replace(' ', '-')
    region = row['Region'].lower()

    platform = console
    if region == 'pal':
        platform = f'{region}-{console}'
    elif region == 'ntsc-j':
        platform = f'jp-{console}'

    url = f'https://www.pricecharting.com/game/{platform}/{title}'
    r = requests.get(url)

    data = r.text
    soup = BeautifulSoup(data, features='html.parser')

    price_html_id = '' 
    if row['Condition'] == 'C':
        price_html_id = 'complete_price'
    elif row['Condition'] == 'L':
        price_html_id == 'used_price'
    elif row['Condition'] == 'N':
         price_html_id == 'new_price'
    elif row['Condition'] == 'G':
         price_html_id == 'graded_price'
    elif row['Condition'] == 'B':
         price_html_id == 'box_only_price'
    elif row['Condition'] == 'M':
         price_html_id == 'manual_only_price'

    try:
        price_html = soup.find(id=price_html_id)
        price_text = price_html.find(class_='price js-price').text
        price = float(("".join(line.strip() 
                    for line in price_text.split("\n")).replace('$', '')))

        if CURRENCY != 'USD':
            price = round(c.convert(price, 'USD', CURRENCY), 2)
        # print(f'{row["Platform"]}, {row["Title"]}: {price} {CURRENCY}')
        prices.append(price)
    except AttributeError:
        price = 0.00
        print('Missing price', row['Title'])
        prices.append(price)

print('Prices collected')
df[f'Price ({CURRENCY})'] = prices

print(f'Writing results to {OUTPUT_FILE_PATH}')
writer = pd.ExcelWriter(f'{OUTPUT_FILE_PATH}', engine='xlsxwriter')
for group, data in df.groupby('Platform'):
    data.drop(columns=['Platform'], inplace=True)
    data.to_excel(writer, group, index=False)

workbook  = writer.book
price_format = workbook.add_format({'num_format': '0.00'})
sheets = writer.sheets
for sheet in sheets:
    worksheet = writer.sheets[sheet]
    worksheet.set_column('D:D', None, price_format)

totals_df = pd.DataFrame(df.groupby('Platform').sum())
totals_df.loc['Total']= df[f'Price ({CURRENCY})'].sum()
totals_df.to_excel(writer, sheet_name='Totals')
totals_worksheet = writer.sheets['Totals']
totals_worksheet.set_column('B:B', None, price_format)

writer.save()
print('Done!')
