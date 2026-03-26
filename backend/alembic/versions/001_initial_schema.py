"""Initial schema: users, waste_categories, locations, scans, routes

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="citizen"),
        sa.Column("city", sa.String(100)),
        sa.Column("ward_number", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- waste_categories ---
    op.create_table(
        "waste_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("category_group", sa.String(50)),
        sa.Column("urgency_weight", sa.Float(), server_default="1.0"),
        sa.Column("color_hex", sa.String(7)),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("name", name="uq_waste_categories_name"),
        sa.UniqueConstraint("slug", name="uq_waste_categories_slug"),
    )

    # --- locations ---
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("ward_number", sa.String(20)),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address_text", sa.Text()),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="valid_lat"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="valid_lon"),
    )
    op.create_index("ix_locations_city", "locations", ["city"])
    op.create_index("ix_locations_ward_number", "locations", ["ward_number"])

    # --- scans ---
    op.create_table(
        "scans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("image_path", sa.String(500)),
        sa.Column("image_hash", sa.String(64)),
        sa.Column("scan_status", sa.String(20), server_default="pending"),
        sa.Column("detected_classes", JSONB()),
        sa.Column(
            "dominant_category",
            sa.Integer(),
            sa.ForeignKey("waste_categories.id"),
            nullable=True,
        ),
        sa.Column("yolo_inference_ms", sa.Integer()),
        sa.Column("rag_response", sa.Text()),
        sa.Column("rag_sources", JSONB()),
        sa.Column("urgency_score", sa.Float(), server_default="0.0"),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_scans_image_hash", "scans", ["image_hash"])
    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_index("ix_scans_lat_lon", "scans", ["latitude", "longitude"])
    op.create_index("ix_scans_dominant_category", "scans", ["dominant_category"])

    # --- routes ---
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("ward_number", sa.String(20)),
        sa.Column("route_date", sa.Date(), nullable=False),
        sa.Column("waypoints", JSONB(), nullable=False),
        sa.Column("total_distance_km", sa.Float()),
        sa.Column("estimated_duration_min", sa.Integer()),
        sa.Column("status", sa.String(20), server_default="planned"),
        sa.Column("vehicle_id", sa.String(50)),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_routes_city", "routes", ["city"])
    op.create_index("ix_routes_route_date", "routes", ["route_date"])


def downgrade() -> None:
    op.drop_table("routes")
    op.drop_table("scans")
    op.drop_table("locations")
    op.drop_table("waste_categories")
    op.drop_table("users")
