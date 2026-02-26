defmodule AgentHarnessWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :agent_harness

  @session_options [
    store: :cookie,
    key: "_agent_harness_key",
    signing_salt: "agent_harness"
  ]

  socket "/live", Phoenix.LiveView.Socket,
    websocket: [connect_info: [session: @session_options]]

  plug Plug.Static,
    at: "/",
    from: :agent_harness,
    gzip: false,
    only: ~w(assets)

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Jason

  plug Plug.MethodOverride
  plug Plug.Head
  plug Plug.Session, @session_options
  plug AgentHarnessWeb.Router
end
