"""Model admin, token reset password, dan activity log."""

from database import execute, fetch_all, fetch_one, transaction

ADMIN_PUBLIC_COLUMNS = (
    "id, username, email, full_name, status, last_login, "
    "created_at, updated_at"
)


def count_admins():
    return fetch_one("SELECT COUNT(*) AS total FROM admins")["total"]


def get_admin(admin_id):
    return fetch_one(
        f"SELECT {ADMIN_PUBLIC_COLUMNS} FROM admins WHERE id = %s",
        (admin_id,),
    )


def get_admin_with_password(admin_id):
    return fetch_one("SELECT * FROM admins WHERE id = %s", (admin_id,))


def find_by_login(login):
    """Mencari admin berdasarkan username atau email."""
    return fetch_one(
        "SELECT * FROM admins WHERE username = %s OR email = %s LIMIT 1",
        (login, login.lower()),
    )


def find_by_email(email):
    return fetch_one(
        "SELECT * FROM admins WHERE email = %s", (email.lower(),)
    )


def username_or_email_taken(username, email, exclude_id=None):
    sql = "SELECT id FROM admins WHERE (username = %s OR email = %s)"
    params = [username, email.lower()]
    if exclude_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_id)
    return fetch_one(sql, params) is not None


def create_admin(username, email, full_name, password_hash):
    return execute(
        "INSERT INTO admins (username, email, full_name, password_hash) "
        "VALUES (%s, %s, %s, %s)",
        (username, email.lower(), full_name, password_hash),
    )


def update_profile(admin_id, username, email, full_name):
    execute(
        "UPDATE admins SET username = %s, email = %s, full_name = %s "
        "WHERE id = %s",
        (username, email.lower(), full_name, admin_id),
    )


def update_password(admin_id, password_hash):
    execute(
        "UPDATE admins SET password_hash = %s WHERE id = %s",
        (password_hash, admin_id),
    )


def touch_last_login(admin_id):
    execute(
        "UPDATE admins SET last_login = UTC_TIMESTAMP() WHERE id = %s",
        (admin_id,),
    )


def create_password_reset(admin_id, token_hash, minutes):
    with transaction() as cursor:
        cursor.execute(
            "DELETE FROM password_resets WHERE admin_id = %s "
            "AND used_at IS NULL",
            (admin_id,),
        )
        cursor.execute(
            "INSERT INTO password_resets (admin_id, token_hash, expires_at) "
            "VALUES (%s, %s, UTC_TIMESTAMP() + INTERVAL %s MINUTE)",
            (admin_id, token_hash, minutes),
        )


def find_valid_reset(token_hash):
    return fetch_one(
        "SELECT * FROM password_resets WHERE token_hash = %s "
        "AND used_at IS NULL AND expires_at > UTC_TIMESTAMP()",
        (token_hash,),
    )


def consume_reset(reset_id, admin_id, password_hash):
    with transaction() as cursor:
        cursor.execute(
            "UPDATE password_resets SET used_at = UTC_TIMESTAMP() "
            "WHERE id = %s AND used_at IS NULL",
            (reset_id,),
        )
        if cursor.rowcount != 1:
            return False
        cursor.execute(
            "UPDATE admins SET password_hash = %s WHERE id = %s",
            (password_hash, admin_id),
        )
    return True


def log_activity(admin_id, action, description=None, entity_type=None,
                 entity_id=None, ip_address=None):
    execute(
        "INSERT INTO activity_logs "
        "(admin_id, action, entity_type, entity_id, description, ip_address) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (admin_id, action, entity_type, entity_id,
         (description or "")[:500] or None, ip_address),
    )


def recent_activity(limit=20):
    return fetch_all(
        "SELECT l.id, l.action, l.entity_type, l.entity_id, l.description, "
        "l.created_at, a.username, a.full_name "
        "FROM activity_logs l LEFT JOIN admins a ON a.id = l.admin_id "
        "ORDER BY l.created_at DESC, l.id DESC LIMIT %s",
        (limit,),
    )
