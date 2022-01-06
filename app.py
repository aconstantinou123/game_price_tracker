import os
import pandas as pd
import aiohttp
import asyncio
from urllib import parse
from sys import argv
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter


if len(argv) < 3:
    raise AttributeError('Missing args')

INPUT_FILE_PATH = argv[1]
OUTPUT_FILE_PATH = argv[2]

try:
    PLATFORMS = [x.strip() for x in argv[4].split(',')] 
except:
    PLATFORMS = None

try:
    CURRENCY = argv[3]
except IndexError:
    CURRENCY = 'USD'

c = CurrencyConverter()


async def get_price(session, url, row):
    async with session.get(url) as r:
        data = await r.text()
        soup = BeautifulSoup(data, features='html.parser')

        condition_lookup = {
            'C': 'complete_price',
            'L': 'used_price',
            'N': 'new_price',
            'G': 'graded_price',
            'B': 'box_only_price',
            'M': 'manual_only_price',
        }
        price_html_id = condition_lookup[row['Condition']] 
    
        try:
            price_html = soup.find(id=price_html_id)
            price_text = price_html.find(class_='price js-price').text
            price = float(("".join(line.strip() 
                        for line in price_text.split("\n")).replace('$', '')))

            if CURRENCY != 'USD':
                price = round(c.convert(price, 'USD', CURRENCY), 2)
            # print(f'{row["Platform"]}, {row["Title"]}: {price} {CURRENCY}')
            return price
        except AttributeError:
            price = 0.00
            print('Missing price', row['Title'])
            return price


async def main():
    async with aiohttp.ClientSession() as session:
        workbook = pd.ExcelFile(f'{INPUT_FILE_PATH}')
        sheets = workbook.sheet_names

        df = pd.concat([pd.read_excel(workbook, sheet_name=s)
                        .assign(Platform=s) for s in sheets
                        if not PLATFORMS or s in PLATFORMS])

        tasks = []
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

            tasks.append(asyncio.ensure_future(get_price(session, url, row)))

        prices = await asyncio.gather(*tasks)

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

asyncio.run(main())