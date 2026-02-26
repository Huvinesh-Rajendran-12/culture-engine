import Config

config :agent_harness, AgentHarnessWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  http: [port: 4000],
  render_errors: [formats: [html: AgentHarnessWeb.ErrorHTML], layout: false],
  live_view: [signing_salt: "agent_harness_lv"],
  secret_key_base: String.duplicate("a", 64),
  server: true,
  pubsub_server: AgentHarness.PubSub

config :phoenix, :json_library, Jason

config :logger, :console,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]
