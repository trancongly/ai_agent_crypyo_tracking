import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS setups(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setup_name TEXT UNIQUE,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    winrate REAL DEFAULT 0
)
""")

conn.commit()


def update_setup(setup_name, success):

    cur.execute(
        "SELECT wins, losses FROM setups WHERE setup_name=?",
        (setup_name,)
    )

    row = cur.fetchone()

    if row is None:
        cur.execute(
            "INSERT INTO setups(setup_name,wins,losses) VALUES(?,?,?)",
            (setup_name,0,0)
        )

        wins = 0
        losses = 0
    else:
        wins, losses = row

    if success:
        wins += 1
    else:
        losses += 1

    total = wins + losses
    winrate = round((wins/total)*100,2)

    cur.execute("""
    UPDATE setups
    SET wins=?,
        losses=?,
        winrate=?
    WHERE setup_name=?
    """,(wins,losses,winrate,setup_name))

    conn.commit()


if __name__ == "__main__":
    print("Setup manager ready")
