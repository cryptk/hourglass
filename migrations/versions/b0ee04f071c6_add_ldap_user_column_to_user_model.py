"""Add ldap_user column to user model

Revision ID: b0ee04f071c6
Revises: 22d14acc37df
Create Date: 2019-11-27 16:03:16.477422

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b0ee04f071c6'
down_revision = '22d14acc37df'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('ldap_user', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'ldap_user')
    # ### end Alembic commands ###