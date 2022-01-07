import os
import pandas as pd
import aiohttp
import asyncio
import argparse
from urllib import parse
from sys import argv
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter

c = CurrencyConverter()


def check_file_extension(path):
    _, file_extension = os.path.splitext(path)
    if file_extension != '.xlsx':
        raise TypeError(f'Incorrect file type: {file_extension} - ' +
                        'Input/out files must have extension .xlsx')


async def get_price(session, url, row, currency, verbosity):
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
        price_html_id = condition_lookup.get(row['Condition'].strip(), None)
        if price_html_id is None:
            print(f'ERROR: Unknown condition for {row["Title"]} - {row["Condition"]}. ' +
                  f'Price may be inaccurate. Must be one of {", ".join(list(condition_lookup.keys()))}')

        try:
            price_html = soup.find(id=price_html_id)
            price_text = price_html.find(class_='price js-price').text
            price = float(("".join(line.strip()
                                   for line in price_text.split("\n")).replace('$', '')))

            if currency != 'USD':
                price = round(c.convert(price, 'USD', currency), 2)
            if verbosity == 'DEBUG':
                print(f'{row["Platform"]}, {row["Title"]}: {price} {currency}')
            return price
        except AttributeError:
            price = 0.00
            print(f'ERROR: Missing price {row["Title"]} - {row["Platform"]}/{row["Region"]}. ' +
                  'Check title/platform/region is correct')
            return price


async def generate_prices_spreadsheet(inputfile, outputfile, currency, platforms, verbosity):
    if platforms:
        platforms = [x.strip() for x in platforms.split(',')]
    async with aiohttp.ClientSession() as session:
        workbook = pd.ExcelFile(f'{inputfile}')
        sheets = workbook.sheet_names

        df = pd.concat([pd.read_excel(workbook, sheet_name=s)
                        .assign(Platform=s) for s in sheets
                        if not platforms or s in platforms])

        allowed_columns = ['Title', 'Region', 'Condition', 'Platform']

        if not all([True if col in list(df.columns) else False for col in allowed_columns]):
            raise ValueError(f'Incorrect spreadsheet columns: ' +
                             f'{", ".join(list(df.columns))}. Must include {", ".join(allowed_columns)}')

        tasks = []
        print('Collecting prices from www.pricecharting.com')
        for index, row in df.iterrows():
            title = parse.quote(row['Title'].lower().replace(' ', '-').strip())
            console = row['Platform'].lower().replace(' ', '-').strip()
            region = row['Region'].lower().strip()

            platform = console
            if region == 'pal':
                platform = f'{region}-{console}'
            elif region == 'ntsc-j':
                platform = f'jp-{console}'

            url = f'https://www.pricecharting.com/game/{platform}/{title}'

            tasks.append(
                asyncio.ensure_future(
                    get_price(
                        session,
                        url,
                        row,
                        currency,
                        verbosity)))

        prices = await asyncio.gather(*tasks)

        print('Prices collected')
        df[f'Price ({currency})'] = prices

        print(f'Writing results to {outputfile}')
        writer = pd.ExcelWriter(f'{outputfile}', engine='xlsxwriter')
        for group, data in df.groupby('Platform'):
            data.drop(columns=['Platform'], inplace=True)
            data.to_excel(writer, group, index=False)

        workbook = writer.book
        price_format = workbook.add_format({'num_format': '0.00'})
        sheets = writer.sheets
        for sheet in sheets:
            worksheet = writer.sheets[sheet]
            worksheet.set_column('D:D', None, price_format)

        totals_df = pd.DataFrame(df.groupby('Platform').sum())
        totals_df.loc['Total'] = df[f'Price ({currency})'].sum()
        totals_df.to_excel(writer, sheet_name='Totals')
        totals_worksheet = writer.sheets['Totals']
        totals_worksheet.set_column('B:B', None, price_format)

        writer.save()
        print('Done!')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', type=str)
    parser.add_argument('-o', '--outputfile', type=str)
    parser.add_argument('-c', '--currency', type=str, default='USD')
    parser.add_argument('-p', '--platforms', type=str)
    parser.add_argument('-v', '--verbosity', type=str, default='INFO')
    args = parser.parse_args().__dict__
    if args['inputfile'] is None:
        raise ValueError('Input file path required')
    if args['outputfile'] is None:
        raise ValueError('Output file path required')
    check_file_extension(args['inputfile'])
    check_file_extension(args['outputfile'])
    asyncio.run(generate_prices_spreadsheet(**args))


if __name__ == '__main__':
    main()
