from ..connection import get_db_conn


def create_advanced_war_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_battles
    # PURPOSE: Records every country-vs-country battle from launch
    #          to resolution. Tracks travel phase, live battle phase,
    #          outcome, and loot. The central table of the war system.
    #
    # COLUMNS:
    #   id                  — Internal autoincrement PK.
    #   attacker_country_id — The country that launched the attack.
    #   defender_country_id — The country being attacked.
    #   attacker_user_id    — Telegram user ID of the attacker.
    #   defender_user_id    — Telegram user ID of the defender.
    #   status              — Battle phase: 'traveling' → 'in_battle' → 'finished'.
    #   travel_end_time     — Unix timestamp when the attacker arrives.
    #   battle_end_time     — Unix timestamp when the battle resolves.
    #   winner_country_id   — The winning country. NULL until resolved.
    #   loot                — Currency transferred to the winner.
    #   attacker_power      — Attacker's total power at battle start.
    #   defender_power      — Defender's total power at battle start.
    #   battle_type         — 'normal' or 'sudden' (surprise attack, faster travel).
    #   created_at          — When the attack was launched.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_battles (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        defender_country_id INTEGER NOT NULL,
        attacker_user_id    INTEGER NOT NULL,
        defender_user_id    INTEGER NOT NULL,
        status              TEXT    DEFAULT 'traveling',
        travel_end_time     INTEGER,
        battle_end_time     INTEGER,
        winner_country_id   INTEGER,
        loot                REAL    DEFAULT 0,
        attacker_power      REAL    DEFAULT 0,
        defender_power      REAL    DEFAULT 0,
        battle_type         TEXT    DEFAULT 'normal',
        created_at          INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
        FOREIGN KEY (defender_country_id) REFERENCES countries(id),
        FOREIGN KEY (attacker_user_id)    REFERENCES users(user_id),
        FOREIGN KEY (defender_user_id)    REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: battle_supporters
    # PURPOSE: Countries that joined an ongoing battle to support
    #          one side. Their power is added to the side they chose.
    #
    # COLUMNS:
    #   id                — Internal autoincrement PK.
    #   battle_id         — References country_battles.id.
    #   country_id        — The supporting country.
    #   user_id           — The player who sent the support.
    #   side              — 'attacker' or 'defender'.
    #   power_contributed — How much power this supporter added.
    #   joined_at         — When they joined the battle.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_supporters (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id         INTEGER NOT NULL,
        country_id        INTEGER NOT NULL,
        user_id           INTEGER NOT NULL,
        side              TEXT    NOT NULL,
        power_contributed REAL    DEFAULT 0,
        joined_at         INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(battle_id, country_id),
        FOREIGN KEY (battle_id)  REFERENCES country_battles(id),
        FOREIGN KEY (country_id) REFERENCES countries(id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: spy_units
    # PURPOSE: Stores each country's espionage capability stats.
    #          One row per country. Controls spy mission success rates
    #          and how well the country hides its real army stats.
    #
    # COLUMNS:
    #   id               — Internal autoincrement PK.
    #   country_id       — References countries.id. UNIQUE — one row per country.
    #   spy_count        — Number of active spy units available.
    #   counter_intel    — Counter-intelligence strength. Reduces enemy spy success.
    #   spy_level        — Overall spy capability level. Affects mission outcomes.
    #   defense_level    — Defense against incoming spy operations.
    #   camouflage_level — How well the country hides its real army stats from spies.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_units (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id       INTEGER NOT NULL,
        spy_count        INTEGER DEFAULT 0,
        counter_intel    INTEGER DEFAULT 0,
        spy_level        INTEGER DEFAULT 1,
        defense_level    INTEGER DEFAULT 1,
        camouflage_level INTEGER DEFAULT 1,
        UNIQUE(country_id),
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: spy_operations
    # PURPOSE: Immutable log of every spy mission attempted.
    #          Used for history, achievement tracking, and leaderboards.
    #
    # COLUMNS:
    #   id                  — Internal autoincrement PK.
    #   attacker_country_id — The country that sent the spy.
    #   target_country_id   — The country being spied on.
    #   result              — 'success', 'partial', or 'failed'.
    #   info_obtained       — JSON or text of what was discovered. NULL on failure.
    #   created_at          — When the operation was executed.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spy_operations (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        target_country_id   INTEGER NOT NULL,
        result              TEXT,
        info_obtained       TEXT,
        created_at          INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
        FOREIGN KEY (target_country_id)   REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: cards
    # PURPOSE: Master catalog of all battle cards players can buy
    #          and use during battles. Seeded at startup.
    #          Cards provide temporary combat, time, or spy effects.
    #
    # COLUMNS:
    #   id             — Internal autoincrement PK.
    #   name           — Unique English key (e.g. 'power_boost').
    #   name_ar        — Arabic display name shown to players.
    #   emoji          — Display emoji.
    #   category       — Card group: 'time', 'combat', 'spy', 'special'.
    #   effect_type    — What the card does (e.g. 'attack_boost', 'reduce_travel').
    #   effect_value   — Magnitude of the effect (e.g. 0.25 = 25% boost).
    #   description_ar — Arabic description shown to the player.
    #   price          — Cost in currency to purchase this card.
    #   max_uses       — How many times the card can be used per purchase.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    NOT NULL UNIQUE,
        name_ar        TEXT    NOT NULL,
        emoji          TEXT    DEFAULT '',
        category       TEXT    NOT NULL,
        effect_type    TEXT    NOT NULL,
        effect_value   REAL    DEFAULT 0,
        description_ar TEXT    DEFAULT '',
        price          REAL    DEFAULT 0,
        max_uses       INTEGER DEFAULT 1
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: user_cards
    # PURPOSE: Cards currently owned by players.
    #          Quantity decreases as cards are used in battles.
    #
    # COLUMNS:
    #   id       — Internal autoincrement PK.
    #   user_id  — The card owner.
    #   card_id  — References cards.id. Which card type.
    #   quantity — How many of this card the user currently holds.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_cards (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id  INTEGER NOT NULL,
        card_id  INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        UNIQUE(user_id, card_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (card_id) REFERENCES cards(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: player_reputation
    # PURPOSE: Tracks each player's loyalty and reputation score
    #          based on their behavior in battles and alliances.
    #          Affects whether support requests are auto-accepted.
    #
    # COLUMNS:
    #   user_id          — Primary key. References users.user_id.
    #   loyalty_score    — Overall reputation score. Starts at 50. Range 0–100.
    #   battles_helped   — Total battles this player supported an ally in.
    #   battles_ignored  — Times this player ignored a support request.
    #   betrayals        — Times this player betrayed an alliance.
    #   reputation_title — Display title based on score (e.g. 'محايد', 'خائن').
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_reputation (
        user_id          INTEGER PRIMARY KEY,
        loyalty_score    INTEGER DEFAULT 50,
        battles_helped   INTEGER DEFAULT 0,
        battles_ignored  INTEGER DEFAULT 0,
        betrayals        INTEGER DEFAULT 0,
        reputation_title TEXT    DEFAULT 'محايد',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: support_requests
    # PURPOSE: Pending requests sent to a player asking them to join
    #          a battle as a supporter. Tracks notification state
    #          to avoid spamming the same player repeatedly.
    #
    # COLUMNS:
    #   id                    — Internal autoincrement PK.
    #   battle_id             — Which battle needs support.
    #   requesting_country_id — The country asking for help.
    #   target_country_id     — The country being asked (NULL if targeting a user directly).
    #   target_user_id        — The player being asked.
    #   side                  — Which side they're being asked to support.
    #   status                — 'pending', 'accepted', or 'rejected'.
    #   last_sent_at          — Last time the notification was sent (throttle control).
    #   created_at            — When the request was first created.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_requests (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id             INTEGER NOT NULL,
        requesting_country_id INTEGER NOT NULL,
        target_country_id     INTEGER,
        target_user_id        INTEGER NOT NULL,
        side                  TEXT    NOT NULL,
        status                TEXT    DEFAULT 'pending',
        last_sent_at          INTEGER DEFAULT (strftime('%s','now')),
        created_at            INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (battle_id)             REFERENCES country_battles(id),
        FOREIGN KEY (requesting_country_id) REFERENCES countries(id),
        FOREIGN KEY (target_country_id)     REFERENCES countries(id),
        FOREIGN KEY (target_user_id)        REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_visibility
    # PURPOSE: Controls whether a country is publicly visible or
    #          hidden from attack lists. Hidden countries require
    #          a daily code to be attacked.
    #
    # COLUMNS:
    #   country_id          — Primary key. References countries.id.
    #   visibility_mode     — 'public' or 'hidden'.
    #   daily_attack_code   — Secret code required to attack a hidden country.
    #   code_generated_at   — When the current code was generated.
    #   hidden_cost_paid_at — When the daily hiding fee was last paid.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_visibility (
        country_id          INTEGER PRIMARY KEY,
        visibility_mode     TEXT    DEFAULT 'public',
        daily_attack_code   TEXT,
        code_generated_at   INTEGER DEFAULT 0,
        hidden_cost_paid_at INTEGER DEFAULT 0,
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: discovered_countries
    # PURPOSE: Tracks which countries a player has "discovered"
    #          through exploration or spy operations. Only discovered
    #          countries appear in the attack target list.
    #
    # COLUMNS:
    #   id                  — Internal autoincrement PK.
    #   attacker_country_id — The country that did the discovering.
    #   target_country_id   — The country that was discovered.
    #   discovered_at       — When the discovery happened.
    #   expires_at          — When the discovery expires. NULL = permanent.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discovered_countries (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_country_id INTEGER NOT NULL,
        target_country_id   INTEGER NOT NULL,
        discovered_at       INTEGER DEFAULT (strftime('%s','now')),
        expires_at          INTEGER,
        UNIQUE(attacker_country_id, target_country_id),
        FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
        FOREIGN KEY (target_country_id)   REFERENCES countries(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: country_freeze
    # PURPOSE: Temporarily prevents a country from being attacked.
    #          Applied automatically after a country transfer to
    #          protect the new owner during the transition period.
    #
    # COLUMNS:
    #   country_id   — Primary key. References countries.id.
    #   frozen_until — Unix timestamp until which the country is protected.
    #   reason       — Why it was frozen (e.g. 'transfer', 'admin').
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_freeze (
        country_id   INTEGER PRIMARY KEY,
        frozen_until INTEGER NOT NULL,
        reason       TEXT    DEFAULT 'transfer',
        FOREIGN KEY (country_id) REFERENCES countries(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_status ON country_battles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_attacker ON country_battles(attacker_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country_battles_defender ON country_battles(defender_country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_supporters_battle ON battle_supporters(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovered_attacker ON discovered_countries(attacker_country_id)")

    conn.commit()
    _seed_cards(conn)


def _seed_cards(conn):
    try:
        cursor = conn.cursor()
        cards = [
        ("speed_march",    "زحف سريع",          "⚡",  "time",    "reduce_travel",  600,  "تقلل وقت السفر بـ 10 دقائق",              300,  1),
        ("delay_enemy",    "تأخير العدو",        "⏳",  "time",    "delay_travel",   600,  "تؤخر هجوم العدو بـ 10 دقائق",             400,  1),
        ("instant_march",  "زحف فوري",           "🚀",  "time",    "reduce_travel",  1200, "تقلل وقت السفر بـ 20 دقيقة",              700,  1),
        ("power_boost",    "تعزيز القوة",        "💪",  "combat",  "attack_boost",   0.25, "تزيد قوة الهجوم 25%",                     500,  1),
        ("iron_shield",    "درع حديدي",          "🛡",  "combat",  "defense_boost",  0.30, "تزيد الدفاع 30%",                         500,  1),
        ("berserker_rage", "غضب المحارب",        "🔥",  "combat",  "hp_boost",       0.20, "تزيد نقاط الحياة 20%",                    400,  1),
        ("double_strike",  "ضربة مزدوجة",        "⚔️", "combat",  "attack_boost",   0.50, "تزيد الهجوم 50% لمعركة واحدة",            900,  1),
        ("spy_boost",      "تعزيز الجواسيس",     "🕵️","spy",     "spy_level_boost", 2,   "ترفع مستوى الجواسيس مؤقتاً",              350,  1),
        ("intel_reveal",   "كشف المعلومات",      "📡",  "spy",     "reveal_intel",   1,    "تكشف معلومات دقيقة عن العدو",             600,  1),
        ("counter_spy",    "مضاد التجسس",        "🛡️","spy",     "counter_boost",   2,   "يرفع مستوى مضاد التجسس",                  300,  1),
        ("fake_attack",    "هجوم وهمي",          "🎭",  "special", "fake_attack",    1,    "يبدو كهجوم حقيقي لكن بدون ضرر",           800,  1),
        ("sudden_attack",  "هجوم مباغت",         "💥",  "special", "sudden_attack",  1,    "وصول فوري لكن بقوة أقل 30%",              1000, 1),
        ("sabotage",       "تخريب",              "🧨",  "special", "sabotage",       0.20, "يقلل قوة العدو 20% قبل المعركة",          1200, 1),
        ("satellite",      "قمر صناعي",          "🛰️","special", "satellite",       1,   "يكشف الجيش الحقيقي ويقلل التمويه",        1500, 1),
        ("building_raid",  "غارة على المباني",   "🏚️","special", "building_raid",   1,   "تستهدف المباني بدلاً من الجنود",           700,  1),
        ("reveal_hidden",  "كشف المخفي",         "🔍",  "spy",     "reveal_hidden",  1,    "يكشف الدول المخفية ويضيفها لقائمة أهدافك", 800, 1),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO cards
            (name, name_ar, emoji, category, effect_type, effect_value, description_ar, price, max_uses)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, cards)
        conn.commit()
    except Exception as e:
        print(f"[advanced_war] تجاهل seed: {e}")
