import csv
from gen_elo import EloCalculator

TEAM_MAPPING = {
    "DAMWON Gaming": "Dplus KIA",
    "DWG KIA": "Dplus KIA",
    "SK Telecom T1": "T1",
    "Vici Gaming": "Rare Atom",
    "Incredible Miracle": "DRX",
    "Longzhu Gaming": "DRX",
    "Kingzone DragonX": "DRX",
    "DragonX": "DRX",
    "Samsung Ozone": "Samsung White",
    "HUYA Tigers": "ROX Tigers",
    "GE Tigers": "ROX Tigers",
    "Rogue (European Team)": "Rogue"
}

def load_match_info():
    match_reader = csv.DictReader(open("lol.csv"))

    for row in match_reader:
        #if row["DateTime UTC"].split()[0].replace("-","") > "20231001": continue

        #map old team names to the newest version for continuity
        row["Team1"] = TEAM_MAPPING.get(row["Team1"],row["Team1"])
        row["Team2"] = TEAM_MAPPING.get(row["Team2"],row["Team2"])
        row["WinTeam"] = TEAM_MAPPING.get(row["WinTeam"],row["WinTeam"])

        yield {
            "basic_info": {
                "yyyymmdd": row["DateTime UTC"].split()[0].replace("-",""),
                "total_score": 1
            },
            "team_to_info": {
                row["Team1"]: {"score": 1*(row["Team1"] == row["WinTeam"])},
                row["Team2"]: {"score": 1*(row["Team2"] == row["WinTeam"])}
            }
        }

if __name__ == "__main__":
    match_data = list(load_match_info())
    elo_calc = EloCalculator(match_data, "lol", 50)
    elo_calc.generate_elos()
    elo_calc.print_elos()
    elo_calc.write_elos()
