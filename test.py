from helpers.search_tools import DuckDuckGoSearcher
from helpers.ghseet import GoogleSheetsService
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
# searcher = DuckDuckGoSearcher()
# query = '"F1 2025 current point standings"'
# query = str(query.replace('"', ''))
# results = asyncio.run(searcher.search(str(query.strip(""))))
# parsed_results = searcher.format_results_for_llm(results)
# print(parsed_results)

service = GoogleSheetsService(
    token_path=os.environ.get('TOKEN_PATH', 'token.json'),
    credentials_path=os.environ.get('CREDENTIALS_PATH', 'credentials.json'),
    drive_folder_id=os.environ.get('DRIVE_FOLDER_ID')
)
spreadsheet = service.create_spreadsheet("Test Spreadsheet")
print(spreadsheet)

ranges =  {
    'A1:E25': [['Pos', 'Driver', 'Nationality', 'Car', 'Pts'], ['1', 'Max Verstappen', 'NED', 'Red Bull Racing Honda RBPT', '437'], ['2', 'Lando Norris', 'GBR', 'McLaren Mercedes', '374'], ['3', 'Charles Leclerc', 'MON', 'Ferrari', '356'], ['4', 'Oscar Piastri', 'AUS', 'McLaren Mercedes', '292'], ['5', 'Carlos Sainz', 'ESP', 'Ferrari', '290'], ['6', 'George Russell', 'GBR', 'Mercedes', '245'], ['7', 'Lewis Hamilton', 'GBR', 'Mercedes', '223'], ['8', 'Sergio Perez', 'MEX', 'Red Bull Racing Honda RBPT', '152'], ['9', 'Fernando Alonso', 'ESP', 'Aston Martin Aramco Mercedes', '70'], ['10', 'Pierre Gasly', 'FRA', 'Alpine Renault', '42'], ['11', 'Nico Hulkenberg', 'GER', 'Haas Ferrari', '41'], ['12', 'Yuki Tsunoda', 'JPN', 'RB Honda RBPT', '30'], ['13', 'Lance Stroll', 'CAN', 'Aston Martin Aramco Mercedes', '24'], ['14', 'Esteban Ocon', 'FRA', 'Alpine Renault', '23'], ['15', 'Kevin Magnussen', 'DEN', 'Haas Ferrari', '16'], ['16', 'Alexander Albon', 'THA', 'Williams Mercedes', '12'], ['17', 'Daniel Ricciardo', 'AUS', 'RB Honda RBPT', '12'], ['18', 'Oliver Bearman', 'GBR', 'Haas Ferrari', '7'], ['19', 'Franco Colapinto', 'ARG', 'Williams Mercedes', '5'], ['20', 'Zhou Guanyu', 'CHN', 'Kick Sauber Ferrari', '4'], ['21', 'Liam Lawson', 'NZL', 'RB Honda RBPT', '4'], ['22', 'Valtteri Bottas', 'FIN', 'Kick Sauber Ferrari', '0'], ['23', 'Logan Sargeant', 'USA', 'Williams Mercedes', '0'],['24', 'Jack Doohan', 'AUS', 'Alpine Renault', '0']]}

output = service.batch_update_cells(spreadsheet['spreadsheetId'], 'Sheet1', ranges)
print(output)