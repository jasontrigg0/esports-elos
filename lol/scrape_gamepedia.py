#options for scraping league of legends
#gamepedia
#liquipedia
#can you use the regular league of legends api to get competitive games? not sure
#there used to be an lolesports api, does that still work? what games are available there?
#gamepedia looks the easiest, going with that: https://lol.gamepedia.com/Help:Leaguepedia_API#Cargo_Table_Overviews
#after downloading the gamepedia data, it seems liquipedia has better old match records, may want to scrape that instead
#starting with https://lol.gamepedia.com/Special:CargoTables/ScoreboardGames
#later can add https://lol.gamepedia.com/Special:CargoTables/ScoreboardPlayers

import mwclient
import time
import csv

if __name__ == "__main__":
    site = mwclient.Site('lol.fandom.com', path='/')
    limit = 500 #max 500
    page = 0
    writer = csv.DictWriter(open("/tmp/lol.csv",'w'),fieldnames=["Tournament", "DateTime UTC", "DateTime UTC__precision", "Team1", "Team2", "WinTeam", "LossTeam"])
    writer.writeheader()
    while True:
        response = site.api('cargoquery',
            limit = str(limit),
            tables = "ScoreboardGames=SG",
            offset = page * limit,
            fields = "SG.Tournament, SG.DateTime_UTC, SG.Team1, SG.Team2, SG.WinTeam, SG.LossTeam"
        )
        page += 1
        for x in response["cargoquery"]:
            row = x["title"]
            writer.writerow(row)
        if len(response["cargoquery"]) == 0:
            break
        time.sleep(2)
