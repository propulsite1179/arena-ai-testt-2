"""Original tasks and a sourced catalog. A catalog entry is never a test result."""
from sqlalchemy import select
from gamedev.database import (
    Provider, Model, ModelVersion, Harness, AgentConfiguration, Suite, Task,
    TaskVersion, PriceHistory, ResearchPost,
)
from gamedev.core.protocol import canonical_hash, HARNESS_VERSION, PROTOCOL_VERSION

CHECKED = '2026-10-13'
PROVIDERS = [
    ('openai', 'OpenAI', 'openai_responses', 'https://api.openai.com/v1', 'OPENAI_API_KEY', 'https://developers.openai.com/api/docs/models'),
    ('anthropic', 'Anthropic', 'anthropic_messages', 'https://api.anthropic.com/v1', 'ANTHROPIC_API_KEY', 'https://platform.claude.com/docs/en/models/overview'),
    ('google', 'Google', 'gemini', 'https://generativelanguage.googleapis.com/v1beta', 'GEMINI_API_KEY', 'https://ai.google.dev/gemini-api/docs/models'),
    ('deepseek', 'DeepSeek', 'openai_compatible', 'https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY', 'https://api-docs.deepseek.com/'),
    ('qwen', 'Qwen / Alibaba Cloud', 'openai_compatible', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1', 'DASHSCOPE_API_KEY', 'https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope'),
    ('zai', 'Z.ai', 'openai_compatible', 'https://api.z.ai/api/paas/v4', 'ZAI_API_KEY', 'https://docs.z.ai/guides/overview/quick-start'),
    ('moonshot', 'Moonshot', 'openai_compatible', 'https://api.moonshot.ai/v1', 'MOONSHOT_API_KEY', 'https://platform.moonshot.ai/docs/guide/start-using-kimi-api'),
]
MODELS = [
    ('gpt-6-astra', 'GPT-6 Astra', 'openai', 'gpt-6-astra', '10', '50', ['low','medium','high','xhigh','max']),
    ('gpt-6-1-sol', 'GPT-6.1 Sol', 'openai', 'gpt-6.1-sol', '2', '10', ['low','medium','high','xhigh','max']),
    ('gpt-6-luna', 'GPT-6 Luna', 'openai', 'gpt-6-luna', '0.1', '0.5', ['none','low','medium','high','xhigh','max']),
    ('claude-fable-5-1', 'Claude Fable 5.1', 'anthropic', 'claude-fable-5-1', '10', '50', []),
    ('claude-opus-5-5', 'Claude Opus 5.5', 'anthropic', 'claude-opus-5-5', '4', '20', []),
    ('claude-sonnet-5-5', 'Claude Sonnet 5.5', 'anthropic', 'claude-sonnet-5-5', '2', '10', []),
    ('gemini-3-8-flash', 'Gemini 3.8 Flash', 'google', 'gemini-3.8-flash', None, None, []),
    ('gemini-3-1-pro', 'Gemini 3.1 Pro Preview', 'google', 'gemini-3.1-pro-preview', None, None, []),
]
# Brief, observable assertions, and manual limits are original project content.
ROBLOX_TASKS = [
    ('rbx-obby', 'creation', 'Build a checkpoint obby', 'Cr\u00e9er un obby \u00e0 checkpoints',
     'Build six anchored platforms, a start, five numbered checkpoints and a finish. A fall returns the player to their highest unlocked checkpoint. Only the server changes progression.',
     'Cr\u00e9er six plateformes ancr\u00e9es, un d\u00e9part, cinq checkpoints num\u00e9rot\u00e9s et une arriv\u00e9e. Une chute ram\u00e8ne au dernier checkpoint. La progression est valid\u00e9e par le serveur.',
     ['platform_count', 'anchored_parts', 'ordered_progression', 'respawn_checkpoint'], 'Route readability and jump difficulty need independent player review.'),
    ('rbx-checkpoints', 'debugging', 'Repair checkpoint regression', 'R\u00e9parer les checkpoints',
     'Repair a checkpoint script that resets progress when an earlier checkpoint is touched. Preserve the public module API and verify repeated touches and respawns.',
     'Corriger une r\u00e9gression qui r\u00e9initialise la progression au contact d\u2019un ancien checkpoint. Conserver l\u2019API du module et tester les contacts r\u00e9p\u00e9t\u00e9s et les respawns.',
     ['monotonic_progress', 'repeat_touch', 'respawn', 'api_preserved'], 'Actual respawn behavior requires Studio play mode.'),
    ('rbx-inventory', 'coding', 'A server-owned inventory', 'Un inventaire g\u00e9r\u00e9 par le serveur',
     'Implement a 12-slot inventory with stacking, capacity, item validation and atomic removal. Expose Add, Remove and Snapshot methods. Invalid requests must not change state.',
     'Impl\u00e9menter 12 emplacements avec empilement, capacit\u00e9, validation des objets et retrait atomique. Exposer Add, Remove et Snapshot. Une requ\u00eate invalide ne modifie rien.',
     ['capacity', 'stacking', 'atomic_remove', 'input_validation'], 'UI usability is separate from correctness.'),
    ('rbx-remote-security', 'security', 'Validate a reward RemoteEvent', 'S\u00e9curiser un RemoteEvent de r\u00e9compense',
     'Replace a client-trusted reward amount with server-calculated rewards. Reject negative, huge, NaN and malformed values; enforce cooldown and ownership without punishing legitimate requests.',
     'Remplacer le montant envoy\u00e9 par le client par un calcul serveur. Rejeter les valeurs n\u00e9gatives, excessives, NaN ou malform\u00e9es ; imposer un d\u00e9lai et v\u00e9rifier la propri\u00e9t\u00e9.',
     ['server_authority', 'malformed_requests', 'cooldown', 'ownership'], 'Passing these cases is not a complete exploit-resistance audit.'),
    ('rbx-rewards', 'gameplay', 'Idempotent round rewards', 'R\u00e9compenses de manche idempotentes',
     'Award 10 coins to eligible players exactly once per round ID. Duplicate end-round events and reconnects must not duplicate the grant. Use a test persistence adapter, not a live datastore.',
     'Attribuer 10 pi\u00e8ces une seule fois par identifiant de manche. Les doublons et reconnexions ne doivent pas multiplier le gain. Utiliser un adaptateur de test, jamais un datastore r\u00e9el.',
     ['eligibility', 'single_grant', 'duplicate_event', 'reconnect'], 'Live DataStore consistency is not inferred from local adapter tests.'),
    ('rbx-ui', 'ui', 'Accessible quest interface', 'Interface de qu\u00eates accessible',
     'Create a quest panel with open/close, three objectives, a server-confirmed claim button and visible error state. Handle phone safe areas and keyboard focus.',
     'Cr\u00e9er un panneau ouvrable avec trois objectifs, un bouton de r\u00e9compense confirm\u00e9 par le serveur et des erreurs visibles. G\u00e9rer les zones s\u00fbres mobiles et le clavier.',
     ['open_close', 'claim_validation', 'error_state', 'mobile_layout'], 'Screen-reader support and visual hierarchy require human review.'),
    ('rbx-regression', 'debugging', 'Modify without breaking the game', 'Modifier sans r\u00e9gression',
     'Add a timed sprint to an existing movement controller. Preserve jumping, camera behavior and existing input bindings. Test cooldown, respawn and exhausted stamina.',
     'Ajouter un sprint temporaire au contr\u00f4leur existant sans casser le saut, la cam\u00e9ra ni les touches. Tester le d\u00e9lai, le respawn et l\u2019\u00e9puisement.',
     ['existing_jump', 'sprint_duration', 'cooldown', 'respawn_cleanup'], 'Camera feel requires a real player.'),
    ('rbx-world', 'world', 'Build a navigable island', 'Construire une \u00eele navigable',
     'Create an original low-poly island from primitive parts with three connected landmarks, a traversable route, collision-safe spawn and a 300-part maximum. No marketplace assets.',
     'Cr\u00e9er une \u00eele originale en formes simples, trois rep\u00e8res reli\u00e9s, un chemin praticable et un spawn libre. Maximum 300 pi\u00e8ces, sans assets du marketplace.',
     ['part_budget', 'spawn_clearance', 'landmarks', 'connected_route'], 'Artistic coherence and navigation readability are human criteria.'),
    ('rbx-multiplayer', 'multiplayer', 'Fix round synchronization', 'Corriger la synchronisation des manches',
     'Repair a round timer shared by a server and two clients. Late joiners must receive the current round state, and only the server may advance a round.',
     'R\u00e9parer un chronom\u00e8tre partag\u00e9 entre serveur et deux clients. Les nouveaux joueurs re\u00e7oivent l\u2019\u00e9tat courant ; seul le serveur lance une nouvelle manche.',
     ['server_authority', 'late_join', 'two_client_sync', 'single_transition'], 'Two-client testing is required; a single-client mock cannot verify this task.'),
    ('rbx-full-game', 'long-horizon', 'From baseplate to a complete game', 'De la baseplate au jeu complet',
     'Build an original five-minute crystal collection game: safe lobby, timed round, scoring, end screen, restart, mobile controls and server-owned scores. No purchases, external assets or publication.',
     'Construire un jeu original de collecte : lobby, manche chronom\u00e9tr\u00e9e, score serveur, fin, red\u00e9marrage et commandes tactiles. Sans achats, assets externes ni publication.',
     ['round_lifecycle', 'score_authority', 'restart', 'mobile_controls'], 'Gameplay, visual quality and fun need independent rubric-based reviews.'),
]
WEB_TASKS = [
    ('web-orbit', 'creation', 'Orbital Collector', 'Collecteur orbital',
     'Create an original 2D canvas game. Move with arrows or WASD, collect nine energy cells and avoid hazards. Include Start, Pause and Restart buttons, a visible numeric score and touch controls.',
     'Cr\u00e9er un jeu Canvas 2D : fl\u00e8ches ou WASD, neuf cellules d\u2019\u00e9nergie \u00e0 collecter et des obstacles. Pr\u00e9voir D\u00e9marrer, Pause, Recommencer, un score num\u00e9rique et des commandes tactiles.'),
    ('web-platformer', 'debugging', 'Repair a platformer checkpoint', 'R\u00e9parer un checkpoint de plateforme',
     'Repair the provided checkpoint regression: touching an earlier checkpoint must not lower progress. Keep keyboard and touch movement, a visible checkpoint score and restart behavior.',
     'Corriger la r\u00e9gression fournie : un ancien checkpoint ne diminue jamais la progression. Conserver d\u00e9placement clavier et tactile, score visible et red\u00e9marrage.'),
    ('web-responsive', 'ui', 'One game, every screen', 'Un jeu sur tous les \u00e9crans',
     'Build an original responsive canvas collection game for desktop and a 390x844 viewport. Touch buttons must be at least 44px. Pause must stop simulation and restart must reset the score.',
     'Cr\u00e9er un jeu Canvas de collecte pour ordinateur et \u00e9cran 390x844. Boutons tactiles d\u2019au moins 44px. La pause arr\u00eate la simulation ; le red\u00e9marrage remet le score \u00e0 z\u00e9ro.'),
    ('web-world', 'world', 'A tiny browser world', 'Un petit monde dans le navigateur',
     'Create an original isometric or WebGL world with collectable cells, collision boundaries, keyboard and touch input, start/pause/restart and a Canvas fallback. Use local files only.',
     'Cr\u00e9er un monde isom\u00e9trique ou WebGL original avec objets \u00e0 collecter, collisions, clavier, tactile, d\u00e9marrage, pause et restart. Fallback Canvas et fichiers locaux uniquement.'),
]


def seed_catalog(db) -> None:
    with db.session() as session:
        if session.get(Suite, 'web-v1'):
            return
        for id_, name, adapter, base, key, docs in PROVIDERS:
            session.add(Provider(id=id_, name=name, adapter=adapter, base_url=base, key_env=key, docs_url=docs))
        session.add(Harness(id=HARNESS_VERSION, version='1.0.0', tools=[],
                            description='Single bounded provider request; no tool use. Artifact-only web evaluation.'))
        session.add(Harness(id='roblox-local/1.0.0', version='1.0.0', tools=['tools/list'],
                            description='Local Studio MCP discovery and explicitly approved tool plans.'))
        session.flush()
        for slug, name, provider, api, inp, out, reasoning in MODELS:
            source = next(p[5] for p in PROVIDERS if p[0] == provider)
            session.add(Model(id=slug, provider_id=provider, name=name, description={
                'en': 'Listed from official documentation. No independent evaluation has been published.',
                'fr': 'R\u00e9f\u00e9renc\u00e9 dans la documentation officielle. Aucune \u00e9valuation ind\u00e9pendante publi\u00e9e.',
            }))
            session.flush()
            version = ModelVersion(model_id=slug, api_id=api, source_url=source, source_checked_at=CHECKED,
                                   availability='preview' if 'preview' in api else 'documented',
                                   capabilities={'reasoning_levels': reasoning, 'tool_use': True,
                                                 'text_input': True, 'image_input': True, 'source': 'provider_claim',
                                                 'api_access_verified': False})
            session.add(version)
            session.flush()
            session.add(AgentConfiguration(model_version_id=version.id, harness_id=HARNESS_VERSION,
                name=f'{name} / API default', mode='standardized', reasoning='provider-default',
                parameters={'max_output_tokens': 4096, 'time_limit_seconds': 90}))
            if inp is not None:
                session.add(PriceHistory(model_version_id=version.id, input_per_million=inp,
                    output_per_million=out, source_url=source, checked_at=CHECKED,
                    notes='Provider standard text prices as documented on 2026-10-13. No volume, regional or tool fees included.'))
        session.add(AgentConfiguration(id='fixture-reference', harness_id=HARNESS_VERSION, name='Internal reference fixture',
                                      mode='fixture', reasoning='not-applicable', parameters={}, fixture=True))
        for env, id_, title, fr, desc, desc_fr in [
            ('web','web-v1','Web Game Bench','Bench jeux web','Real browser execution. Observable checks. Evidence you can inspect.',
             'Ex\u00e9cution dans un vrai navigateur. V\u00e9rifications observables et preuves consultables.'),
            ('roblox','roblox-v1','Roblox Studio Bench','Bench Roblox Studio','Native Studio workflows, from Luau to complete multiplayer systems.',
             'Workflows natifs Studio, du Luau aux syst\u00e8mes multijoueurs complets.'),
        ]:
            session.add(Suite(id=id_, version='1.0.0', environment=env, name={'en':title,'fr':fr},
                              description={'en':desc,'fr':desc_fr}, protocol_version=PROTOCOL_VERSION))
        session.flush()
        for task in ROBLOX_TASKS:
            id_, cat, title, fr, brief, brief_fr, checks, limits = task
            spec = {'brief':{'en':brief,'fr':brief_fr},'checks':checks,'automation':'requires_real_studio',
                    'human_review_required': True, 'limits':limits, 'network':'none', 'max_parts':300,
                    'starter':f'apps/roblox-runner/scenarios/{id_}.luau', 'license':'project-original',
                    'protocol_version': PROTOCOL_VERSION}
            session.add(Task(id=id_, suite_id='roblox-v1', category=cat, title={'en':title,'fr':fr},
                             difficulty='advanced' if cat in ('multiplayer','long-horizon','security') else 'intermediate'))
            session.flush()
            session.add(TaskVersion(task_id=id_, version='1.0.0', specification=spec, spec_hash=canonical_hash(spec)))
        for id_, cat, title, fr, brief, brief_fr in WEB_TASKS:
            spec = {'brief':{'en':brief,'fr':brief_fr}, 'checks':['boot','canvas','runtime','start','keyboard','restart','mobile','touch'],
                    'automation':'playwright', 'human_review_required':True, 'max_files':64,'max_bytes':2_000_000,
                    'network':'none', 'contract':{'start':'[data-testid="start"]','restart':'[data-testid="restart"]',
                    'score':'[data-testid="score"]','state':'[data-testid="state"]','player':'[data-testid="player"]',
                    'touch':'[data-testid="touch-right"]'}, 'protocol_version': PROTOCOL_VERSION,
                    'limits':'Automated checks measure functionality, not visual quality or enjoyment.'}
            session.add(Task(id=id_, suite_id='web-v1', category=cat, title={'en':title,'fr':fr}))
            session.flush()
            session.add(TaskVersion(task_id=id_, version='1.0.0', specification=spec, spec_hash=canonical_hash(spec)))
        session.add(ResearchPost(slug='why-evidence-first', title={'en':'No evidence. No leaderboard score.',
            'fr':'Sans preuve, pas de score.'}, body={'en':'This launch includes original tasks, a reproducible harness and two explicitly labeled technical fixtures. Provider models are catalogued, not evaluated. Results are published only after actual execution and independent review.',
            'fr':'Ce lancement comprend des t\u00e2ches originales, un moteur reproductible et deux jeux de test explicitement identifi\u00e9s. Les mod\u00e8les sont r\u00e9f\u00e9renc\u00e9s, pas \u00e9valu\u00e9s. Une publication exige une ex\u00e9cution r\u00e9elle et une validation ind\u00e9pendante.'},
            sources=['https://crfm.stanford.edu/helm/','https://github.com/Roblox/open-game-eval'], published=True))
