"""Add device ID and BMC IP columns to Host model

Revision ID: e3a769d9438f
Revises: b0ee04f071c6
Create Date: 2020-04-08 11:57:36.585027

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3a769d9438f'
down_revision = 'b0ee04f071c6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('hosts', sa.Column('bmc_ip', sa.String(length=39), nullable=True))
    op.add_column('hosts', sa.Column('device_id', sa.String(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('hosts', 'device_id')
    op.drop_column('hosts', 'bmc_ip')
    # ### end Alembic commands ###
