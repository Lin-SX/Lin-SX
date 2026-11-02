#!/usr/bin/env python3
"""Dependency-free Xiangqi rules, shared game state, and README/SVG renderer."""
import html
import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
FILES = "abcdefghi"
NAMES = {"K": "将", "A": "士", "E": "象", "H": "马", "R": "车", "C": "炮", "P": "卒"}
EN_NAMES = {"K": "General", "A": "Advisor", "E": "Elephant", "H": "Horse", "R": "Rook", "C": "Cannon", "P": "Pawn"}


def initial():
    b = [[None] * 9 for _ in range(10)]
    back = "R H E A K A E H R".split()
    for x, k in enumerate(back):
        b[0][x] = "b" + k
        b[9][x] = "r" + k
    for x in (1, 7):
        b[2][x] = "bC"
        b[7][x] = "rC"
    for x in (0, 2, 4, 6, 8):
        b[3][x] = "bP"
        b[6][x] = "rP"
    return {"board": b, "turn": "r", "moves": [], "ply": 0}


def inside(x, y):
    return 0 <= x < 9 and 0 <= y < 10


def palace(c, x, y):
    return 3 <= x <= 5 and (7 <= y <= 9 if c == "r" else 0 <= y <= 2)


def king(b, c):
    for y, row in enumerate(b):
        for x, p in enumerate(row):
            if p == c + "K":
                return x, y
    return None


def piece_name(p):
    c, k = p
    name = NAMES[k]
    if k == "K":
        name = "帅" if c == "r" else "将"
    elif k == "A":
        name = "仕" if c == "r" else "士"
    elif k == "E":
        name = "相" if c == "r" else "象"
    elif k == "P":
        name = "兵" if c == "r" else "卒"
    return ("红" if c == "r" else "黑") + name


def attacks(b, x, y):
    p = b[y][x]
    c, k = p[0], p[1]
    e = "b" if c == "r" else "r"
    out = []

    def add(a, d):
        if inside(a, d) and (b[d][a] is None or b[d][a][0] == e):
            out.append((a, d))

    if k == "K":
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, d = x + dx, y + dy
            if palace(c, a, d):
                add(a, d)

        # Flying-general line of sight. This is used as an attack relation;
        # legal() deliberately does not model literal king capture.
        dy = -1 if c == "r" else 1
        d = y + dy
        while 0 <= d < 10:
            if b[d][x]:
                if b[d][x] == e + "K":
                    out.append((x, d))
                break
            d += dy

    elif k == "A":
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            a, d = x + dx, y + dy
            if palace(c, a, d):
                add(a, d)

    elif k == "E":
        for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            a, d = x + dx, y + dy
            own_side = d >= 5 if c == "r" else d <= 4
            eye_clear = inside(a, d) and b[y + dy // 2][x + dx // 2] is None
            if inside(a, d) and own_side and eye_clear:
                add(a, d)

    elif k == "H":
        for dx, dy, lx, ly in (
            (2, 1, 1, 0), (2, -1, 1, 0), (-2, 1, -1, 0), (-2, -1, -1, 0),
            (1, 2, 0, 1), (-1, 2, 0, 1), (1, -2, 0, -1), (-1, -2, 0, -1),
        ):
            a, d = x + dx, y + dy
            if inside(a, d) and b[y + ly][x + lx] is None:
                add(a, d)

    elif k in ("R", "C"):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, d = x + dx, y + dy
            screen = False
            while inside(a, d):
                q = b[d][a]
                if k == "R":
                    if q is None:
                        out.append((a, d))
                    else:
                        if q[0] == e:
                            out.append((a, d))
                        break
                elif not screen:
                    if q is None:
                        out.append((a, d))
                    else:
                        screen = True
                elif q:
                    if q[0] == e:
                        out.append((a, d))
                    break
                a += dx
                d += dy

    elif k == "P":
        dy = -1 if c == "r" else 1
        add(x, y + dy)
        crossed_river = y <= 4 if c == "r" else y >= 5
        if crossed_river:
            add(x - 1, y)
            add(x + 1, y)

    return out


def checked(b, c):
    pos = king(b, c)
    if pos is None:
        return True
    e = "b" if c == "r" else "r"
    return any(
        p and p[0] == e and pos in attacks(b, x, y)
        for y, row in enumerate(b)
        for x, p in enumerate(row)
    )


def legal(b, c):
    out = []
    enemy = "b" if c == "r" else "r"
    for y, row in enumerate(b):
        for x, p in enumerate(row):
            if not p or p[0] != c:
                continue
            for a, d in attacks(b, x, y):
                # A legal move answers check; the opposing king is never
                # literally captured in the shared-game state.
                if b[d][a] == enemy + "K":
                    continue
                t = deepcopy(b)
                t[d][a], t[y][x] = t[y][x], None
                if not checked(t, c):
                    out.append((x, y, a, d))
    return out


def position_status(b, c):
    moves = legal(b, c)
    in_check = checked(b, c)
    if moves:
        return ("check" if in_check else "playing"), moves
    return ("checkmate" if in_check else "stalemate"), moves


def apply(s, m):
    state, moves = position_status(s["board"], s["turn"])
    if state in ("checkmate", "stalemate"):
        raise ValueError("棋局已经结束，当前一方没有合法走法。")
    if m not in moves:
        raise ValueError("该走法不合法，可能已被其他玩家抢先落子。")

    x, y, a, d = m
    b = s["board"]
    p = b[y][x]
    cap = b[d][a]
    c = s["turn"]
    b[d][a], b[y][x] = p, None
    s["turn"] = "b" if c == "r" else "r"
    s["ply"] += 1
    s["moves"].append({
        "from": FILES[x] + str(y),
        "to": FILES[a] + str(d),
        "piece": p,
        "captured": cap,
        "by": c,
    })
    return s


def render_board_svg(s, output=None):
    """Render the current position as a traditional wood-style Xiangqi board."""
    b = s["board"]
    x0, y0, cell = 80, 90, 70
    right, bottom = x0 + 8 * cell, y0 + 9 * cell
    status, _ = position_status(b, s["turn"])

    # Extra footer space keeps the status safely below the bottom pieces.
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="850" viewBox="0 0 720 850">',
        '<defs><linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f8e8c6"/><stop offset=".48" stop-color="#e9c98f"/><stop offset="1" stop-color="#d7ad6e"/></linearGradient><radialGradient id="face" cx="34%" cy="28%" r="78%"><stop offset="0" stop-color="#fffdf4"/><stop offset=".58" stop-color="#f3dfb5"/><stop offset="1" stop-color="#d9b878"/></radialGradient><filter id="shadow" x="-35%" y="-35%" width="170%" height="180%"><feDropShadow dx="0" dy="3" stdDeviation="2.4" flood-color="#3e2816" flood-opacity=".38"/></filter><filter id="boardShadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="7" stdDeviation="8" flood-color="#3b2617" flood-opacity=".24"/></filter>',
        '<style>.grid{stroke:#6d4528;stroke-width:2;fill:none}.coord{font:14px ui-monospace,SFMono-Regular,Consolas,monospace;fill:#6f4728}.river{font:31px STKaiti,KaiTi,"Kaiti SC","Noto Serif CJK SC",serif;fill:#80532f}.piece text{font:700 31px STKaiti,KaiTi,"Kaiti SC","Noto Serif CJK SC",serif;stroke:#f5e6c7;stroke-width:.35;paint-order:stroke fill}.red text{fill:#a51f28}.black text{fill:#24211f}.status{font:650 16px system-ui,sans-serif;fill:#5e3c23}.status2{font:11px system-ui,sans-serif;fill:#7d5a3c}</style>',
        '<g id="black"><circle cy="1.5" r="29" fill="#9e6d38" opacity=".28"/><circle r="27" fill="url(#face)" stroke="#4b433c" stroke-width="3"/><circle r="21.7" fill="none" stroke="#4b433c" stroke-width="1.25" opacity=".82"/><circle cx="-8.5" cy="-10" r="2.1" fill="#4b433c" opacity=".22"/><circle cx="10" cy="8" r="1.5" fill="#4b433c" opacity=".16"/></g><g id="red"><circle cy="1.5" r="29" fill="#9e6d38" opacity=".28"/><circle r="27" fill="url(#face)" stroke="#bd343a" stroke-width="3"/><circle r="21.7" fill="none" stroke="#bd343a" stroke-width="1.25" opacity=".82"/><circle cx="-8.5" cy="-10" r="2.1" fill="#bd343a" opacity=".22"/><circle cx="10" cy="8" r="1.5" fill="#bd343a" opacity=".16"/></g></defs>',
        '<rect x="25" y="18" width="670" height="820" rx="28" fill="url(#paper)" stroke="#8f5e2f" stroke-width="3" filter="url(#boardShadow)"/><rect x="42" y="35" width="636" height="792" rx="19" fill="none" stroke="#b78248" stroke-width="1.3" opacity=".62"/>',
    ]

    svg.append('<g class="coord">')
    for x, label in enumerate("ABCDEFGHI"):
        svg.append(f'<text x="{x0 + x * cell}" y="58" text-anchor="middle">{label}</text>')
    for y in range(10):
        svg.append(f'<text x="42" y="{y0 + y * cell + 5}" text-anchor="middle">{y}</text>')
    svg.append("</g>")

    h = "".join(f"M{x0} {y0 + y * cell}H{right}" for y in range(10))
    v = f"M{x0} {y0}V{bottom}M{right} {y0}V{bottom}" + "".join(
        f"M{x0 + x * cell} {y0}V{y0 + 4 * cell}M{x0 + x * cell} {y0 + 5 * cell}V{bottom}"
        for x in range(1, 8)
    )
    palace_path = (
        f"M{x0 + 3 * cell} {y0}L{x0 + 5 * cell} {y0 + 2 * cell}"
        f"M{x0 + 5 * cell} {y0}L{x0 + 3 * cell} {y0 + 2 * cell}"
        f"M{x0 + 3 * cell} {y0 + 7 * cell}L{x0 + 5 * cell} {bottom}"
        f"M{x0 + 5 * cell} {y0 + 7 * cell}L{x0 + 3 * cell} {bottom}"
    )
    svg.append(f'<path class="grid" d="{h}{v}{palace_path}"/>')

    river_y = y0 + 4.5 * cell + 10
    svg.append(
        f'<g class="river" text-anchor="middle">'
        f'<text x="{x0 + 2 * cell}" y="{river_y}" letter-spacing="10">楚 河</text>'
        f'<text x="{x0 + 6 * cell}" y="{river_y}" letter-spacing="10">汉 界</text>'
        f"</g>"
    )

    for y, row in enumerate(b):
        for x, p in enumerate(row):
            if not p:
                continue
            cx, cy = x0 + x * cell, y0 + y * cell
            side = "red" if p[0] == "r" else "black"
            char = piece_name(p)[1:]
            svg.append(
                f'<g class="piece {side}" transform="translate({cx} {cy})" filter="url(#shadow)">'
                f'<use href="#{side}"/><text x="0" y="10" text-anchor="middle">{char}</text></g>'
            )

    if status in ("checkmate", "stalemate"):
        winner_cn = "黑方" if s["turn"] == "r" else "红方"
        winner_en = "Black" if s["turn"] == "r" else "Red"
        footer_cn, footer_en = f"棋局结束 · {winner_cn}胜", f"Game over · {winner_en} wins"
    else:
        side_cn = "红方" if s["turn"] == "r" else "黑方"
        side_en = "Red" if s["turn"] == "r" else "Black"
        footer_cn = f"当前回合 · {side_cn}" + (" · 将军" if status == "check" else "")
        footer_en = f"Turn · {side_en}" + (" · check" if status == "check" else "")

    # Keep both status lines clearly separated from the bottom rank of pieces.
    svg.append(
        f'<text class="status" x="360" y="785" text-anchor="middle">{footer_cn}</text>'
        f'<text class="status2" x="360" y="807" text-anchor="middle">{footer_en}</text>'
        "</svg>"
    )

    text = "".join(svg) + "\n"
    output = Path(output) if output else ROOT / "assets/xiangqi-board.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return text


def render(s, stats=None):
    b = s["board"]
    stats = stats or {}
    status, moves = position_status(b, s["turn"])
    render_board_svg(s)

    lines = [
        "<!-- XIANGQI:START -->",
        '<div align="center">',
        '<img src="assets/xiangqi-board.svg?v={s[\'ply\']}" width="720" alt="当前中国象棋棋盘 · Current Xiangqi board">',
        "</div>",
        "",
    ]

    if status in ("checkmate", "stalemate"):
        winner_cn = "黑方" if s["turn"] == "r" else "红方"
        winner_en = "Black" if s["turn"] == "r" else "Red"
        reason_cn = "被将死" if status == "checkmate" else "无合法走法"
        reason_en = "checkmate" if status == "checkmate" else "no legal moves"
        lines += [
            f"### 🏁 棋局结束：{winner_cn}胜",
            f"<sub><i>Game over: {winner_en} wins.</i></sub>",
            "",
            f"当前一方{reason_cn}。",
            f"<sub><i>The side to move has {reason_en}.</i></sub>",
        ]
    else:
        side_cn = "🔴 红方" if s["turn"] == "r" else "⚫ 黑方"
        side_en = "Red" if s["turn"] == "r" else "Black"
        lines += [
            f"### 当前回合：{side_cn}　·　已走 {s['ply']} 手" + ("　·　⚠️ 将军" if status == "check" else ""),
            f"<sub><i>Turn: {side_en} · {s['ply']} ply played" + (" · Check" if status == "check" else "") + ".</i></sub>",
            "",
            "### 🎯 选择下一步",
            "<sub><i>Choose the next move</i></sub>",
            "",
            "点击任一目标坐标，会打开一个已经填好走法的 GitHub Issue；提交后，Actions 会自动验证棋规并刷新棋盘。",
            "<br><sub><i>Click any destination to open a pre-filled GitHub Issue. After submission, Actions validates the move and refreshes the shared board automatically.</i></sub>",
            "",
            "| 棋子 / 起点<br><sub>Piece / From</sub> | 可选目标位置<br><sub>Legal destinations</sub> |",
            "|:---:|:---|",
        ]

        groups = {}
        for x, y, a, d in moves:
            groups.setdefault((x, y), []).append((a, d))

        for (x, y), dest in sorted(groups.items(), key=lambda z: (z[0][1], z[0][0])):
            p = b[y][x]
            cn = piece_name(p)[1:]
            en = EN_NAMES[p[1]]
            links = []
            for a, d in dest:
                mv = f"{FILES[x]}{y}-{FILES[a]}{d}"
                url = (
                    "https://github.com/Lin-SX/Lin-SX/issues/new?"
                    f"title={quote('Xiangqi move: ' + mv)}&body={quote('xiangqi: ' + mv)}"
                )
                links.append(f"[{FILES[a]}{d}]({url})")
            lines.append(f"| **{cn} {FILES[x]}{y}**<br><sub>{en}</sub> | " + " · ".join(links) + " |")

    lines += [
        "",
        "<details>",
        "<summary>📜 最近 5 步</summary>",
        "",
        "<sub><i>Last five moves in this game</i></sub>",
        "",
    ]
    recent = s["moves"][-5:][::-1]
    if recent:
        for m in recent:
            player = m.get("player")
            side_cn = "红方" if m["by"] == "r" else "黑方"
            side_en = "Red" if m["by"] == "r" else "Black"
            who_cn = f"@{player}" if player else "历史棋步"
            who_en = f"@{player}" if player else "recorded move"
            lines.append(
                f"- **{side_cn}** · {m['from']} → {m['to']} · {who_cn}"
                f"<br><sub><i>{side_en} · {m['from']} → {m['to']} · {who_en}</i></sub>"
            )
    else:
        lines.append("- 暂无走棋记录<br><sub><i>No moves yet.</i></sub>")

    lines += [
        "",
        "</details>",
        "",
        "<details>",
        "<summary>🏆 最活跃玩家 Top 10</summary>",
        "",
        "<sub><i>Top 10 most active players</i></sub>",
        "",
        "| 排名<br><sub>Rank</sub> | 玩家<br><sub>Player</sub> | 有效走棋<br><sub>Moves</sub> |",
        "|:---:|:---|---:|",
    ]
    ranking = sorted(stats.items(), key=lambda item: (-item[1], item[0].lower()))[:10]
    if ranking:
        for i, (player, count) in enumerate(ranking, 1):
            safe_player = html.escape(player)
            lines.append(f"| {i} | [@{safe_player}](https://github.com/{quote(player)}) | {count} |")
    else:
        lines.append("| — | 还没有统计数据<br><sub>No stats yet</sub> | 0 |")

    lines += [
        "",
        "</details>",
        "",
        "### ⚙️ 工作原理",
        "<sub><i>How it works</i></sub>",
        "",
        "1. **选择走法：** 点击棋盘下方的目标坐标，创建预填好的 GitHub Issue。<br><sub><i>Choose a move: click a destination below the board to create a pre-filled GitHub Issue.</i></sub>",
        "2. **自动判定：** GitHub Actions 运行 Python 象棋规则引擎，验证走法、将军与自陷将军等约束。<br><sub><i>Validate automatically: GitHub Actions runs the Python Xiangqi engine and checks move legality, check, and self-check.</i></sub>",
        "3. **更新棋局：** 合法走法写入共享状态，并自动刷新棋盘、最近走棋与玩家统计。<br><sub><i>Update the game: legal moves are committed to the shared state and the board, history, and player stats are regenerated.</i></sub>",
        "",
        "发现问题或有改进建议？欢迎 [提交 Issue](https://github.com/Lin-SX/Lin-SX/issues/new)。",
        "<br><sub><i>Found a bug or have an idea? Feel free to [open an issue](https://github.com/Lin-SX/Lin-SX/issues/new).</i></sub>",
        "<!-- XIANGQI:END -->",
    ]

    rp = ROOT / "README.md"
    old = rp.read_text(encoding="utf-8")
    start, end = "<!-- XIANGQI:START -->", "<!-- XIANGQI:END -->"
    rp.write_text(
        old[:old.index(start)] + "\n".join(lines) + old[old.index(end) + len(end):],
        encoding="utf-8",
    )


def main():
    statefile = ROOT / "state/game.json"
    statefile.parent.mkdir(exist_ok=True)
    if statefile.exists():
        s = json.loads(statefile.read_text(encoding="utf-8"))
    else:
        s = initial()
        statefile.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    statsfile = ROOT / "stats/moves.json"
    statsfile.parent.mkdir(exist_ok=True)
    if statsfile.exists():
        stats = json.loads(statsfile.read_text(encoding="utf-8"))
    else:
        stats = {}
        statsfile.write_text("{}\n", encoding="utf-8")

    render(s, stats)


if __name__ == "__main__":
    main()
