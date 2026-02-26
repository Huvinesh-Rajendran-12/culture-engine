defmodule AgentHarness.MixProject do
  use Mix.Project

  def project do
    [
      app: :agent_harness,
      version: "0.1.0",
      elixir: "~> 1.19",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      escript: escript()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :runtime_tools],
      mod: {AgentHarness.Application, []}
    ]
  end

  defp deps do
    [
      {:req, "~> 0.5"},
      {:jason, "~> 1.4"},
      {:phoenix, "~> 1.7"},
      {:phoenix_live_view, "~> 1.0"},
      {:phoenix_html, "~> 4.1"},
      {:bandit, "~> 1.6"}
    ]
  end

  defp escript do
    [main_module: AgentHarness.CLI]
  end
end
