"""
نظام الدبلوماسية الاستراتيجية للتحالفات
Alliance Diplomacy & Strategic Expansion — Database Schema

Tables:
  alliance_treaties        — المعاهدات الدبلوماسية بين التحالفات
  alliance_treaty_log      — سجل أحداث المعاهدات
  alliance_influence       — نقاط النفوذ والقوة الناعمة
  alliance_expansion       — طلبات الاستيعاب والاندماج والاتحادات
  alliance_federation      — الاتحادات المشكّلة بين تحالفات
  alliance_intelligence    — بيانات الاستخبارات لكل تحالف
  alliance_balance_log     — سجل تطبيق قواعد التوازن
"""
from ..connection import get_db_conn


def create_alliance_diplomacy_tables():
    conn = get_db_conn()
    cursor = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_treaties
    # PURPOSE: Diplomatic agreements between two alliances.
    #          Covers non-aggression pacts, military alliances,
    #          trade treaties, and betrayal tracking.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   alliance_a      — First party (proposer).
    #   alliance_b      — Second party (recipient).
    #   treaty_type     — 'non_aggression' | 'military_alliance' | 'trade' | 'protectorate'
    #   status          — 'pending' | 'active' | 'expired' | 'broken' | 'rejected'
    #   proposed_by     — user_id of the leader who proposed.
    #   accepted_by     — user_id of the leader who accepted.
    #   terms           — JSON text of treaty terms (optional metadata).
    #   duration_days   — How many days the treaty lasts (0 = permanent).
    #   starts_at       — When the treaty became active.
    #   expires_at      — When it expires (NULL if permanent).
    #   broken_at       — When it was broken (NULL if intact).
    #   broken_by       — Which alliance broke it.
    #   created_at      — When the proposal was made.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_treaties (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_a    INTEGER NOT NULL,
        alliance_b    INTEGER NOT NULL,
        treaty_type   TEXT    NOT NULL DEFAULT 'non_aggression',
        status        TEXT    NOT NULL DEFAULT 'pending',
        proposed_by   INTEGER NOT NULL,
        accepted_by   INTEGER,
        terms         TEXT    DEFAULT '{}',
        duration_days INTEGER DEFAULT 30,
        starts_at     INTEGER,
        expires_at    INTEGER,
        broken_at     INTEGER,
        broken_by     INTEGER,
        created_at    INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_a)  REFERENCES alliances(id),
        FOREIGN KEY (alliance_b)  REFERENCES alliances(id),
        FOREIGN KEY (proposed_by) REFERENCES users(user_id),
        FOREIGN KEY (accepted_by) REFERENCES users(user_id),
        FOREIGN KEY (broken_by)   REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_treaty_log
    # PURPOSE: Immutable audit trail for every treaty event.
    #
    # COLUMNS:
    #   id          — Internal autoincrement PK.
    #   treaty_id   — References alliance_treaties.id.
    #   event_type  — 'proposed' | 'accepted' | 'rejected' | 'expired' | 'broken'
    #   actor_id    — alliance_id that triggered the event.
    #   note        — Optional context.
    #   created_at  — When the event occurred.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_treaty_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        treaty_id   INTEGER NOT NULL,
        event_type  TEXT    NOT NULL,
        actor_id    INTEGER,
        note        TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (treaty_id) REFERENCES alliance_treaties(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_influence
    # PURPOSE: Tracks soft-power influence each alliance exerts
    #          over others. Strong alliances accumulate influence
    #          points that boost war voting weight and diplomacy.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   source_alliance — The alliance exerting influence.
    #   target_alliance — The alliance being influenced.
    #   influence_pts   — Current influence score (0–100).
    #   pressure_active — 1 = diplomatic pressure is being applied.
    #   last_updated    — When influence was last recalculated.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_influence (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        source_alliance INTEGER NOT NULL,
        target_alliance INTEGER NOT NULL,
        influence_pts   REAL    DEFAULT 0,
        pressure_active INTEGER DEFAULT 0,
        last_updated    INTEGER DEFAULT (strftime('%s','now')),
        UNIQUE(source_alliance, target_alliance),
        FOREIGN KEY (source_alliance) REFERENCES alliances(id),
        FOREIGN KEY (target_alliance) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_expansion
    # PURPOSE: Requests for absorption, merger, or federation
    #          between alliances. Tracks the full lifecycle.
    #
    # COLUMNS:
    #   id              — Internal autoincrement PK.
    #   initiator_id    — Alliance proposing the expansion.
    #   target_id       — Alliance being targeted.
    #   expansion_type  — 'absorb' | 'merge' | 'federate'
    #   status          — 'pending' | 'accepted' | 'rejected' | 'cancelled'
    #   proposed_by     — user_id of the proposing leader.
    #   terms           — JSON metadata (e.g. treasury split ratio).
    #   created_at      — When the proposal was made.
    #   resolved_at     — When it was accepted/rejected.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_expansion (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        initiator_id   INTEGER NOT NULL,
        target_id      INTEGER NOT NULL,
        expansion_type TEXT    NOT NULL DEFAULT 'merge',
        status         TEXT    NOT NULL DEFAULT 'pending',
        proposed_by    INTEGER NOT NULL,
        terms          TEXT    DEFAULT '{}',
        created_at     INTEGER DEFAULT (strftime('%s','now')),
        resolved_at    INTEGER,
        FOREIGN KEY (initiator_id) REFERENCES alliances(id),
        FOREIGN KEY (target_id)    REFERENCES alliances(id),
        FOREIGN KEY (proposed_by)  REFERENCES users(user_id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_federation
    # PURPOSE: Active federations — groups of alliances that share
    #          war voting bonuses and diplomatic weight.
    #
    # COLUMNS:
    #   id           — Internal autoincrement PK.
    #   name         — Federation name.
    #   leader_id    — The leading alliance of the federation.
    #   created_at   — When the federation was formed.
    #   dissolved_at — When it was dissolved (NULL if active).
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_federation (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT    NOT NULL UNIQUE,
        leader_id    INTEGER NOT NULL,
        created_at   INTEGER DEFAULT (strftime('%s','now')),
        dissolved_at INTEGER,
        FOREIGN KEY (leader_id) REFERENCES alliances(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_federation_members (
        federation_id INTEGER NOT NULL,
        alliance_id   INTEGER NOT NULL,
        joined_at     INTEGER DEFAULT (strftime('%s','now')),
        PRIMARY KEY (federation_id, alliance_id),
        FOREIGN KEY (federation_id) REFERENCES alliance_federation(id),
        FOREIGN KEY (alliance_id)   REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_intelligence
    # PURPOSE: Computed intelligence snapshot for each alliance.
    #          Updated by the interval scheduler. Used for strategic
    #          decisions, predictions, and soft-power calculations.
    #
    # COLUMNS:
    #   alliance_id        — PK. References alliances.id.
    #   activity_score     — 0–100. Based on recent war/vote participation.
    #   war_readiness      — 0–100. Based on military power vs avg.
    #   economic_stability — 0–100. Based on treasury balance & tax income.
    #   threat_level       — 0–100. Composite danger score for others.
    #   last_computed      — When this snapshot was last refreshed.
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_intelligence (
        alliance_id        INTEGER PRIMARY KEY,
        activity_score     REAL    DEFAULT 50,
        war_readiness      REAL    DEFAULT 50,
        economic_stability REAL    DEFAULT 50,
        threat_level       REAL    DEFAULT 50,
        last_computed      INTEGER DEFAULT 0,
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # ─────────────────────────────────────────────────────────────
    # TABLE: alliance_balance_log
    # PURPOSE: Records every time a balance rule was applied to an
    #          alliance (diminishing returns, instability penalty, etc.)
    # ─────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliance_balance_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        alliance_id INTEGER NOT NULL,
        rule_type   TEXT    NOT NULL,
        penalty     REAL    DEFAULT 0,
        note        TEXT    DEFAULT '',
        created_at  INTEGER DEFAULT (strftime('%s','now')),
        FOREIGN KEY (alliance_id) REFERENCES alliances(id)
    )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_treaties_a      ON alliance_treaties(alliance_a)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_treaties_b      ON alliance_treaties(alliance_b)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_treaties_status ON alliance_treaties(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_influence_src   ON alliance_influence(source_alliance)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_influence_tgt   ON alliance_influence(target_alliance)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expansion_init  ON alliance_expansion(initiator_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expansion_tgt   ON alliance_expansion(target_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fed_members     ON alliance_federation_members(alliance_id)")

    conn.commit()
    print("✅ [alliance_diplomacy] تم إنشاء جداول نظام الدبلوماسية.")
