#other options for scraping league of legends
#gamepedia
#liquipedia

import mwclient
import time
import csv

def get_all_games(cutoff_year):
    site = mwclient.Site('lol.fandom.com', path='/')
    limit = 500 #max 500
    page = 0
    while True:
        #mediawiki args here: https://www.mediawiki.org/wiki/Extension:Cargo/Querying_data
        args = {
            "limit": str(limit),
            "tables": "ScoreboardGames=SG",
            "offset": page * limit,
            "fields": "SG.Tournament, SG.DateTime_UTC, SG.Team1, SG.Team2, SG.WinTeam, SG.LossTeam",
            "order by": "SG.DateTime_UTC DESC"
        }

        filter_fn = lambda x: x["DateTime UTC"][:4] >= str(cutoff_year)
        
        rows = [x["title"] for x in site.api('cargoquery', **args)["cargoquery"]]
        past_cutoff = any(not filter_fn(x) for x in rows)
        rows = [x for x in rows if filter_fn(x)]
        
        page += 1

        for r in rows:
            yield r
            writer.writerow(r)

        if past_cutoff or len(rows) == 0:
            break
        time.sleep(2)

if __name__ == "__main__":
    cutoff_year = 2025

    year_to_writer = {}
    for game in get_all_games(cutoff_year):
        year = game["DateTime UTC"][:4]
        if not year in year_to_writer:
            writer = csv.DictWriter(open(f"../data/lol/lol_{year}.csv",'w'),fieldnames=["Tournament", "DateTime UTC", "DateTime UTC__precision", "Team1", "Team2", "WinTeam", "LossTeam"])
            writer.write_header()
        writer = year_to_writer[year]
        writer.writerow(game)
