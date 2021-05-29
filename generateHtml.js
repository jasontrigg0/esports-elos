const { sortArray,readCsvFiles } = require("./csgo/util.js");
const { teamInfo } = require("./csgo/teams.js");
const { playerInfo } = require("./csgo/players.js");
moment = require('moment');
fs = require('fs');

function generateTabRow(tabInfo) {
  const START = `
      <div class="mdc-tab-bar" role="tablist">
        <div class="mdc-tab-scroller">
          <div class="mdc-tab-scroller__scroll-area">
            <div class="mdc-tab-scroller__scroll-content">
  `;

  let allTabs = [];
  for (let tab in tabInfo) {
    allTabs.push(`
                <button class="mdc-tab${tabInfo[tab]["active"] ? " mdc-tab--active" : ""}" role="tab" aria-selected="true" tabindex="0">
                  <span class="mdc-tab__content">
                    <span class="mdc-tab__icon material-icons" aria-hidden="true">${tabInfo[tab]["icon"]}</span>
                    <span class="mdc-tab__text-label">${tabInfo[tab]["label"]}</span>
                  </span>
                  <span class="mdc-tab-indicator${tabInfo[tab]["active"] ? " mdc-tab-indicator--active" : ""}">
                    <span class="mdc-tab-indicator__content mdc-tab-indicator__content--underline"></span>
                  </span>
                  <span class="mdc-tab__ripple"></span>
                </button>
    `);
  }

  const END = `
            </div>
          </div>
        </div>
      </div>
  `;

  return START + allTabs.join("\n") + END;
}

function generateHtml(gameInfo) {
  const tabInfo = {
    csgo: {
      label: "CS:GO live",
      icon: "trending_up",
      active: true
    },
    csgo_alltime: {
      label: "CS:GO all-time",
      icon: "calendar_today",
    },
  };

  const tabHtml = generateTabRow(tabInfo);

  let headerHtml = '<h2 style="padding-top: 10px; text-align: center">CS:GO Elo Ratings</h2><div style="text-align: center">Data from <a href="https://hltv.org">hltv.org</a>.</div>\n';

  let cardHtml = '';
  for (let game in gameInfo) {
    cardHtml += `<div style="margin-top: 25px; flex-direction: row; justify-content: space-around" class="tab-panel ${tabInfo[game]["active"] ? "active" : ""}">`;
    cardHtml += generateCards("Teams", gameInfo[game]["teams"], row => teamInfo[row["team"]]);
    cardHtml += generateCards("Players", gameInfo[game]["players"], row => playerInfo[row["player"]]);
    cardHtml += '</div>';
  }

  const HTML_HEADER = `
  <head>
    <!-- Required styles for MDC Web -->
    <link rel="stylesheet" href="https://unpkg.com/material-components-web@latest/dist/material-components-web.min.css">
    <link rel="stylesheet" href="mdc-demo-card.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
     .tab-panel {
       display: none;
     }
     .tab-panel.active {
       display: flex;
     }
    </style>
  </head>
  <body>
  `;

  const HTML_FOOTER = `
    <!-- Required MDC Web JavaScript library -->
    <script src="https://unpkg.com/material-components-web@latest/dist/material-components-web.min.js"></script>
    <script>
     //setup tabs
     window.onload = function() {
       for (const e of document.querySelectorAll(".mdc-tab-bar")) {
         let tab = new mdc.tabBar.MDCTabBar(e)
         tab.preventDefaultOnClick = true

         tab.listen("MDCTabBar:activated", function({detail: {index: index}}) {
           // Hide all panels.
           for (const t of document.querySelectorAll(".tab-panel")) {
             t.classList.remove("active")
           }

           // Show the current one.
           let tab = document.querySelector(".tab-panel:nth-child(" + (index + 4) + ")")
           tab.classList.add("active")
         })
       }
     };
    </script>
  </body>
</html>
  `;

  return HTML_HEADER + tabHtml + headerHtml + cardHtml + HTML_FOOTER;
}

function generateCard(image, header1, header2, header3, header4) {
    return `
    <div class="mdc-card" style="margin-bottom: 20px; max-width: 500px;">
      <div style="display: flex; justify-content: space-between; align-items: center; min-height: 155px">
        <div style="display: flex; margin-left: 25px; height: 120px; width: 120px; justify-content: center; align-items: center">
          <img style="max-height: 120px; max-width: 100px" src="${image}"></img>
        </div>
        <div>
          <div class="demo-card__primary">
            <h2 style="text-align: right" class="demo-card__title mdc-typography mdc-typography--headline6">${header1}</h2>
            <h2 style="text-align: right" class="demo-card__title mdc-typography mdc-typography--headline6">${header2}</h2>
          </div>
          <div style="text-align: right; padding-bottom: 0" class="demo-card__secondary mdc-typography mdc-typography--body2">${header3}</div>
          <div style="text-align: right" class="demo-card__secondary mdc-typography mdc-typography--body2">${header4}</div>
        </div>
      </div>
    </div>`;
}

function generateCards(title, info, fn) {
  let allCards = [];
  let cnt = 1;
  for (let row of info) {
    if (!fn(row)) {
      console.log(title);
      console.log("not found");
      console.log(fn(row));
      console.log(row);
      console.log(row["team"]);
      console.log(teamInfo[row["team"]]);
    }

    let card = generateCard(
      fn(row) ? fn(row)["image"]: "",
      `#${cnt} ${fn(row)["name"]}`,
      `${row["elo"]}`,
      `${row["detail"] ? row["detail"] : ""}`,
      ``
    );
    allCards.push(card);
    cnt += 1;
    if (cnt > 25) break;
  }
  let html = "";
  let header = `<div style="text-align: center; padding-bottom: 10px">${title}</div>`;

  return `  <div style="max-width: 500px">` + header + allCards.join("\n") + "\n" + `  </div>`;
}

async function main() {
  let teams = [];
  for await (let row of readCsvFiles(['/tmp/teams.csv'])) {
    if (row["team"] === "/team/5752/cloud9" && row["detail"] === '<a href="https://hltv.org/matches/2346948/cloud9-vs-mibr-esl-pro-league-season-13">Last match</a>') {
      continue;
    }
    if (row["team"] === "/team/7733/mibr-1") {
      continue;
    }
    teams.push(row);
  }

  let players = [];
  for await (let row of readCsvFiles(['/tmp/players.csv'])) {
    players.push(row);
  }

  let alltime_teams = [];
  for await (let row of readCsvFiles(['/tmp/alltime_teams.csv'])) {
    // if (row["team"] === "/team/7733/mibr-1") {
    //   continue;
    // }
    alltime_teams.push(row);
  }

  let alltime_players = [];
  for await (let row of readCsvFiles(['/tmp/alltime_players.csv'])) {
    alltime_players.push(row);
  }

  const gameInfo = {
    csgo: {
      teams: teams,
      players: players
    },
    csgo_alltime: {
      teams: alltime_teams,
      players: alltime_players
    }
  };

  const html = generateHtml(gameInfo);

  fs.writeFile('index.html', html, function (err) {
    if (err) return console.log(err);
  });
}

main();
