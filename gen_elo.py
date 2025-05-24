#TODO: remove /15 from generic)
import csv
import datetime
import copy
import scipy.optimize
import numpy as np
import math

class EloCalculator:
    def __init__(self, all_match_info, prefix="elo", k=20, ml_iter=100, adj_iter=15, has_wlt=True):
        self.prefix = prefix
        self.k = k
        self.ml_iter = ml_iter
        self.adj_iter = adj_iter
        self.starting_elo = 1500

        #maximum likelihood elos
        self.ml_elos = self.new_elos()

        #pseudo prior-adjusted elos (janky)
        self.adj_elos = self.new_elos()

        self.performances = {}

        self.alltime_team_top_25 = [] #top team performances
        self.alltime_player_top_25 = [] #top team performances

        self.all_match_info = all_match_info

        #f"<a href=\"{last['url']}\">Last match</a>"
        #f"<a href=\"{last['url']}\">Last match</a>"

        #f"Last: {wlt} vs <a href=\"{last['url']}\">{last['opp']}</a>"

        #f"<a href=\"{x['last']['url']}\">{datetime.datetime.strptime(x['yyyymmdd'], '%Y%m%d').strftime('%B %d, %Y')}</a>"

        #{datetime.datetime.strptime(last['yyyymmdd'], '%Y%m%d').strftime('%B %d, %Y')}</a>"

        def detail_wlt(last):
            wlt = "Win" if last["score"] > last["opp_score"] else ("Loss" if last["score"] < last["opp_score"] else "Tie")
            if last.get("url",None):
                return f"Last: {wlt} vs <a href=\"{last['url']}\">{last['opp']}</a>"
            else:
                return f"Last: {wlt} vs {last['opp']}"

            return f"Last: {wlt} vs {last['opp']}"

        def detail_last(last):
            if last.get("url",None):
                return f"<a href=\"{last['url']}\">Last match</a>"
            else:
                return f""

        def detail_date(last):
            if last.get("url",None):
                return f"<a href=\"{last['url']}\">{datetime.datetime.strptime(last['yyyymmdd'], '%Y%m%d').strftime('%B %d, %Y')}</a>"
            else:
                return f"{datetime.datetime.strptime(last['yyyymmdd'], '%Y%m%d').strftime('%B %d, %Y')}"

        if has_wlt:
            self.live_detail_fn = detail_wlt
            self.hist_detail_fn = detail_date
        else:
            self.live_detail_fn = detail_last
            self.hist_detail_fn = detail_date
    def new_elos(self):
        return {
            "team": {},
            "recent_matches": {}, #save recent matches, used for last 180 days performance
            "team_last_match": {}, #save most recent match info, used for the leaderboard
            "player_last_match": {} #save most recent match info, used for the leaderboard
        }
    def initialize_elos(self, team, basic_info):
        self.ml_elos["team"].setdefault(team, self.starting_elo)
        self.adj_elos["team"].setdefault(team, self.starting_elo)
    def compute_match_adj_elo(self, team0, team1, basic_info, team_to_info, team0_elos, team1_elos):
        match_adj_elo = team0_elos["team"][team0]
        difficulty = team1_elos["team"][team1]
        return match_adj_elo, difficulty
    def update_elos_from_perf(self, elos, basic_info, team_to_info, team_to_perf):
        for team in team_to_perf:
            info = team_to_info[team]
            perf = team_to_perf[team]
            score = basic_info["total_score"]
            elos["team"][team] += self.k * perf
    def update_player_elos(self, update_elo, basic_info, team_to_info):
        raise #no player elos by default
    def get_players(self, team_to_info):
        raise
    def shrink_adj_elos(self):
        elos = self.adj_elos
        for team in elos["team"]:
            elos["team"][team] = 0.5 * (elos["team"][team] + self.starting_elo)
    def print_elos(self):
        print("ml elo")
        sorted_ml_elos = sorted([(team, self.ml_elos["team"][team]) for team in self.ml_elos["team"]], key = lambda x: x[1])
        for x in sorted_ml_elos[::-1][:100]:
            print(x)

        print("cur adjusted elo")
        sorted_adj_elos = sorted([(team, self.adj_elos["team"][team]) for team in self.adj_elos["team"]], key = lambda x: x[1])
        #for x in [x for x in sorted_adj_elos if x[0] in self.performances][::-1][:200]:
        for x in [x for x in sorted_adj_elos][::-1][:200]:
            print(x, self.adj_elos["team_last_match"][x[0]])

        print("best all-time")
        for x in self.alltime_team_top_25:
            print(x)

        print("performances")
        sorted_performances = sorted([(team, self.performances[team]) for team in self.performances], key = lambda x: x[1])
        for x in sorted_performances[::-1][:100]:
            print(x)

        if "player" in self.adj_elos:
            sorted_player_elos = sorted([(player, self.adj_elos["player"][player]) for player in self.adj_elos["player"]], key = lambda x: x[1])
            for x in sorted_player_elos[::-1][:100]:
                print(x)
            print("best all-time players")
            for x in self.alltime_player_top_25:
                print(x)

    def write_elos(self):
        sorted_adj_elos = sorted([(team, self.adj_elos["team"][team]) for team in self.adj_elos["team"]], key = lambda x: x[1])
        team_writer = csv.DictWriter(open(f"/tmp/{self.prefix}_teams.csv","w"), fieldnames=["team","elo","detail"])
        team_writer.writeheader()
        for x in [x for x in sorted_adj_elos if x[0] in self.performances][::-1][:50]:
            last = self.adj_elos["team_last_match"][x[0]]
            wlt = "Win" if last["score"] > last["opp_score"] else ("Loss" if last["score"] < last["opp_score"] else "Tie")
            team_writer.writerow({
                "team": x[0],
                "elo": round(x[1]),
                "detail": self.live_detail_fn(last)
            })

        alltime_team_writer = csv.DictWriter(open(f"/tmp/{self.prefix}_alltime_teams.csv","w"), fieldnames=["team","elo","detail"])
        alltime_team_writer.writeheader()
        for x in self.alltime_team_top_25:
            alltime_team_writer.writerow({
                "team": x["name"],
                "elo": round(x["elo"]),
                "detail": self.hist_detail_fn(x["last"])
            })
        if "player" in self.adj_elos:
            sorted_player_elos = sorted([(player, self.adj_elos["player"][player]) for player in self.adj_elos["player"]], key = lambda x: x[1])
            player_writer = csv.DictWriter(open(f"/tmp/{self.prefix}_players.csv","w"), fieldnames=["player","elo","detail"])
            player_writer.writeheader()
            print("player info")
            for x in sorted_player_elos[::-1][:25]:
                last = self.adj_elos["player_last_match"][x[0]]
                player_writer.writerow({
                    "player":x[0],
                    "elo": round(x[1]),
                    "detail": self.live_detail_fn(last)
                })

            alltime_player_writer = csv.DictWriter(open(f"/tmp/{self.prefix}_alltime_players.csv","w"), fieldnames=["player","elo","detail"])
            alltime_player_writer.writeheader()
            for x in self.alltime_player_top_25:
                print(x)
                alltime_player_writer.writerow({
                    "player": x["name"],
                    "elo": round(x["elo"]),
                    "detail": self.hist_detail_fn(x["last"])
                })



    def update_alltime(self, top_25, info, window = 180):
        if len(top_25) < 25 or info["elo"] > top_25[-1]["elo"]:
            recent_peaks = [x for x in top_25 if x["name"] == info["name"] and diff_days(info["yyyymmdd"], x["yyyymmdd"]) <= window]
            if len(recent_peaks) == 0:
                top_25.append(info)
                top_25.sort(key = lambda x: x["elo"], reverse=True)
                del top_25[25:]
            elif len(recent_peaks) == 1:
                if info["elo"] > recent_peaks[0]["elo"]:
                    recent_peaks[0]["name"] = info["name"]
                    recent_peaks[0]["elo"] = info["elo"]
                    recent_peaks[0]["yyyymmdd"] = info["yyyymmdd"]
                    recent_peaks[0]["last"] = info["last"]
                    top_25.sort(key = lambda x: x["elo"], reverse=True)
            else:
                print(info["name"])
                print(recent_peaks)
                raise


    def generate_elos(self):
        #compute maximum likelihood elos (ml_elos)
        #these are the elos that best explain without taking
        #priors into account, which is suboptimal
        print("generating maximum likelihood")
        for i in range(self.ml_iter):
            print(f"iteration {i}")
            for reverse in [False, True]:
                err = self.update_elos_all_matches(False, reverse)
                if reverse == False:
                    print(f"Error: {err}")

        #adj_elos is a hamfisted attempt to include priors
        #doesn't feel too theoretically sound
        #adj_elos are computed by comparing against the ml_elos
        #and then shrinking all elos by 50% before each iteration
        print("generating adjusted elos")
        for i in range(self.adj_iter):
            print(f"iteration {i}")
            for reverse in [False, True]:
                #shrink adj_elos by 50% for priors
                self.shrink_adj_elos()
                err = self.update_elos_all_matches(True, reverse)
                if reverse == False:
                    print(f"Error: {err}")
        #run forward once more to finish
        #on the last iteration compute performances and leaderboard as well
        self.shrink_adj_elos()
        self.compute_performances()
    def compute_performances(self, performance_window = 180):
        for match_info in self.all_match_info:
            days_ago = (datetime.datetime.today() - datetime.datetime.strptime(match_info["basic_info"]["yyyymmdd"],"%Y%m%d")).days
            if days_ago > performance_window:
                self.update_elos_from_match(match_info["basic_info"], match_info["team_to_info"], True, False, True)
            else:
                self.update_elos_from_match(match_info["basic_info"], match_info["team_to_info"], True, True, True)
        for team in self.ml_elos["recent_matches"]:
            outcomes = self.ml_elos["recent_matches"][team] #opp_elo, sides_played, frac_won
            total_played = sum(x[1] for x in outcomes)
            avg_opp_elo = sum(x[0] * x[1] for x in outcomes) / total_played
            total_won = sum(x[1] * x[2] for x in outcomes)
            total_lost = total_played - total_won

            #standard tournament performance equation is
            #avg_opp_elo + 400 * (total_won - total_lost) / total_played
            #performances[team] = avg_opp_elo + 400 * (total_won - total_lost) / total_played

            #instead we want a formula that rewards teams playing longer at a high level
            #idea: approximate what would happen if you were to play the matches one at a time against opponents of that level
            #elo_delta = k * (0.5 - exp_win_pct)
            #          = k * (0.5 - (1.0 / (1.0 + 10**(-1 * elo_diff / 400.))))
            #where elo_diff is the difference between your current elo and the performance elo
            #setting x as the number of games played with this performance
            #and y as the difference between current elo and the performance elo
            #y' = k * (0.5 - (1.0 / (1.0 + 10**(-1 * y / 400.))))
            #y' = -1 * (k/2) * tanh(log(10) * y / 800)
            #thanks wolfram alpha ->
            #y = np.sign(y0) * (800 / math.log(10)) * np.arctanh((10 ** (c/400) / (10 ** (c/400) + 10 ** (k*x/800))) ** 0.5)
            #https://www.wolframalpha.com/input/?i=y%27+%3D+-tanh%28log%2810%29+*+y%2F800%29
            if total_won == 0:
                elo_perf = avg_opp_elo - 800 #technically undefined
            elif total_won == total_played:
                elo_perf = avg_opp_elo + 800 #technically undefined
            else:
                elo_perf = avg_opp_elo + compute_elo_diff(total_won / total_played)
            y0 = self.starting_elo - elo_perf
            c = 400 * math.log10((1 / (1 - (np.tanh(abs(y0) * math.log(10) / 800)) ** 2)) - 1)
            x = total_played
            yn = np.sign(y0) * (800 / math.log(10)) * np.arctanh(10 ** (c/800) / ((10 ** (c/400) + 10 ** (self.k*x/800)) ** 0.5))
            self.performances[team] = yn + elo_perf
    def update_elos_all_matches(self, update_adj_elos=False, reverse=False):
        total_err = {
            "team_err": 0,
            "player_err": 0
        }

        ordered_matches = self.all_match_info if not reverse else self.all_match_info[::-1]

        for match_info in ordered_matches:
            basic_info = match_info["basic_info"]
            team_to_info = match_info["team_to_info"]
            err = self.update_elos_from_match(basic_info, team_to_info, update_adj_elos)
            total_err["team_err"] += err.get("team_err",0)
            total_err["player_err"] += err.get("player_err",0)

        return total_err
    def calculate_team_performance(self):
        pass
    def update_elos_from_match(self, basic_info, team_to_info, update_adj_elos = False, record_performance = False, update_leaderboard = False):
        team_err = None
        player_err = None
        updates = [{
            "update_elo": self.ml_elos,
            "baseline_elo": self.ml_elos,
            "team_to_perf": {} #outcome - expected
        }]
        if update_adj_elos:
            updates = [{
                "update_elo": self.adj_elos,
                "baseline_elo": self.ml_elos,
                "team_to_perf": {}
            }]

        all_teams = list(team_to_info.keys())
        if len(all_teams) != 2:
            print(all_teams)
            raise
        for i,u in enumerate(updates):
            update_elo = u["update_elo"]
            baseline_elo = u["baseline_elo"]
            for j, (team, opp_team) in enumerate([all_teams, all_teams[::-1]]):
                self.initialize_elos(team, basic_info)
                self.initialize_elos(opp_team, basic_info)
                #compute the team's elo adjusted for this match
                #and the elo difficulty of this match
                match_adj_elo, match_difficulty = self.compute_match_adj_elo(team, opp_team, basic_info, team_to_info, update_elo, baseline_elo)
                outcome = team_to_info[team]["score"] / basic_info["total_score"]
                expected = compute_expected_raw(match_adj_elo - match_difficulty)
                delta = outcome - expected

                #add error once per match
                #if update_adj_elos is set then report of the error from using the adj_elos
                #otherwise report on the error from using the ml elos
                if i == (len(updates)-1) and j == 0:
                    #print(",".join([str(x) for x in [team,opp_team,update_elo["team"][team],baseline_elo["team"][opp_team],outcome,expected,delta]]))
                    team_err = delta**2
                u["team_to_perf"][team] = delta

                if "player" in self.adj_elos and i == (len(updates)-1) and j == 0:
                    player_err = self.update_player_elos(update_elo, basic_info, team_to_info)


                if record_performance:
                    update_elo["recent_matches"].setdefault(team,[])
                    update_elo["recent_matches"][team].append([match_difficulty, basic_info["total_score"], outcome])
                if update_leaderboard and update_elo == self.adj_elos:
                    update_elo["team_last_match"][team] = {
                        "score": outcome,
                        "opp_score": 1 - outcome,
                        "opp": opp_team,
                        "yyyymmdd": basic_info["yyyymmdd"],
                        "url": basic_info.get("url",None)
                    }
                    if "player" in self.adj_elos:
                        for player in self.get_players(team_to_info):
                            update_elo["player_last_match"][player] = {
                                "url": basic_info.get("url",None),
                                "yyyymmdd": basic_info["yyyymmdd"],
                            }

        for u in updates:
            update_elo = u["update_elo"]
            team_to_perf = u["team_to_perf"]
            self.update_elos_from_perf(update_elo, basic_info, team_to_info, team_to_perf)
            if update_leaderboard and update_elo == self.adj_elos:
                team_info = {
                    "name": team,
                    "elo": update_elo["team"][team],
                    "yyyymmdd": basic_info["yyyymmdd"],
                    "last": update_elo["team_last_match"][team]
                }
                self.update_alltime(self.alltime_team_top_25, team_info)

                #update player all time if necessary
                if "player" in update_elo:
                    for player in self.get_players(team_to_info):
                        if player not in update_elo["player"]:
                            continue #TODO: figure out why this happens
                        player_info = {
                            "name": player,
                            "elo": update_elo["player"][player],
                            "yyyymmdd": basic_info["yyyymmdd"],
                            "last": update_elo["team_last_match"][team]
                        }
                        self.update_alltime(self.alltime_player_top_25, player_info, 10**9)
        err = { "team_err": team_err }
        if player_err:
            err["player_err"] = player_err
        return err

def compute_expected_raw(elo_diff):
    return (1.0 / (1.0 + 10**(-1 * elo_diff / 400.)))

def compute_elo_diff(win_pct):
    return -400 * math.log10((1 / win_pct) - 1)

def diff_days(yyyymmdd1, yyyymmdd2):
    return (datetime.datetime.strptime(yyyymmdd1,"%Y%m%d") - datetime.datetime.strptime(yyyymmdd2,"%Y%m%d")).days
