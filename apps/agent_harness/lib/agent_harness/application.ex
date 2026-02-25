defmodule AgentHarness.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {Registry, keys: :unique, name: AgentHarness.AgentRegistry}
    ]

    opts = [strategy: :one_for_one, name: AgentHarness.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
