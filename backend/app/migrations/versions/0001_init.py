"""init schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("segment_len_sec", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("segments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("s3_prefix", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "playlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, unique=True),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "stream_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.execute("INSERT INTO stream_state (id, started_at) VALUES (1, NOW()) ON CONFLICT (id) DO NOTHING")


def downgrade() -> None:
    op.drop_table("stream_state")
    op.drop_table("playlist_items")
    op.drop_table("videos")
