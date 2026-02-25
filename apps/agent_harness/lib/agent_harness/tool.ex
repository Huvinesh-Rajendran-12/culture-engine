defmodule AgentHarness.Tool do
  @moduledoc """
  Behaviour for agent tools. Each tool defines its name, description,
  input schema, and an execute function.
  """

  @callback name() :: String.t()
  @callback description() :: String.t()
  @callback input_schema() :: map()
  @callback execute(input :: map()) :: {:ok, String.t()} | {:error, String.t()}

  @doc """
  Converts a tool module into the API definition format expected by Claude.
  """
  def to_api_definition(module) do
    %{
      "name" => module.name(),
      "description" => module.description(),
      "input_schema" => module.input_schema()
    }
  end
end
