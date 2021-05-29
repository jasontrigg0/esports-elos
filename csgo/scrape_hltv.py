import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import re
import os
import time
from jtutils import url_to_soup

def split_list(l, key):
    chunks = []
    current_chunk = []
    for x in l:
        if key(x):
            chunks.append(current_chunk)
            current_chunk = []
        else:
            current_chunk.append(x)
    chunks.append(current_chunk)
    return chunks

def get_team_info(soup):
    info = {}
    for team in soup.select("div.match-page div.team a"):
        team_name = team.text
        team_url = team.attrs["href"]
        info[team_name.strip().lower()] = team_url
    return info

def get_match_info(match_url, soup):
    #pull basic match stats
    teams = [x.attrs["href"] for x in soup.select("div.match-page div.team a")] #x.text.strip()
    map_scores = [(x.text.strip()) for x in soup.select("div.match-page div.team div div") if "teamName" not in x.attrs["class"]]

    event = [x.attrs["href"] for x in soup.select("div.event a")][0] #x.text.strip()
    dt = soup.select("div.match-page div.date")[0].attrs["data-unix"]
    yyyymmdd = datetime.utcfromtimestamp(int(dt)/1000).strftime('%Y%m%d')
    hhmm = datetime.utcfromtimestamp(int(dt)/1000).strftime('%H%M')

    output = {
        "match": match_url,
        "team0": teams[0],
        "team1": teams[1],
        "event": event,
        "yyyymmdd": yyyymmdd,
        "hhmm": hhmm
    }

    #placeholders for map info
    for i in range(5):
        output[f"map{i}"] = ""
        output[f"map{i}_score0"] = ""
        output[f"map{i}_score1"] = ""

    return output

def get_stats_info(soup):
    #pull map stats
    map_info = {}
    for map_ in soup.select("div.matchstats div.box-headline div.dynamic-map-name-full"):
        if map_["id"] == "all": continue
        map_info[map_["id"]] = map_.text

    stats_info = {}
    for map_id in map_info:
        map_name = map_info[map_id]
        for side in ["tstats","ctstats"]:
            for row in soup.select("div.matchstats")[0].find_all("div",id=f"{map_id}-content")[0].select(f"table.{side} tr"):
                if "header-row" in row.attrs["class"]:
                    team = row.select("td.players a")[0].text
                    continue
                player = row.select("td.players a")[0]["href"]
                kills = row.select("td.kd")[0].text.split("-")[0]
                deaths = row.select("td.kd")[0].text.split("-")[1]
                adr = row.select("td.adr")[0].text if row.select("td.adr") else ""
                kast = row.select("td.kast")[0].text if row.select("td.kast") else ""
                rating = row.select("td.rating")[0].text
                stats_info.setdefault((map_name, team, side.replace("stats","")),[]).append({
                    "player": player,
                    "kills": kills,
                    "deaths": deaths,
                    "adr": adr,
                    "kast": kast,
                    "rating": rating
                })
    return stats_info

def get_match_list():
    match_file = "/tmp/match_info.csv"
    first_run = not os.path.exists(match_file)
    existing_matches = [] if first_run else [r["match"] for r in csv.DictReader(open(match_file))]

    #create csv writers
    match_fields = ["match", "team0", "team1", "event", "yyyymmdd", "hhmm"]
    for i in range(5):
        match_fields += [f"map{i}", f"map{i}_score0", f"map{i}_score1"]
    match_writer = csv.DictWriter(open(match_file,"a"),fieldnames=match_fields)

    sides_fields = ["match", "map", "overtime", "team0", "side0", "score0", "team1", "side1", "score1"]
    sides_writer = csv.DictWriter(open("/tmp/sides_info.csv","a"),fieldnames=sides_fields)

    stats_fields = ["match", "map", "overtime", "team", "side", "player", "kills", "deaths", "adr", "kast", "rating"]
    stats_writer = csv.DictWriter(open("/tmp/stats_info.csv","a"),fieldnames=stats_fields)

    if first_run:
        match_writer.writeheader()
        sides_writer.writeheader()
        stats_writer.writeheader()


    files = {
        "match_writer": match_writer,
        "sides_writer": sides_writer,
        "stats_writer": stats_writer
    }

    for i in range(0,20):
        results_url = f"https://www.hltv.org/results?offset={i*100}"
        #r = requests.get(results_url)
        soup = url_to_soup(results_url, js=True)
        #soup = BeautifulSoup(r.text,"lxml")

        for match in soup.select("div.result-con a.a-reset"):
            match_url = match.attrs["href"]
            if match_url in existing_matches:
                # print("found existing match, skipping...")
                continue
            print(match_url)
            process_match(match_url, files)
            existing_matches.append(match_url)
            time.sleep(1)

def process_match(match_url, files):
    if match_url in [
        "/matches/2342965/navi-2010-vs-natus-vincere-showmatch-csgo", #skip showmatch with cs 1.6 and csgo maps
        "/matches/2342171/truckers-with-attitude-vs-avant-esea-mdl-season-34-australia", #missing second half data?
        "/matches/2319507/dignitas-vs-luminosity-esl-pro-league-season-7-north-america", #weird half situation?
        "/matches/2299747/ttc-vs-torpedo-rgn-european-open", #6 maps, not supported
        "/matches/2297249/mousesports-vs-hellraisers-acer-predator-masters-powered-by-intel-season-1-finals", #6 maps, skipping
        "/matches/2294587/xfunction-vs-mindplay-xfunction-iberian-cup-by-hitbox", #weird half situation? don't understand
        "/matches/2293464/mythic-vs-xile-rgn-summers-end-tournament", #two bo3s packed into one, skipping
        "/matches/2293119/cloud9-vs-ibuypower-cevo-professional-season-5-lan-finals", #two bo3s packed into one, skipping
    ]:
        return

    MAX_RETRIES = 3
    retry_cnt = 0
    while retry_cnt < MAX_RETRIES:
        try:
            # r = requests.get("https://hltv.org" + match_url)
            # soup = BeautifulSoup(r.text,"lxml")
            soup = url_to_soup("https://hltv.org" + match_url, js=True)
            print("here")
            break
        except:
            retry_cnt += 1
            time.sleep(10)
            if retry_cnt > MAX_RETRIES:
                print("Exceeded max retries")
                raise

    if soup.select('div.error-500'):
        print("Match page won't load, skipping")
        return

    #pull players
    # for team in soup.select("div.lineup"):
    #     team_name = team.select("div.box-headline a.text-ellipsis")[0]["href"]
    #     print(team_name)
    #     player_list = team.select("div.players")[0].select("tr")[1]
    #     players = [player["href"] for player in player_list.select("td.player a")]
    #     print(players)

    team_info = get_team_info(soup)

    match_info = get_match_info(match_url, soup)

    stats_info = get_stats_info(soup)

    #pull map results
    for i,info in enumerate(soup.select("div.mapholder")):
        if not info.select("div.results.played"): continue #map wasn't played
        teamnames = [x.text for x in info.select(f"div.results-teamname")]
        full_scores = [x.text for x in info.select("div.results-team-score")]
        map_name = [x.text for x in info.select("div.mapname")][0]
        if map_name in ["Default","TBA"]: continue #used for advantaged finals and forfeits, not handling for now

        match_info[f"map{i}"] = map_name
        match_info[f"map{i}_score0"] = full_scores[0]
        match_info[f"map{i}_score1"] = full_scores[1]

        halves = []
        half = None

        all_spans = [x for x in info.select(f"div.results-center-half-score span") if not re.findall("^[\(\)\-:; ]*$",x.text)]

        print(map_name)
        if len(all_spans) == 0:
            print("no map score")
            continue
        if len(all_spans) not in [4,6]:
            print("unexpected span length")
            print(all_spans)
            print(match_url)
            #raise Exception("Unexpected span length")
        overtime = 1 * (len(all_spans) == 6)

        halves = [all_spans[:2], all_spans[2:4]]
        for half in halves:
            if not half: continue
            sides = [x.attrs["class"][0] for x in half]
            scores = [x.text.strip() for x in half]
            files["sides_writer"].writerow({
                "match": match_url,
                "map": map_name,
                "overtime": overtime,
                "team0": team_info[teamnames[0].strip().lower()],
                "side0": sides[0],
                "score0": scores[0],
                "team1": team_info[teamnames[1].strip().lower()],
                "side1": sides[1],
                "score1": scores[1]
            })
            if not stats_info:
                print("skipping stats")
                continue
            for i,key in enumerate([(map_name, teamnames[0], sides[0]), (map_name, teamnames[1], sides[1])]):
                if key not in stats_info:
                    print("skipping map stats")
                    continue
                stats_list = stats_info[key];
                for stats in stats_list:
                    files["stats_writer"].writerow({
                        "match": match_url,
                        "map": map_name,
                        "overtime": overtime,
                        "team": team_info[teamnames[i].strip().lower()],
                        "side": sides[i],
                        "player": stats["player"],
                        "kills": stats["kills"],
                        "deaths": stats["deaths"],
                        "adr": stats["adr"],
                        "kast": stats["kast"],
                        "rating": stats["rating"]
                    })
    files["match_writer"].writerow(match_info)



if __name__ == "__main__":
    get_match_list()
