CREATE TABLE benchmark_suites (
	id VARCHAR(80) NOT NULL, 
	version VARCHAR(30) NOT NULL, 
	environment VARCHAR(20) NOT NULL, 
	name JSON NOT NULL, 
	description JSON NOT NULL, 
	protocol_version VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE leads (
	email VARCHAR(254) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	message TEXT NOT NULL, 
	consent BOOLEAN NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE organizations (
	name VARCHAR(120) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE providers (
	id VARCHAR(40) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	adapter VARCHAR(30) NOT NULL, 
	base_url VARCHAR(300) NOT NULL, 
	key_env VARCHAR(80) NOT NULL, 
	docs_url VARCHAR(500) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE rate_buckets (
	key VARCHAR(150) NOT NULL, 
	"window" INTEGER NOT NULL, 
	count INTEGER NOT NULL, 
	PRIMARY KEY (key)
)
-- statement
CREATE TABLE research_posts (
	slug VARCHAR(120) NOT NULL, 
	title JSON NOT NULL, 
	body JSON NOT NULL, 
	sources JSON NOT NULL, 
	published BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
)
-- statement
CREATE TABLE schema_revisions (
	revision VARCHAR(30) NOT NULL, 
	checksum VARCHAR(64) NOT NULL, 
	applied_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (revision)
)
-- statement
CREATE TABLE settings (
	key VARCHAR(100) NOT NULL, 
	value JSON NOT NULL, 
	PRIMARY KEY (key)
)
-- statement
CREATE TABLE sponsorships (
	organization VARCHAR(150) NOT NULL, 
	disclosure TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE tool_harnesses (
	id VARCHAR(80) NOT NULL, 
	version VARCHAR(40) NOT NULL, 
	tools JSON NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE users (
	email VARCHAR(254) NOT NULL, 
	password_hash TEXT NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	locale VARCHAR(2) NOT NULL, 
	email_verified BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('member','reviewer','admin')), 
	UNIQUE (email)
)
-- statement
CREATE TABLE webhook_events (
	id VARCHAR(150) NOT NULL, 
	kind VARCHAR(60) NOT NULL, 
	received_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
)
-- statement
CREATE TABLE workers (
	name VARCHAR(100) NOT NULL, 
	environment VARCHAR(20) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	capabilities JSON NOT NULL, 
	active BOOLEAN NOT NULL, 
	last_seen_at VARCHAR(40), 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (token_hash)
)
-- statement
CREATE TABLE api_keys (
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	label VARCHAR(80) NOT NULL, 
	scopes JSON NOT NULL, 
	active BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
)
-- statement
CREATE TABLE audit_logs (
	actor_id VARCHAR(36), 
	action VARCHAR(80) NOT NULL, 
	target VARCHAR(150) NOT NULL, 
	data JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
)
-- statement
CREATE TABLE benchmark_tasks (
	id VARCHAR(80) NOT NULL, 
	suite_id VARCHAR(80) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	title JSON NOT NULL, 
	difficulty VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(suite_id) REFERENCES benchmark_suites (id)
)
-- statement
CREATE TABLE idempotency_records (
	key VARCHAR(150) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	resource_id VARCHAR(80) NOT NULL, 
	PRIMARY KEY (key), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE CASCADE
)
-- statement
CREATE TABLE memberships (
	user_id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, organization_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)
-- statement
CREATE TABLE model_announcements (
	provider_id VARCHAR(40) NOT NULL, 
	api_id VARCHAR(150) NOT NULL, 
	source_url VARCHAR(500) NOT NULL, 
	metadata_json JSON NOT NULL, 
	reviewed BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (provider_id, api_id), 
	FOREIGN KEY(provider_id) REFERENCES providers (id)
)
-- statement
CREATE TABLE models (
	id VARCHAR(100) NOT NULL, 
	provider_id VARCHAR(40) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(provider_id) REFERENCES providers (id)
)
-- statement
CREATE TABLE notifications (
	user_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(50) NOT NULL, 
	data JSON NOT NULL, 
	read BOOLEAN NOT NULL, 
	delivered_at VARCHAR(40), 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
-- statement
CREATE TABLE saved_comparisons (
	user_id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	model_ids JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
-- statement
CREATE TABLE sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	csrf_hash VARCHAR(64) NOT NULL, 
	expires_at INTEGER NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
-- statement
CREATE TABLE subscriptions (
	user_id VARCHAR(36) NOT NULL, 
	provider_id VARCHAR(150) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	plan VARCHAR(50) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, plan), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (provider_id)
)
-- statement
CREATE TABLE model_follows (
	user_id VARCHAR(36) NOT NULL, 
	model_id VARCHAR(100) NOT NULL, 
	email_alerts BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, model_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(model_id) REFERENCES models (id)
)
-- statement
CREATE TABLE model_versions (
	model_id VARCHAR(100) NOT NULL, 
	api_id VARCHAR(150) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	availability VARCHAR(30) NOT NULL, 
	capabilities JSON NOT NULL, 
	source_url VARCHAR(500) NOT NULL, 
	source_checked_at VARCHAR(40) NOT NULL, 
	release_date VARCHAR(30), 
	alias BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (model_id, api_id), 
	FOREIGN KEY(model_id) REFERENCES models (id)
)
-- statement
CREATE TABLE task_versions (
	task_id VARCHAR(80) NOT NULL, 
	version VARCHAR(20) NOT NULL, 
	specification JSON NOT NULL, 
	spec_hash VARCHAR(64) NOT NULL, 
	visibility VARCHAR(20) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (task_id, version), 
	FOREIGN KEY(task_id) REFERENCES benchmark_tasks (id)
)
-- statement
CREATE TABLE agent_configurations (
	model_version_id VARCHAR(36), 
	harness_id VARCHAR(80) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	mode VARCHAR(30) NOT NULL, 
	reasoning VARCHAR(30) NOT NULL, 
	parameters JSON NOT NULL, 
	fixture BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (mode IN ('standardized','agentic','fixture')), 
	FOREIGN KEY(model_version_id) REFERENCES model_versions (id), 
	FOREIGN KEY(harness_id) REFERENCES tool_harnesses (id)
)
-- statement
CREATE TABLE price_history (
	model_version_id VARCHAR(36) NOT NULL, 
	input_per_million VARCHAR(30) NOT NULL, 
	output_per_million VARCHAR(30) NOT NULL, 
	cached_per_million VARCHAR(30), 
	source_url VARCHAR(500) NOT NULL, 
	checked_at VARCHAR(40) NOT NULL, 
	notes TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(model_version_id) REFERENCES model_versions (id)
)
-- statement
CREATE TABLE campaigns (
	name VARCHAR(150) NOT NULL, 
	suite_id VARCHAR(80) NOT NULL, 
	configuration_id VARCHAR(36) NOT NULL, 
	created_by VARCHAR(36), 
	state VARCHAR(30) NOT NULL, 
	fixture BOOLEAN NOT NULL, 
	authorized_microusd INTEGER NOT NULL, 
	reserved_microusd INTEGER NOT NULL, 
	spent_microusd INTEGER NOT NULL, 
	approval JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (authorized_microusd >= 0), 
	CHECK (reserved_microusd >= 0), 
	CHECK (spent_microusd >= 0), 
	CHECK (reserved_microusd + spent_microusd <= authorized_microusd), 
	FOREIGN KEY(suite_id) REFERENCES benchmark_suites (id), 
	FOREIGN KEY(configuration_id) REFERENCES agent_configurations (id), 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)
-- statement
CREATE TABLE runs (
	campaign_id VARCHAR(36) NOT NULL, 
	task_version_id VARCHAR(36) NOT NULL, 
	state VARCHAR(30) NOT NULL, 
	attempt INTEGER NOT NULL, 
	trial INTEGER NOT NULL, 
	fixture BOOLEAN NOT NULL, 
	environment VARCHAR(20) NOT NULL, 
	frozen_config JSON NOT NULL, 
	config_hash VARCHAR(64) NOT NULL, 
	lease_token_hash VARCHAR(64), 
	lease_expires_at INTEGER, 
	started_at VARCHAR(40), 
	finished_at VARCHAR(40), 
	duration_ms INTEGER, 
	input_tokens INTEGER, 
	output_tokens INTEGER, 
	cached_tokens INTEGER, 
	estimated_cost_microusd INTEGER, 
	observed_cost_microusd INTEGER, 
	error_code VARCHAR(100), 
	score JSON NOT NULL, 
	published BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (campaign_id, task_version_id, trial, attempt), 
	CHECK (state IN ('pending','preparing','running','evaluating','awaiting-review','completed','failed','cancelled')), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id), 
	FOREIGN KEY(task_version_id) REFERENCES task_versions (id)
)
-- statement
CREATE TABLE arena_matches (
	visitor_hash VARCHAR(64) NOT NULL, 
	left_run_id VARCHAR(36), 
	right_run_id VARCHAR(36), 
	left_fixture VARCHAR(30), 
	right_fixture VARCHAR(30), 
	fixture BOOLEAN NOT NULL, 
	task_id VARCHAR(80) NOT NULL, 
	expires_at INTEGER NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(left_run_id) REFERENCES runs (id), 
	FOREIGN KEY(right_run_id) REFERENCES runs (id), 
	FOREIGN KEY(task_id) REFERENCES benchmark_tasks (id)
)
-- statement
CREATE TABLE artifacts (
	run_id VARCHAR(36) NOT NULL, 
	name VARCHAR(180) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	media_type VARCHAR(100) NOT NULL, 
	public BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (run_id, name), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)
-- statement
CREATE TABLE human_reviews (
	run_id VARCHAR(36) NOT NULL, 
	reviewer_id VARCHAR(36), 
	verdict VARCHAR(20) NOT NULL, 
	rubric JSON NOT NULL, 
	notes TEXT NOT NULL, 
	conflict_of_interest BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id), 
	FOREIGN KEY(reviewer_id) REFERENCES users (id) ON DELETE SET NULL
)
-- statement
CREATE TABLE reports (
	user_id VARCHAR(36), 
	run_id VARCHAR(36), 
	reason TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)
-- statement
CREATE TABLE run_events (
	run_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(60) NOT NULL, 
	data JSON NOT NULL, 
	public BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)
-- statement
CREATE TABLE score_snapshots (
	run_id VARCHAR(36) NOT NULL, 
	protocol_version VARCHAR(60) NOT NULL, 
	snapshot JSON NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	supersedes VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id), 
	FOREIGN KEY(supersedes) REFERENCES score_snapshots (id)
)
-- statement
CREATE TABLE test_results (
	run_id VARCHAR(36) NOT NULL, 
	assertion_id VARCHAR(80) NOT NULL, 
	outcome VARCHAR(20) NOT NULL, 
	weight INTEGER NOT NULL, 
	blocking BOOLEAN NOT NULL, 
	observed JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (run_id, assertion_id), 
	CHECK (outcome IN ('passed','failed','not_run','error')), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)
-- statement
CREATE TABLE tool_calls (
	run_id VARCHAR(36) NOT NULL, 
	tool VARCHAR(100) NOT NULL, 
	arguments_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	duration_ms INTEGER NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)
-- statement
CREATE TABLE votes (
	match_id VARCHAR(36) NOT NULL, 
	visitor_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36), 
	choice VARCHAR(20) NOT NULL, 
	fixture BOOLEAN NOT NULL, 
	excluded BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (choice IN ('a','b','tie','both_bad')), 
	UNIQUE (match_id), 
	FOREIGN KEY(match_id) REFERENCES arena_matches (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)
-- statement
CREATE INDEX ix_benchmark_suites_environment ON benchmark_suites (environment)
-- statement
CREATE INDEX ix_leads_created_at ON leads (created_at)
-- statement
CREATE INDEX ix_organizations_created_at ON organizations (created_at)
-- statement
CREATE INDEX ix_rate_buckets_window ON rate_buckets ("window")
-- statement
CREATE INDEX ix_research_posts_created_at ON research_posts (created_at)
-- statement
CREATE INDEX ix_sponsorships_created_at ON sponsorships (created_at)
-- statement
CREATE INDEX ix_users_created_at ON users (created_at)
-- statement
CREATE INDEX ix_workers_created_at ON workers (created_at)
-- statement
CREATE INDEX ix_api_keys_created_at ON api_keys (created_at)
-- statement
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)
-- statement
CREATE INDEX ix_audit_logs_action ON audit_logs (action)
-- statement
CREATE INDEX ix_benchmark_tasks_suite_id ON benchmark_tasks (suite_id)
-- statement
CREATE INDEX ix_memberships_created_at ON memberships (created_at)
-- statement
CREATE INDEX ix_model_announcements_created_at ON model_announcements (created_at)
-- statement
CREATE INDEX ix_models_provider_id ON models (provider_id)
-- statement
CREATE INDEX ix_notifications_user_id ON notifications (user_id)
-- statement
CREATE INDEX ix_notifications_created_at ON notifications (created_at)
-- statement
CREATE INDEX ix_saved_comparisons_created_at ON saved_comparisons (created_at)
-- statement
CREATE INDEX ix_saved_comparisons_user_id ON saved_comparisons (user_id)
-- statement
CREATE INDEX ix_sessions_expires_at ON sessions (expires_at)
-- statement
CREATE INDEX ix_sessions_user_id ON sessions (user_id)
-- statement
CREATE INDEX ix_subscriptions_created_at ON subscriptions (created_at)
-- statement
CREATE INDEX ix_model_follows_created_at ON model_follows (created_at)
-- statement
CREATE INDEX ix_model_follows_user_id ON model_follows (user_id)
-- statement
CREATE INDEX ix_model_versions_model_id ON model_versions (model_id)
-- statement
CREATE INDEX ix_model_versions_created_at ON model_versions (created_at)
-- statement
CREATE INDEX ix_task_versions_created_at ON task_versions (created_at)
-- statement
CREATE INDEX ix_task_versions_task_id ON task_versions (task_id)
-- statement
CREATE INDEX ix_agent_configurations_created_at ON agent_configurations (created_at)
-- statement
CREATE INDEX ix_price_history_created_at ON price_history (created_at)
-- statement
CREATE INDEX ix_price_history_model_version_id ON price_history (model_version_id)
-- statement
CREATE INDEX ix_campaigns_state ON campaigns (state)
-- statement
CREATE INDEX ix_campaigns_created_at ON campaigns (created_at)
-- statement
CREATE INDEX ix_runs_campaign_id ON runs (campaign_id)
-- statement
CREATE INDEX ix_runs_created_at ON runs (created_at)
-- statement
CREATE INDEX ix_runs_published ON runs (published)
-- statement
CREATE INDEX ix_runs_task_version_id ON runs (task_version_id)
-- statement
CREATE INDEX ix_runs_state ON runs (state)
-- statement
CREATE INDEX ix_runs_lease_expires_at ON runs (lease_expires_at)
-- statement
CREATE INDEX ix_run_queue ON runs (state, environment, created_at)
-- statement
CREATE INDEX ix_arena_matches_visitor_hash ON arena_matches (visitor_hash)
-- statement
CREATE INDEX ix_arena_matches_created_at ON arena_matches (created_at)
-- statement
CREATE INDEX ix_artifacts_created_at ON artifacts (created_at)
-- statement
CREATE INDEX ix_artifacts_sha256 ON artifacts (sha256)
-- statement
CREATE INDEX ix_artifacts_run_id ON artifacts (run_id)
-- statement
CREATE INDEX ix_human_reviews_run_id ON human_reviews (run_id)
-- statement
CREATE INDEX ix_human_reviews_created_at ON human_reviews (created_at)
-- statement
CREATE INDEX ix_reports_created_at ON reports (created_at)
-- statement
CREATE INDEX ix_run_events_created_at ON run_events (created_at)
-- statement
CREATE INDEX ix_run_events_run_id ON run_events (run_id)
-- statement
CREATE INDEX ix_score_snapshots_created_at ON score_snapshots (created_at)
-- statement
CREATE INDEX ix_score_snapshots_run_id ON score_snapshots (run_id)
-- statement
CREATE INDEX ix_test_results_run_id ON test_results (run_id)
-- statement
CREATE INDEX ix_test_results_created_at ON test_results (created_at)
-- statement
CREATE INDEX ix_tool_calls_created_at ON tool_calls (created_at)
-- statement
CREATE INDEX ix_tool_calls_run_id ON tool_calls (run_id)
-- statement
CREATE INDEX ix_votes_visitor_hash ON votes (visitor_hash)
-- statement
CREATE INDEX ix_votes_created_at ON votes (created_at)
-- statement
CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Published snapshots are append-only'; END; $$
-- statement
CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON score_snapshots FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation()
