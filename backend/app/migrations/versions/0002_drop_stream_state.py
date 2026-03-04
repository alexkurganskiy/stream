"""drop stream_state table"""

from alembic import op


revision = "0002_drop_stream_state"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("stream_state")


def downgrade() -> None:
    op.execute(
        "CREATE TABLE stream_state (id INTEGER PRIMARY KEY, started_at TIMESTAMP WITH TIME ZONE NOT NULL)"
    )
    op.execute("INSERT INTO stream_state (id, started_at) VALUES (1, NOW())")
