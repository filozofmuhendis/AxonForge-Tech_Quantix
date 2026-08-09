"""Initial database schema definition

Revision ID: 001
Revises: 
Create Date: 2026-08-09 15:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Piyasalar (markets)
    op.create_table(
        'markets',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('trading_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('holidays', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true')
    )
    op.create_index(op.f('ix_markets_name'), 'markets', ['name'], unique=True)

    # 2. Varlıklar (assets)
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_class', sa.String(length=50), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true')
    )
    op.create_index(op.f('ix_assets_symbol'), 'assets', ['symbol'], unique=True)
    op.create_index(op.f('ix_assets_asset_class'), 'assets', ['asset_class'], unique=False)
    op.create_index(op.f('ix_assets_sector'), 'assets', ['sector'], unique=False)

    # 3. Fiyat Barları (price_bars)
    op.create_table(
        'price_bars',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('adj_close', sa.Float(), nullable=True),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('freshness_seconds', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_price_bars_timestamp'), 'price_bars', ['timestamp'], unique=False)

    # 4. Gün İçi Barlar (intraday_bars)
    op.create_table(
        'intraday_bars',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('freshness_seconds', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_intraday_bars_timestamp'), 'intraday_bars', ['timestamp'], unique=False)

    # 5. Temel Finansal Veriler (fundamentals)
    op.create_table(
        'fundamentals',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sector_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    op.create_index(op.f('ix_fundamentals_symbol'), 'fundamentals', ['symbol'], unique=False)

    # 6. Makroekonomik Veriler (macro_observations)
    op.create_table(
        'macro_observations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('indicator_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('data_quality_score', sa.Float(), nullable=False)
    )
    op.create_index(op.f('ix_macro_observations_indicator_name'), 'macro_observations', ['indicator_name'], unique=False)
    op.create_index(op.f('ix_macro_observations_timestamp'), 'macro_observations', ['timestamp'], unique=False)

    # 7. Haberler (news_articles)
    op.create_table(
        'news_articles',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('sentiment', sa.Float(), nullable=True),
        sa.Column('impact', sa.String(length=20), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=False)
    )
    op.create_index(op.f('ix_news_articles_published_at'), 'news_articles', ['published_at'], unique=False)
    op.create_index(op.f('ix_news_articles_event_type'), 'news_articles', ['event_type'], unique=False)

    # 8. Model Kayıt (models)
    op.create_table(
        'models',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('training_period', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='PRODUCTION'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    op.create_index(op.f('ix_models_model_id'), 'models', ['model_id'], unique=True)

    # 9. Model Tahminleri (model_predictions)
    op.create_table(
        'model_predictions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('prediction_value', sa.Float(), nullable=False),
        sa.Column('probability', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('horizon', sa.String(length=20), nullable=False),
        sa.Column('feature_version', sa.String(length=20), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=False),
        sa.Column('calibration_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_model_predictions_symbol'), 'model_predictions', ['symbol'], unique=False)
    op.create_index(op.f('ix_model_predictions_timestamp'), 'model_predictions', ['timestamp'], unique=False)

    # 10. Kompozit Sinyaller (signals)
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('signal_type', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('components', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('data_quality_score', sa.Float(), nullable=False),
        sa.Column('market_regime_state', sa.String(length=50), nullable=False),
        sa.Column('analog_similarity', sa.Float(), nullable=True),
        sa.Column('confidence_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('decision_trace', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    op.create_index(op.f('ix_signals_symbol'), 'signals', ['symbol'], unique=False)
    op.create_index(op.f('ix_signals_signal_type'), 'signals', ['signal_type'], unique=False)

    # 11. İşlem Önerileri (trade_proposals)
    op.create_table(
        'trade_proposals',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('entry_zone', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=False),
        sa.Column('target_price', sa.Float(), nullable=False),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=False),
        sa.Column('risk_gate_status', sa.String(length=50), nullable=False),
        sa.Column('position_size', sa.Float(), nullable=False),
        sa.Column('risk_amount', sa.Float(), nullable=False),
        sa.Column('holding_horizon', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('invalidation_conditions', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_trade_proposals_symbol'), 'trade_proposals', ['symbol'], unique=False)

    # 12. Karar Günlüğü (decision_journal)
    op.create_table(
        'decision_journal',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('thesis_text', sa.Text(), nullable=False),
        sa.Column('entry_reasoning', sa.Text(), nullable=False),
        sa.Column('exit_reasoning', sa.Text(), nullable=True),
        sa.Column('regime_at_entry', sa.String(length=50), nullable=False),
        sa.Column('risk_metrics_at_entry', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actual_outcome_pnl', sa.Float(), nullable=True),
        sa.Column('post_trade_evaluation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['proposal_id'], ['trade_proposals.id'], ondelete='CASCADE')
    )

    # 13. Portföyler (portfolios)
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='TRY'),
        sa.Column('cash', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    op.create_index(op.f('ix_portfolios_name'), 'portfolios', ['name'], unique=True)

    # 14. Portföy Pozisyonları (portfolio_positions)
    op.create_table(
        'portfolio_positions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('cost_basis', sa.Float(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_portfolio_positions_symbol'), 'portfolio_positions', ['symbol'], unique=False)

    # 15. Portföy İşlemleri (portfolio_transactions)
    op.create_table(
        'portfolio_transactions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.Column('fees', sa.Float(), nullable=False),
        sa.Column('slippage', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_portfolio_transactions_symbol'), 'portfolio_transactions', ['symbol'], unique=False)

    # 16. Emirler (orders)
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='CREATED'),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('stop_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_orders_symbol'), 'orders', ['symbol'], unique=False)

    # 17. Gerçekleşmeler (executions)
    op.create_table(
        'executions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('fill_price', sa.Float(), nullable=False),
        sa.Column('commission', sa.Float(), nullable=False),
        sa.Column('slippage', sa.Float(), nullable=False),
        sa.Column('execution_time', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE')
    )

    # 18. Geriye Dönük Testler (backtests)
    op.create_table(
        'backtests',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('benchmark_symbol', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )

    # 19. Backtest Çalışmaları (backtest_runs)
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cagr', sa.Float(), nullable=False),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('sharpe', sa.Float(), nullable=False),
        sa.Column('sortino', sa.Float(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('total_return', sa.Float(), nullable=False),
        sa.Column('trades_count', sa.Integer(), nullable=False),
        sa.Column('walk_forward_step', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtests.id'], ondelete='CASCADE')
    )

    # 20. Backtest İşlemleri (backtest_trades)
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('pnl_pct', sa.Float(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ondelete='CASCADE')
    )

    # 21. Ajan Seansları (agent_sessions)
    op.create_table(
        'agent_sessions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )

    # 22. Ajan Mesajları (agent_messages)
    op.create_table(
        'agent_messages',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('decision_trace_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id'], ondelete='CASCADE')
    )

    # 23. Denetim Günlükleri (audit_logs)
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('input_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False)
    )
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Tabloları tersten kaldır
    op.drop_table('audit_logs')
    op.drop_table('agent_messages')
    op.drop_table('agent_sessions')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('backtests')
    op.drop_table('executions')
    op.drop_table('orders')
    op.drop_table('portfolio_transactions')
    op.drop_table('portfolio_positions')
    op.drop_table('portfolios')
    op.drop_table('decision_journal')
    op.drop_table('trade_proposals')
    op.drop_table('signals')
    op.drop_table('model_predictions')
    op.drop_table('models')
    op.drop_table('news_articles')
    op.drop_table('macro_observations')
    op.drop_table('fundamentals')
    op.drop_table('intraday_bars')
    op.drop_table('price_bars')
    op.drop_table('assets')
    op.drop_table('markets')
