import csv
import sys
sys.path.append(".")
from gen_elo import EloCalculator, compute_expected_raw

class CsGoEloCalculator(EloCalculator):
    def __init__(self, all_match_info, k, ml_iter, adj_iter):
        self.team_map_k = 0
        self.map_ct_k = 10 / 15.
        self.player_k = 20 / 15.
        super().__init__(all_match_info, k, ml_iter, adj_iter)
    def new_elos(self):
        return {
            "team": {},
            "team_map": {},
            "map_ct": {},
            "player": {},
            "recent_matches": {},
            "team_last_match": {},
            "player_last_match": {}
        }
    def initialize_elos(self, team, basic_info):
        #initialize elos
        map_name = basic_info["map"]
        for elo in [self.ml_elos, self.adj_elos]:
            elo["team"].setdefault(team,self.starting_elo)
            elo["team_map"].setdefault((team,map_name),0)
            elo["map_ct"].setdefault(map_name,0)
    def compute_match_adj_elo(self, team0, team1, basic_info, team_to_info, team0_elos, team1_elos):
        match_adj_elo = team0_elos["team"][team0]
        difficulty = team1_elos["team"][team1]

        map_name = basic_info["map"]
        if map_name:
            match_adj_elo += team0_elos["team_map"].get((team0, map_name), 0)
            difficulty += team1_elos["team_map"].get((team1, map_name), 0)

        side0 = team_to_info[team0].get("side",None)
        if side0:
            map_ct_bias = team0_elos["map_ct"].get(map_name, 0) * (1 if side0 == "ct" else -1)
            difficulty -= map_ct_bias

        return match_adj_elo, difficulty
    def update_elos_from_perf(self, elos, basic_info, team_to_info, team_to_perf):
        for team in team_to_perf:
            info = team_to_info[team]
            perf = team_to_perf[team]

            round_cnt = basic_info["total_score"]
            map_name = basic_info["map"]

            elos["team"][team] += self.k * round_cnt * perf
            elos["team_map"][(team, basic_info["map"])] += self.team_map_k * round_cnt * perf
            if "side" in team_to_info[team] and team_to_info[team]["side"] == "ct": #run only on the ct side
                elos["map_ct"][map_name] += self.map_ct_k * round_cnt * perf
    def get_players(self, team_to_info):
        for team in team_to_info:
            stats = team_to_info[team]["stats"]
            for row in stats:
                yield row["player"]
    def update_player_elos(self, elos, basic_info, team_to_info):
        #QUESTIONS:
        #(1) What is the relationship between team kill share and team round share?
        #Answer: roughly round_share = 2*kill_share - 0.5 (cap at 0 and 1?)
        #so 3-1 kill/death ratio = 0.75 kill share should win almost every round
        #so we can convert from team elo -> team round share -> team kill share
        #
        #(2) How much are individuals held back by the performance of their teammates in csgo?
        #in the 100% individual version the individual plays the same regardless of teammate strength
        #in the 100% team version everyone's stats are the same as those of the whole team
        #observed_kda_performance = alpha * team_average_kda + (1 - alpha) * true_kda_performance
        #where alpha is the teamwork factor: 1 = can't overperform the team, 0 = performance doesn't depend on the team
        #then we can convert from individual observed kdas to true kdas via
        #true_kda_performance = (observed_kda_performance - alpha * team_average_kda) / (1 - alpha)
        #maybe try alpha = 0.2?
        #so if you observe a two player team with kdas of 1.2 and 0.8 then the true performances
        #would be 1.25 and 0.75
        #maybe you could test this when new teams form? still difficult.
        #maybe better to see how it qualitatively scores good players on bad teams compared to good players on good teams
        #
        #(3) If a team's round share is greater than you'd predict from their kda, did they get lucky?
        #or did they just execute better on the non-kda portion of the game?
        #for now take the round share as ground truth. Could test this by seeing if you improve predictive
        #power by including the kda info
        TEAM_FACTOR_CONSTANT = 0.2
        for team in team_to_info:
            stats = team_to_info[team]["stats"]
            round_cnt = basic_info["total_score"]
            team_d = sum(int(x["deaths"]) for x in stats)
            team_k = sum(int(x["kills"]) for x in stats)
            if (team_k + team_d) == 0:
                return #empty stats
            team_kill_share = team_k / (team_k + team_d)
            for row in stats:
                player = row["player"]
                if not player in elos["player"]:
                    elos["player"][player] = self.starting_elo
                if (int(row["kills"]) + int(row["deaths"])) == 0:
                    raw_kill_share = 0.5
                else:
                    raw_kill_share = int(row["kills"]) / (int(row["kills"]) + int(row["deaths"]))
                relative_kill_share = raw_kill_share - team_kill_share
                adjusted_relative_kill_share = relative_kill_share / (1 - TEAM_FACTOR_CONSTANT)
                adjusted_pseudo_round_share = 2*(0.5 + adjusted_relative_kill_share) - 0.5
                adjusted_pseudo_round_share = min(max(adjusted_pseudo_round_share,0),1)
                expected_pseudo_round_share = compute_expected_raw(elos["player"][player]-elos["team"][team])
                delta = (adjusted_pseudo_round_share - expected_pseudo_round_share)
                elos["player"][player] += self.player_k * round_cnt * delta
                #error["player"] += round_cnt * abs(adjusted_pseudo_round_share - expected_pseudo_round_share)
    def shrink_adj_elos(self):
        elos = self.adj_elos
        for team in elos["team"]:
            elos["team"][team] = 0.5 * (elos["team"][team] + self.starting_elo)
        for team_map in elos["team_map"]:
            elos["team_map"][team_map] = 0.5 * elos["team_map"][team_map]

        for player in elos["player"]:
            elos["player"][player] = 0.5 * (elos["player"][player] + self.starting_elo)

def load_raw_match_info():
    match_reader = csv.DictReader(open("csgo/match_info.csv"))
    half_reader = csv.DictReader(open("csgo/sides_info.csv"))
    stats_reader = csv.DictReader(open("csgo/stats_info.csv"))

    match_info = {}

    for row in match_reader:
        if row["match"] in [
                "/matches/2314674/tempo-storm-vs-tempo-storm-epicenter-2017-americas-qualifier-2",
                "/matches/2302840/alientech-vs-alientech-alientech-csgo-invitational-ii",
                "/matches/2301918/k1ck-vs-k1ck-alientech-csgo-league-season-i-finals",
                "/matches/2297191/k1ck-vs-k1ck-xfunction-masters-season-iii"
                ]:
            print("improperly parsed match, skipping") #TODO fix, looks like the match itself worked but the halves / stats didn't when the team name is the same
            continue
        match_info[row["match"]] = row
    for row in half_reader:
        if not row["match"] in match_info:
            #print("missing match info for half", row["match"])
            continue
        match_info[row["match"]].setdefault("halves",[])
        half_info = {x:row[x] for x in ["map","team0","side0","score0","team1","side1","score1"]}
        if any(half_info == x for x in match_info[row["match"]]["halves"]):
            #print("duplicate half, skipping")
            continue
        match_info[row["match"]]["halves"].append(half_info)
    for row in stats_reader:
        if row["match"] not in match_info:
            #print("missing match info for stats", row["match"])
            continue
        half = [x for x in match_info[row["match"]]["halves"] if (row["map"], row["team"], row["side"]) == (x["map"], x["team0"], x["side0"]) or (row["map"], row["team"], row["side"]) == (x["map"], x["team1"], x["side1"])]
        if len(half) != 1:
            print(row)
            print(row["match"])
            print(match_info[row["match"]]["halves"])
            print(half)
            raise
        half = half[0]

        stats_info = {x:row[x] for x in ["team", "player", "kills", "deaths", "adr", "kast", "rating"]}
        half.setdefault("stats",[])
        half["stats"].append(stats_info)
    all_match_info = sorted([match_info[x] for x in match_info], key = lambda x: x["yyyymmdd"] + x["hhmm"])
    return all_match_info

def preprocess_raw_matches(all_raw_matches):
    #teams that changed orgs -- store all matches as the latest iteration
    team_mappings = {
        "/team/10831/entropiq": {
            (None, "20210509"): "/team/11147/entropiq-prague",
            ("20210510", None): "/team/10831/entropiq"
        },
        "/team/11085/ex-winstrike": {
            (None, None): "/team/10831/entropiq"
        },
        "/team/11119/epg-family": {
            (None, None): "/team/10831/entropiq"
        },
        "/team/7733/boom": {
            (None, None): "/team/9215/mibr"
        },
        "/team/9215/mibr": {
            (None, "20201231"): "/team/7733/mibr-1", #placeholder for former lineup
            ("20210101", None): "/team/9215/mibr"
        }
    }

    def map_team(team, yyyymmdd):
        if team in team_mappings:
            mappings = team_mappings[team]
            for start,end in mappings:
                if (start is None or start <= yyyymmdd) and (end is None or end >= yyyymmdd):
                    return mappings[(start,end)]
        return team


    for raw_match in all_raw_matches:
        match = {}
        yyyymmdd = raw_match["yyyymmdd"]
        team0 = map_team(raw_match["team0"], yyyymmdd)
        team1 = map_team(raw_match["team1"], yyyymmdd)

        if "halves" in raw_match:
            for half in raw_match["halves"]:
                score0 = int(half["score0"])
                score1 = int(half["score1"])
                yield {
                    "basic_info": {
                        "url": "https://hltv.org" + raw_match["match"],
                        "map": half["map"],
                        "yyyymmdd": raw_match["yyyymmdd"],
                        "total_score": score0 + score1 #round count
                    },
                    "team_to_info": {
                        team0: {"score": score0, "side": half["side0"], "stats": [x for x in half.get("stats",[]) if x["team"] == team0]},
                        team1: {"score": score1, "side": half["side1"], "stats": [x for x in half.get("stats",[]) if x["team"] == team1]}
                    }
                }
        else:
            for map_id in range(5):
                map_name = raw_match[f"map{map_id}"]
                if not map_name:
                    continue
                if raw_match[f"map{map_id}_score0"] == "-":
                    continue
                score0 = int(raw_match[f"map{map_id}_score0"])
                score1 = int(raw_match[f"map{map_id}_score1"])
                yield {
                    "basic_info": {
                        "url": "https://hltv.org" + raw_match["match"],
                        "map": map_name,
                        "yyyymmdd": raw_match["yyyymmdd"],
                        "total_score": score0 + score1
                    },
                    "team_to_info": {
                        team0: {"score": score0},
                        team1: {"score": score1}
                    }
                }

if __name__ == "__main__":
    all_raw_matches = load_raw_match_info()

    elo_match_info = list(preprocess_raw_matches(all_raw_matches))

    elo_calc = CsGoEloCalculator(elo_match_info, 40/15., 10, 3)
    elo_calc.generate_elos()
    elo_calc.print_elos()
    elo_calc.write_elos()
