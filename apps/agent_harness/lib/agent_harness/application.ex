defmodule AgentHarness.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    load_dotenv()

    children = [
      {Phoenix.PubSub, name: AgentHarness.PubSub},
      AgentHarnessWeb.Endpoint
    ]

    opts = [strategy: :one_for_one, name: AgentHarness.Supervisor]
    Supervisor.start_link(children, opts)
  end

  defp load_dotenv do
    case File.read(".env") do
      {:ok, content} ->
        content
        |> String.split("\n", trim: true)
        |> Enum.reject(&(String.starts_with?(&1, "#") or &1 == ""))
        |> Enum.each(fn line ->
          case String.split(line, "=", parts: 2) do
            [key, value] -> System.put_env(String.trim(key), String.trim(value))
            _ -> :ok
          end
        end)

      _ ->
        :ok
    end
  end
end
