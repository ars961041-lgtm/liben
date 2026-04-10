from ..connection import get_db_conn

MAX_COUNTRIES_PER_ALLIANCE = 10
MAX_CITIES_PER_COUNTRY = 20

def create_alliance_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliances
    # PURPOSE: Player-created alliances that group multiple countries
    #          together for mutual defense and coordinated attacks.
    #          Power is recomputed from member countries' armies.
    #
    # COLUMNS:
    #   id            — Internal autoincrement PK.
    #   name          — Unique alliance name chosen by the founder.
    #   leader_id     — References users.user_id. The alliance founder/leader.
    #   power         — Computed total military power of all member countries.
    #   is_open       — 1 = anyone can request to join. 0 = invite-only.
    #   max_countries — Maximum number of member countries allowed. Default 10.
    #   description   — Optional alliance description shown in the profile.
    #   created_at    — When the alliance was founded.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliances (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT    UNIQUE,
        leader_id     INTEGER,
        power         REAL    DEFAULT 0,
        is_open       INTEGER DEFAULT 1,
        max_countries INTEGER DEFAULT 10,
        description   TEXT    DEFAULT '',
        created_at    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (leader_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_members
    # PURPOSE: Countries (and their owners) that belong to an alliance.
    #          Primary key is (alliance_id, user_id) — one row per
    #          player per alliance.
    #
    # COLUMNS:
    #   alliance_id     — References alliances.id.
    #   user_id         — The player who owns the member country.
    #   country_id      — The member country. NULL if country was deleted.
    #   role            — 'leader' or 'member'.
    #   loyalty_penalty — Penalty applied if the member betrayed the alliance.
    #   joined_at       — When this country joined.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_members (
        alliance_id     INTEGER,
        user_id         INTEGER,
        country_id      INTEGER,
        role            TEXT    DEFAULT 'member',
        loyalty_penalty REAL    DEFAULT 0,
        joined_at       INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (alliance_id, user_id),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id),
        FOREIGN KEY (country_id)  REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_invites
    # PURPOSE: Pending invitations to join an alliance.
    #          A cooldown prevents spamming the same user with invites.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   alliance_id  — Which alliance is sending the invite.
    #   from_user_id — The member who sent the invite.
    #   to_user_id   — The player being invited.
    #   status       — 'pending', 'accepted', or 'rejected'.
    #   created_at   — When the invite was sent. Used for cooldown checks.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_invites (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id  INTEGER,
        from_user_id INTEGER,
        to_user_id   INTEGER,
        status       TEXT    DEFAULT 'pending',
        created_at   INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id)  REFERENCES alliances(id),
        FOREIGN KEY (from_user_id) REFERENCES users(user_id),
        FOREIGN KEY (to_user_id)   REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_upgrade_types
    # PURPOSE: Master catalog of upgrades an alliance can purchase.
    #          Seeded at startup. Each type defines what the upgrade
    #          does and how much it costs per level.
    #
    # COLUMNS:
    #   id             — Internal autoincrement PK.
    #   name           — Unique English key (e.g. 'military_boost').
    #   name_ar        — Arabic display name.
    #   emoji          — Display emoji.
    #   category       — Upgrade group: 'military', 'support', 'intelligence'.
    #   effect_type    — What the upgrade does (e.g. 'attack_bonus', 'loot_bonus').
    #   effect_value   — Magnitude per level (e.g. 0.10 = +10% per level).
    #   description_ar — Arabic description shown to players.
    #   price          — Cost per level purchase.
    #   max_level      — Maximum level this upgrade can reach.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_upgrade_types (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    UNIQUE NOT NULL,
        name_ar        TEXT    NOT NULL,
        emoji          TEXT    DEFAULT '⬆️',
        category       TEXT    NOT NULL,
        effect_type    TEXT    NOT NULL,
        effect_value   REAL    DEFAULT 0,
        description_ar TEXT,
        price          REAL    DEFAULT 1000,
        max_level      INTEGER DEFAULT 5
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_upgrades
    # PURPOSE: Upgrades that a specific alliance has purchased.
    #          One row per upgrade type per alliance.
    #          Level increases with each purchase up to max_level.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   alliance_id     — Which alliance owns this upgrade.
    #   upgrade_type_id — References alliance_upgrade_types.id.
    #   level           — Current level of this upgrade (starts at 1).
    #   purchased_at    — When the last level was purchased.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_upgrades (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id     INTEGER NOT NULL,
        upgrade_type_id INTEGER NOT NULL,
        level           INTEGER DEFAULT 1,
        purchased_at    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id)     REFERENCES alliances(id),
        FOREIGN KEY (upgrade_type_id) REFERENCES alliance_upgrade_types(id),
        UNIQUE(alliance_id, upgrade_type_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_wars
    # PURPOSE: Wars declared between two alliances. Tracks the
    #          overall war state and which alliance won.
    #
    # COLUMNS:
    #   id         — Internal autoincrement PK.
    #   alliance_1 — One side of the war.
    #   alliance_2 — The other side.
    #   status     — 'active' or 'ended'.
    #   winner     — The winning alliance. NULL until resolved.
    #   started_at — When the war was declared.
    #   ended_at   — When the war ended. NULL if still active.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_wars (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_1 INTEGER,
        alliance_2 INTEGER,
        status     TEXT    DEFAULT 'active',
        winner     INTEGER,
        started_at INTEGER DEFAULT (strftime('%s','now')),
        ended_at   INTEGER,
        FOREIGN KEY (alliance_1) REFERENCES alliances(id),
        FOREIGN KEY (alliance_2) REFERENCES alliances(id),
        FOREIGN KEY (winner)     REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_battles
    # PURPOSE: Individual battles that occurred within an alliance war.
    #          Multiple battles can happen within a single war.
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   war_id            — References alliance_wars.id.
    #   attacker_alliance — The attacking alliance in this battle.
    #   defender_alliance — The defending alliance in this battle.
    #   result            — Outcome text (e.g. 'attacker_won').
    #   created_at        — When this battle occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_battles (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id            INTEGER,
        attacker_alliance INTEGER,
        defender_alliance INTEGER,
        result            TEXT,
        created_at        INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (war_id)            REFERENCES alliance_wars(id),
        FOREIGN KEY (attacker_alliance) REFERENCES alliances(id),
        FOREIGN KEY (defender_alliance) REFERENCES alliances(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_members_user ON alliance_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_members_alliance ON alliance_members(alliance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alliance_invites_to ON alliance_invites(to_user_id)")

    conn.commit()
    _seed_upgrade_types(conn)


def _seed_upgrade_types(conn):
    try:
        cursor = conn.cursor()
        upgrades = [
        ("military_boost",   "تعزيز عسكري",    "⚔️", "military",     "attack_bonus",   0.10, "يزيد قوة هجوم أعضاء التحالف 10% لكل مستوى",  2000, 5),
        ("defense_shield",   "درع الدفاع",      "🛡", "military",     "defense_bonus",  0.10, "يزيد دفاع أعضاء التحالف 10% لكل مستوى",       2000, 5),
        ("medical_corps",    "الفيلق الطبي",    "💊", "support",      "hp_bonus",       0.10, "يزيد نقاط الحياة 10% لكل مستوى",              1500, 5),
        ("intel_network",    "شبكة الاستخبارات","🕵️","intelligence", "spy_bonus",      1,    "يرفع مستوى الجواسيس بمقدار 1 لكل مستوى",      1800, 5),
        ("logistics",        "الإمداد والتموين","🚛", "support",      "loot_bonus",     0.05, "يزيد الغنائم 5% لكل مستوى",                   1200, 5),
        ("rapid_deployment", "النشر السريع",    "⚡", "military",     "travel_reduce",  120,  "يقلل وقت السفر 2 دقيقة لكل مستوى",            2500, 5),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO alliance_upgrade_types
            (name, name_ar, emoji, category, effect_type, effect_value, description_ar, price, max_level)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, upgrades)
        conn.commit()
    except Exception as e:
        print(f"[alliances] تجاهل seed: {e}")
